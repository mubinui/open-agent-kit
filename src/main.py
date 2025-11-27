"""Main application entry point."""

import asyncio
import sys
from uuid import UUID

from src.agents.orchestrator import Orchestrator
from src.audit_logging import AuditLogger, configure_logging
from src.config.registries import get_prompt_registry, get_provider_registry
from src.config.config_loader import get_config_loader
from src.memory import InMemoryConversationStore


async def interactive_chat() -> None:
    """Run an interactive chat session."""
    # Initialize components
    configure_logging()
    store = InMemoryConversationStore()
    audit_logger = AuditLogger()
    orchestrator = Orchestrator(store, audit_logger)

    print("=" * 60)
    print("Microsoft Autogen Sequential Multi-Agent Chatbot")
    print("=" * 60)
    print("\nCommands:")
    print("  quit/exit    - End the conversation")
    print("  history      - See conversation history")
    print("  new          - Start a new session")
    print("  reload       - Reload configuration files")
    print("  providers    - List available API providers")
    print("  prompts      - List available prompt templates")
    print("  status       - Show system status\n")

    # Create initial session
    state = await orchestrator.create_session()
    session_id = state.session_id

    print(f"Session started: {session_id}\n")

    try:
        while True:
            # Get user input
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n\nGoodbye!")
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ["quit", "exit"]:
                await orchestrator.end_session(session_id)
                print("\nSession ended. Goodbye!")
                break

            elif user_input.lower() == "new":
                await orchestrator.end_session(session_id)
                state = await orchestrator.create_session()
                session_id = state.session_id
                print(f"\nNew session started: {session_id}\n")
                continue

            elif user_input.lower() == "history":
                history = await orchestrator.get_session_history(session_id)
                print("\n--- Conversation History ---")
                for msg in history.get("messages", []):
                    role = msg["role"].capitalize()
                    content = msg["content"]
                    print(f"{role}: {content}")
                print(f"Turns: {history.get('turn_count', 0)}")
                print("--- End History ---\n")
                continue

            elif user_input.lower() == "reload":
                print("\nReloading configurations...")
                try:
                    # Reload from centralized config loader
                    config_loader = get_config_loader()
                    config_loader.reload_all()
                    
                    # Also reload registries for backward compatibility
                    provider_registry = get_provider_registry()
                    prompt_registry = get_prompt_registry()
                    provider_registry.reload_from_config()
                    prompt_registry.reload_from_config()
                    
                    print("✓ Configurations reloaded successfully\n")
                except Exception as e:
                    print(f"✗ Failed to reload configurations: {e}\n")
                continue

            elif user_input.lower() == "providers":
                print("\n--- Available API Providers ---")
                provider_registry = get_provider_registry()
                for provider_id in provider_registry.list_providers():
                    provider = provider_registry.get_provider(provider_id)
                    if provider:
                        status = "✓ enabled" if provider.enabled else "✗ disabled"
                        print(f"  {provider_id}: {provider.name} ({provider.type.value}) [{status}]")
                print()
                continue

            elif user_input.lower() == "prompts":
                print("\n--- Available Prompt Templates ---")
                prompt_registry = get_prompt_registry()
                for prompt_id in prompt_registry.list_prompts():
                    prompt = prompt_registry.get_prompt(prompt_id)
                    if prompt:
                        print(f"  {prompt_id}: {prompt.description} (target: {prompt.target})")
                print()
                continue

            elif user_input.lower() == "status":
                print("\n--- System Status ---")
                provider_registry = get_provider_registry()
                prompt_registry = get_prompt_registry()
                print(f"Active Session: {session_id}")
                print(f"Turn Count: {(await orchestrator.get_session_history(session_id)).get('turn_count', 0)}")
                print(f"Registered Providers: {len(provider_registry.list_providers())}")
                print(f"Enabled Providers: {len(provider_registry.list_enabled_providers())}")
                print(f"Prompt Templates: {len(prompt_registry.list_prompts())}")
                print()
                continue

            # Process message through agent pipeline
            print("Assistant: ", end="", flush=True)
            result = await orchestrator.process_message(session_id, user_input)

            if "error" in result:
                print(f"Error: {result['error']}")
                if result.get("session_ended"):
                    break
            else:
                print(result["response"])
                if not result.get("safety_passed", True):
                    print("⚠️  [Safety check triggered]")

            print()  # Empty line for readability

    finally:
        await orchestrator.cleanup()
        print("\nThank you for using the chatbot!")


async def single_message_mode(message: str) -> None:
    """Process a single message (useful for testing)."""
    configure_logging()
    store = InMemoryConversationStore()
    audit_logger = AuditLogger()
    orchestrator = Orchestrator(store, audit_logger)

    try:
        state = await orchestrator.create_session()
        result = await orchestrator.process_message(state.session_id, message)

        print(f"User: {message}")
        print(f"Assistant: {result.get('response', 'No response')}")

        if not result.get("safety_passed", True):
            print("⚠️  Safety check triggered")

    finally:
        await orchestrator.cleanup()


def main() -> None:
    """Main entry point."""
    if len(sys.argv) > 1:
        # Single message mode
        # Handle both --message flag and direct message input
        args = sys.argv[1:]
        if args[0] == "--message" and len(args) > 1:
            message = " ".join(args[1:])
        else:
            message = " ".join(args)
        asyncio.run(single_message_mode(message))
    else:
        # Interactive mode
        asyncio.run(interactive_chat())


if __name__ == "__main__":
    main()
