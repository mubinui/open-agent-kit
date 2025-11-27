"""Tool registry for managing dynamic tool registration with Autogen agents."""

import importlib
import inspect
from typing import Any, Callable, Optional, TYPE_CHECKING

from autogen.agentchat import ConversableAgent

if TYPE_CHECKING:
    from src.config.loader import ConfigurationError
    from src.infrastructure.providers import ProviderAdapter

# Lazy import to avoid circular dependency
def _get_logger():
    from src.audit_logging import get_logger
    return get_logger(__name__)

def _get_loader():
    from src.config.loader import get_loader
    return get_loader()

def _get_configuration_error():
    from src.config.loader import ConfigurationError
    return ConfigurationError


class ToolDefinition:
    """Definition of a tool that can be registered with agents."""

    def __init__(
        self,
        tool_id: str,
        function: Callable,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Initialize a tool definition.

        Args:
            tool_id: Unique identifier for the tool
            function: The callable function to execute
            name: Optional name for the tool (defaults to function name)
            description: Optional description (extracted from docstring if not provided)
        """
        self.tool_id = tool_id
        self.function = function
        self.name = name or function.__name__
        self.description = description or self._extract_description(function)

    def _extract_description(self, func: Callable) -> str:
        """
        Extract description from function docstring.

        Args:
            func: Function to extract description from

        Returns:
            Description string
        """
        if func.__doc__:
            # Get first line of docstring
            lines = func.__doc__.strip().split("\n")
            return lines[0].strip()
        return f"Tool: {func.__name__}"

    def __repr__(self) -> str:
        """String representation of tool definition."""
        return f"ToolDefinition(id={self.tool_id}, name={self.name})"


class ToolRegistry:
    """
    Registry for managing tools and their registration with Autogen agents.

    This registry supports:
    - Dynamic tool registration from Python functions
    - Tool discovery from entrypoints
    - Autogen's register_for_llm and register_for_execution patterns
    - Tool validation and schema generation
    """

    def __init__(self, provider_adapter: Optional["ProviderAdapter"] = None) -> None:
        """
        Initialize the tool registry.
        
        Args:
            provider_adapter: Optional provider adapter for unified client management
        """
        self._tools: dict[str, ToolDefinition] = {}
        self.provider_adapter = provider_adapter

    def register_tool(
        self,
        tool_id: str,
        function: Callable,
        description: Optional[str] = None,
        name: Optional[str] = None,
    ) -> None:
        """
        Register a tool function.

        Args:
            tool_id: Unique identifier for the tool
            function: The callable function to register
            description: Optional description of what the tool does
            name: Optional name for the tool (defaults to function name)

        Raises:
            ValueError: If tool_id already registered or function is invalid
        """
        if tool_id in self._tools:
            _get_logger().warning(
                "Tool already registered, overwriting",
                tool_id=tool_id,
            )

        # Validate function
        if not callable(function):
            raise ValueError(f"Tool {tool_id}: function must be callable")

        # Validate function signature
        self._validate_function_signature(function)

        # Create tool definition
        tool_def = ToolDefinition(
            tool_id=tool_id,
            function=function,
            name=name,
            description=description,
        )

        self._tools[tool_id] = tool_def

        _get_logger().info(
            "Registered tool",
            tool_id=tool_id,
            tool_name=tool_def.name,
        )

    def register_tool_from_entrypoint(
        self,
        tool_id: str,
        entrypoint: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        """
        Register a tool by importing from an entrypoint.

        Args:
            tool_id: Unique identifier for the tool
            entrypoint: Import path in format "module.path:function_name"
            name: Optional name for the tool
            description: Optional description

        Raises:
            ValueError: If entrypoint is invalid or import fails
        """
        try:
            # Parse entrypoint
            if ":" not in entrypoint:
                raise ValueError(
                    f"Invalid entrypoint format: {entrypoint}. "
                    "Expected 'module.path:function_name'"
                )

            module_path, function_name = entrypoint.split(":", 1)

            # Import module and get function
            module = importlib.import_module(module_path)
            function = getattr(module, function_name)

            # Register the function
            self.register_tool(
                tool_id=tool_id,
                function=function,
                description=description,
                name=name,
            )

            _get_logger().info(
                "Registered tool from entrypoint",
                tool_id=tool_id,
                entrypoint=entrypoint,
            )

        except Exception as e:
            _get_logger().error(
                "Failed to register tool from entrypoint",
                tool_id=tool_id,
                entrypoint=entrypoint,
                error=str(e),
            )
            raise ValueError(
                f"Failed to register tool {tool_id} from {entrypoint}: {e}"
            ) from e

    def register_tool_with_agents(
        self,
        tool_id: str,
        caller: ConversableAgent,
        executor: ConversableAgent,
    ) -> None:
        """
        Register a tool with caller and executor agents using Autogen's pattern.

        This uses Autogen's register_for_llm (for the caller) and
        register_for_execution (for the executor) pattern.

        Args:
            tool_id: ID of the tool to register
            caller: Agent that will call the tool (gets function schema)
            executor: Agent that will execute the tool (gets function implementation)

        Raises:
            ValueError: If tool not found
        """
        tool_def = self.get_tool(tool_id)
        if tool_def is None:
            raise ValueError(f"Tool not found: {tool_id}")

        try:
            # Register for LLM (caller gets the schema)
            caller.register_for_llm(
                name=tool_def.name,
                description=tool_def.description,
            )(tool_def.function)

            # Register for execution (executor can run the function)
            executor.register_for_execution(
                name=tool_def.name,
            )(tool_def.function)

            _get_logger().info(
                "Registered tool with agents",
                tool_id=tool_id,
                caller=caller.name,
                executor=executor.name,
            )

        except Exception as e:
            _get_logger().error(
                "Failed to register tool with agents",
                tool_id=tool_id,
                caller=caller.name,
                executor=executor.name,
                error=str(e),
            )
            raise ValueError(
                f"Failed to register tool {tool_id} with agents: {e}"
            ) from e

    def register_tool_with_agent(
        self,
        tool_id: str,
        agent: ConversableAgent,
    ) -> None:
        """
        Register a tool with a single agent (both LLM and execution).

        This is a convenience method for when the same agent both calls
        and executes the tool.

        Args:
            tool_id: ID of the tool to register
            agent: Agent to register the tool with

        Raises:
            ValueError: If tool not found
        """
        self.register_tool_with_agents(tool_id, agent, agent)

    def get_tool(self, tool_id: str) -> Optional[ToolDefinition]:
        """
        Get tool definition by ID.

        Args:
            tool_id: Tool identifier

        Returns:
            ToolDefinition or None if not found
        """
        return self._tools.get(tool_id)

    def list_tools(self) -> list[str]:
        """
        List all registered tool IDs.

        Returns:
            List of tool IDs
        """
        return list(self._tools.keys())

    def unregister_tool(self, tool_id: str) -> None:
        """
        Unregister a tool.

        Args:
            tool_id: ID of tool to unregister
        """
        if tool_id in self._tools:
            del self._tools[tool_id]
            _get_logger().info("Unregistered tool", tool_id=tool_id)

    def _validate_function_signature(self, function: Callable) -> None:
        """
        Validate that a function has a proper signature for tool use.

        Args:
            function: Function to validate

        Raises:
            ValueError: If function signature is invalid
        """
        try:
            sig = inspect.signature(function)

            # Check that function has type hints (recommended for schema generation)
            params_without_hints = [
                name
                for name, param in sig.parameters.items()
                if param.annotation == inspect.Parameter.empty
            ]

            if params_without_hints:
                _get_logger().warning(
                    "Function parameters missing type hints",
                    function=function.__name__,
                    parameters=params_without_hints,
                )

            # Check return type hint
            if sig.return_annotation == inspect.Signature.empty:
                _get_logger().warning(
                    "Function missing return type hint",
                    function=function.__name__,
                )

        except Exception as e:
            _get_logger().warning(
                "Could not validate function signature",
                function=function.__name__,
                error=str(e),
            )

    def load_from_config(self) -> None:
        """
        Load tools from configuration file.

        This method loads all enabled tools from the tools.json configuration
        and registers them with the registry.

        Raises:
            ConfigurationError: If configuration loading fails
        """
        _get_logger().info("Loading tools from configuration")

        try:
            loader = _get_loader()
            config = loader.load_tools(use_cache=False)

            # Track loaded tools
            loaded_count = 0
            failed_count = 0

            # Register enabled tools
            for tool_config in config.get_enabled_tools():
                try:
                    self.register_tool_from_entrypoint(
                        tool_id=tool_config.id,
                        entrypoint=tool_config.entrypoint,
                        name=tool_config.name,
                        description=tool_config.description,
                    )
                    loaded_count += 1
                except Exception as e:
                    _get_logger().error(
                        "Failed to load tool from config",
                        tool_id=tool_config.id,
                        error=str(e),
                    )
                    failed_count += 1

            _get_logger().info(
                "Finished loading tools from configuration",
                loaded=loaded_count,
                failed=failed_count,
                total=len(config.tools),
            )

        except Exception as e:
            _get_logger().error("Failed to load tools configuration", error=str(e))
            raise

    def reload_from_config(self) -> None:
        """
        Reload tools from configuration file.

        This clears all existing tools and reloads from configuration.

        Raises:
            ConfigurationError: If configuration loading fails
        """
        _get_logger().info("Reloading tools from configuration")

        # Clear existing tools
        old_tools = set(self._tools.keys())
        self._tools.clear()

        # Load fresh tools
        self.load_from_config()

        new_tools = set(self._tools.keys())

        # Log changes
        added = new_tools - old_tools
        removed = old_tools - new_tools

        if added:
            _get_logger().info("Added tools", tool_ids=list(added))
        if removed:
            _get_logger().info("Removed tools", tool_ids=list(removed))

        _get_logger().info("Successfully reloaded tools")


# Singleton instance
_tool_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the singleton tool registry instance.

    Returns:
        ToolRegistry instance
    """
    global _tool_registry
    if _tool_registry is None:
        _tool_registry = ToolRegistry()
        # Load initial configuration
        try:
            _tool_registry.load_from_config()
        except Exception as e:
            _get_logger().error("Failed to initialize tool registry from config", error=str(e))
        _get_logger().info("Initialized tool registry")
    return _tool_registry
