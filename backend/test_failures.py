import requests
import json

url = "http://127.0.0.1:8000/api/design/clarify"

# Case 1: Message missing 'content'
payload_bad_msg = {
    "description": "Design a network",
    "conversation_history": [
        {"role": "user", "content": "Hi"},
        {"role": "assistant"} # Missing content
    ]
}

# Case 2: Message missing 'role'
payload_no_role = {
    "description": "Design a network",
    "conversation_history": [
        {"content": "Hi"} # Missing role
    ]
}

print("Testing Bad Message...")
try:
    response = requests.post(url, json=payload_bad_msg)
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")

print("\nTesting No Role...")
try:
    response = requests.post(url, json=payload_no_role)
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
