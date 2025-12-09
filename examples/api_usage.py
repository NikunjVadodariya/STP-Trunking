"""
API Usage Examples
"""

import requests
import json

# API base URL
BASE_URL = "http://localhost:8000/api/v1"

# Example: Register a new user
def register_user(email: str, username: str, password: str, full_name: str = None):
    """Register a new user."""
    response = requests.post(
        f"{BASE_URL}/auth/register",
        json={
            "email": email,
            "username": username,
            "password": password,
            "full_name": full_name
        }
    )
    return response.json()


# Example: Login
def login(username: str, password: str):
    """Login and get access token."""
    response = requests.post(
        f"{BASE_URL}/auth/login",
        data={
            "username": username,
            "password": password
        }
    )
    return response.json()


# Example: Create SIP account
def create_sip_account(token: str, account_name: str, username: str, password: str,
                       server_host: str, server_port: int = 5060, domain: str = "localhost"):
    """Create a SIP account."""
    response = requests.post(
        f"{BASE_URL}/accounts",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "account_name": account_name,
            "username": username,
            "password": password,
            "server_host": server_host,
            "server_port": server_port,
            "domain": domain
        }
    )
    return response.json()


# Example: Make a call
def make_call(token: str, sip_account_id: int, to_uri: str):
    """Initiate a call."""
    response = requests.post(
        f"{BASE_URL}/calls",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "sip_account_id": sip_account_id,
            "to_uri": to_uri
        }
    )
    return response.json()


# Example: Get call status
def get_call_status(token: str, call_id: str):
    """Get call status."""
    response = requests.get(
        f"{BASE_URL}/calls/{call_id}/status",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()


# Example: Hangup call
def hangup_call(token: str, call_id: str):
    """Hang up a call."""
    response = requests.post(
        f"{BASE_URL}/calls/{call_id}/hangup",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()


# Example: List calls
def list_calls(token: str, skip: int = 0, limit: int = 100):
    """List all calls."""
    response = requests.get(
        f"{BASE_URL}/calls?skip={skip}&limit={limit}",
        headers={"Authorization": f"Bearer {token}"}
    )
    return response.json()


if __name__ == "__main__":
    # Example workflow
    print("1. Registering user...")
    user = register_user(
        email="user@example.com",
        username="testuser",
        password="testpass123",
        full_name="Test User"
    )
    print(f"User registered: {user}")
    
    print("\n2. Logging in...")
    token_data = login("testuser", "testpass123")
    token = token_data["access_token"]
    print(f"Logged in. Token: {token[:20]}...")
    
    print("\n3. Creating SIP account...")
    account = create_sip_account(
        token=token,
        account_name="My SIP Account",
        username="sipuser",
        password="sippass",
        server_host="localhost",
        server_port=5060,
        domain="localhost"
    )
    print(f"SIP account created: {account}")
    
    print("\n4. Making a call...")
    call = make_call(
        token=token,
        sip_account_id=account["id"],
        to_uri="sip:user@example.com"
    )
    print(f"Call initiated: {call}")
    
    print("\n5. Getting call status...")
    import time
    time.sleep(2)
    status = get_call_status(token, call["call_id"])
    print(f"Call status: {status}")
    
    print("\n6. Listing calls...")
    calls = list_calls(token)
    print(f"Total calls: {len(calls)}")

