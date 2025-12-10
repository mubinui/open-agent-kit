#!/usr/bin/env python3
"""
Integration test script for Multi-Agent Procurement Chatbot.

This script tests the procurement chatbot workflow by:
1. Obtaining a bearer token from Keycloak
2. Creating a session with the procurement_chatbot workflow
3. Sending test queries and verifying responses

Usage:
    uv run python scripts/test_procurement_chatbot.py
"""

import asyncio
import json
import httpx
import sys

# Configuration
KEYCLOAK_URL = "https://erpdevelopment.brac.net/idp/realms/brac/protocol/openid-connect/token"
BACKEND_URL = "http://localhost:8000"
USERNAME = "175050"
PASSWORD = "abc123$"
CLIENT_ID = "erp"


async def get_token() -> str:
    """Get bearer token from Keycloak."""
    print("🔐 Obtaining bearer token from Keycloak...")
    
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        response = await client.post(
            KEYCLOAK_URL,
            data={
                "grant_type": "password",
                "client_id": CLIENT_ID,
                "username": USERNAME,
                "password": PASSWORD,
            },
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to get token: {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        token_data = response.json()
        print(f"✅ Token obtained (expires in {token_data.get('expires_in')}s)")
        return token_data["access_token"]


async def create_session(token: str, workflow_id: str = "procurement_chatbot") -> str:
    """Create a new session with the specified workflow."""
    print(f"\n📝 Creating session with workflow: {workflow_id}")
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/v1/sessions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "workflow_id": workflow_id,
                "user_id": USERNAME,
                "metadata": {"test": True}
            },
        )
        
        if response.status_code not in [200, 201]:
            print(f"❌ Failed to create session: {response.status_code}")
            print(response.text)
            sys.exit(1)
        
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"✅ Session created: {session_id}")
        return session_id


async def send_message(token: str, session_id: str, message: str) -> dict:
    """Send a message to the session and get response."""
    print(f"\n💬 Sending: {message}")
    
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{BACKEND_URL}/api/v1/sessions/{session_id}/messages",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "message": message,
                "max_turns": 5,
            },
        )
        
        if response.status_code != 200:
            print(f"❌ Failed to send message: {response.status_code}")
            print(response.text)
            return {"error": response.text}
        
        result = response.json()
        print(f"🤖 Response: {result.get('response', 'No response')[:500]}...")
        return result


async def test_requisition_queries(token: str, session_id: str):
    """Test requisition-related queries."""
    print("\n" + "="*60)
    print("📋 TESTING REQUISITION QUERIES")
    print("="*60)
    
    queries = [
        "What is the status of REQ20250010638?",
        "Show my latest requisitions",
        "Who initiated REQ20250010638?",
    ]
    
    for query in queries:
        await send_message(token, session_id, query)
        await asyncio.sleep(1)


async def test_purchase_order_queries(token: str, session_id: str):
    """Test purchase order-related queries."""
    print("\n" + "="*60)
    print("📦 TESTING PURCHASE ORDER QUERIES")
    print("="*60)
    
    queries = [
        "What is the status of BPD/2025/FO-5109?",
        "Is my order approved?",
        "Show my latest purchase orders",
    ]
    
    for query in queries:
        await send_message(token, session_id, query)
        await asyncio.sleep(1)


async def test_framework_agreement_queries(token: str, session_id: str):
    """Test framework agreement-related queries."""
    print("\n" + "="*60)
    print("📄 TESTING FRAMEWORK AGREEMENT QUERIES")
    print("="*60)
    
    queries = [
        "Is there an FA for Controller?",
        "How many FAs are active?",
        "What brands are available for Controller?",
    ]
    
    for query in queries:
        await send_message(token, session_id, query)
        await asyncio.sleep(1)


async def main():
    """Run integration tests."""
    print("="*60)
    print("🚀 PROCUREMENT CHATBOT INTEGRATION TEST")
    print("="*60)
    
    # Check if backend is running
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{BACKEND_URL}/api/v1/health")
            if response.status_code != 200:
                print(f"⚠️  Backend health check returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend not reachable at {BACKEND_URL}")
        print(f"   Error: {e}")
        print("\n💡 Please start the backend first:")
        print("   uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)
    
    print(f"✅ Backend is running at {BACKEND_URL}")
    
    # Get token
    token = await get_token()
    
    # Create session
    session_id = await create_session(token, "procurement_chatbot")
    
    # Run tests
    await test_requisition_queries(token, session_id)
    await test_purchase_order_queries(token, session_id)
    await test_framework_agreement_queries(token, session_id)
    
    print("\n" + "="*60)
    print("✅ INTEGRATION TESTS COMPLETED")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
