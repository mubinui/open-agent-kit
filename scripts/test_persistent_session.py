#!/usr/bin/env python3
"""
Create a test session via API to verify persistence
"""
import requests
import json
import time

API_BASE = "http://localhost:8000/api/v1"

def create_session():
    """Create a new session"""
    response = requests.post(
        f"{API_BASE}/sessions",
        json={
            "workflow_id": "simple_assistant",
            "user_id": "demo-user",
            "metadata": {
                "test": True,
                "purpose": "persistent-demo"
            }
        }
    )
    response.raise_for_status()
    return response.json()

def send_message(session_id, message):
    """Send a message to session"""
    response = requests.post(
        f"{API_BASE}/sessions/{session_id}/messages",
        json={"message": message}
    )
    response.raise_for_status()
    return response.json()

def get_session(session_id):
    """Retrieve session"""
    response = requests.get(f"{API_BASE}/sessions/{session_id}")
    response.raise_for_status()
    return response.json()

def main():
    print("=" * 60)
    print("Creating Persistent Session Demo")
    print("=" * 60)
    
    # Create session
    print("\nCreating new session...")
    session_data = create_session()
    session_id = session_data["session_id"]
    print(f"Session created: {session_id}")
    print(f"   Workflow: {session_data['workflow_id']}")
    print(f"   Active: {session_data['active']}")
    
    # Send a test message
    print(f"\nSending test message...")
    response = send_message(session_id, "Hello! What's the weather like?")
    print(f"Message sent and processed")
    print(f"   Turn count: {response.get('turn_count', 'N/A')}")
    
    # Verify session exists
    print(f"\nRetrieving session...")
    session = get_session(session_id)
    print(f"Session retrieved: {session['session_id']}")
    print(f"   Turn count: {session['turn_count']}")
    print(f"   Active: {session['active']}")
    
    print("\n" + "=" * 60)
    print("Session persisted successfully!")
    print("=" * 60)
    print(f"\nTo verify in MongoDB, run:")
    print(f"docker exec orchestration-mongodb mongosh -u orchestrator -p orchestrator_pass \\")
    print(f"  --authenticationDatabase orchestration orchestration \\")
    print(f"  --eval 'db.sessions.find({{_id: \"{session_id}\"}})'")
    print(f"\nSession ID: {session_id}")
    print(f"This session will auto-expire in 24 hours unless updated.")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to API")
        print("Make sure the orchestration service is running:")
        print("  docker-compose up -d")
    except Exception as e:
        print(f"Error: {e}")
