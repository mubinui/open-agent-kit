#!/usr/bin/env python3
"""
Test script for Requisition API integration.

This script tests the complete authentication flow:
1. Extract username and roles from user's JWT
2. Get admin token using client_credentials grant
3. Call Requisition API with admin token + x-client headers

Usage:
    python scripts/test_requisition_api.py <user_jwt>

Flow:
    User JWT → Extract username/roles → Get admin token → Call API with admin token + x-client headers
"""

import asyncio
import base64
import json
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
from dotenv import load_dotenv

load_dotenv()


def decode_jwt(token: str) -> dict:
    """Decode JWT payload without verification."""
    payload = token.split('.')[1]
    padding = 4 - len(payload) % 4
    if padding != 4:
        payload += '=' * padding
    return json.loads(base64.b64decode(payload))


def extract_user_info(jwt_token: str) -> tuple[str, list[str]]:
    """Extract username and roles from user's JWT."""
    claims = decode_jwt(jwt_token)
    
    username = claims.get("preferred_username", "unknown")
    
    # Get roles from 'authorities' claim (custom) or 'realm_access.roles'
    roles = claims.get("authorities", [])
    if not roles:
        realm_access = claims.get("realm_access", {})
        roles = realm_access.get("roles", [])
    
    return username, roles


async def get_admin_token() -> str:
    """Get admin token using client_credentials grant."""
    server_url = os.getenv("KEYCLOAK_SERVER_URL", "https://erpdevelopment.brac.net/idp")
    realm = os.getenv("KEYCLOAK_REALM", "brac")
    client_id = os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "chat-backend")
    client_secret = os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET")
    
    token_endpoint = f"{server_url}/realms/{realm}/protocol/openid-connect/token"
    
    print(f"\n2️⃣  Getting admin token from Keycloak...")
    print(f"   Endpoint: {token_endpoint}")
    print(f"   Client ID: {client_id}")
    
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            token_endpoint,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        
        if response.status_code != 200:
            print(f"   ❌ Failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
            
        token_data = response.json()
        print(f"   ✅ Got admin token (expires in {token_data.get('expires_in')}s)")
        return token_data["access_token"]


async def call_requisition_api(
    req_no: str,
    admin_token: str,
    username: str,
    roles: list[str],
) -> dict:
    """Call Requisition API with admin token and x-client headers."""
    base_url = "http://10.42.65.155:8012"
    url = f"{base_url}/api/v1/requisition"
    
    # x-client-ref should be comma-separated string
    roles_str = ",".join(roles) if isinstance(roles, list) else roles
    
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {admin_token}",
        "x-client-username": username,
        "x-client-ref": roles_str,
    }
    
    params = {"reqNo": req_no}
    
    print(f"\n3️⃣  Calling Requisition API...")
    print(f"   URL: {url}?reqNo={req_no}")
    print(f"   Authorization: Bearer <admin_token>")
    print(f"   x-client-username: {username}")
    print(f"   x-client-ref: {roles_str[:80]}...")  # Show first 80 chars)
    
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        response = await client.get(url, params=params, headers=headers)
        
        print(f"\n4️⃣  Response:")
        print(f"   Status: {response.status_code}")
        
        try:
            data = response.json()
            if response.status_code == 200:
                print(f"   ✅ Success!")
                print(f"   Data preview: {json.dumps(data, indent=2)[:500]}...")
            else:
                print(f"   ❌ Error: {json.dumps(data)}")
        except:
            print(f"   Body: {response.text[:500]}")
            data = None
        
        return {
            "status_code": response.status_code,
            "success": 200 <= response.status_code < 300,
            "data": data,
        }


async def main():
    print("=" * 70)
    print("Requisition API Test - Service-to-Service Flow")
    print("=" * 70)
    print("\nFlow: User JWT → Extract info → Admin token → API call with x-client headers")
    
    # Check for JWT argument
    if len(sys.argv) < 2:
        print("\n❌ Usage: python scripts/test_requisition_api.py <user_jwt>")
        print("   Provide the user's JWT token as an argument")
        return
    
    user_jwt = sys.argv[1]
    
    # Step 1: Extract username and roles from user's JWT
    print(f"\n1️⃣  Extracting user info from JWT...")
    try:
        username, roles = extract_user_info(user_jwt)
        print(f"   Username: {username}")
        print(f"   Roles: {len(roles)} total")
        print(f"   Sample roles: {roles[:5]}...")
    except Exception as e:
        print(f"   ❌ Failed to decode JWT: {e}")
        return
    
    # Step 2: Get admin token
    admin_token = await get_admin_token()
    if not admin_token:
        print("\n❌ Cannot proceed without admin token")
        return
    
    # Step 3 & 4: Call API with admin token + x-client headers
    req_no = "REQ20250010638"
    result = await call_requisition_api(req_no, admin_token, username, roles)
    
    # Summary
    print("\n" + "=" * 70)
    if result["success"]:
        print("✅ TEST PASSED - Service-to-service flow works correctly!")
    else:
        print(f"❌ TEST FAILED - Status {result['status_code']}")
        if result['status_code'] == 403:
            print("\nThe Requisition API needs to trust x-client-ref header for authorization")
            print("OR add required roles to chat-backend service account in Keycloak")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
