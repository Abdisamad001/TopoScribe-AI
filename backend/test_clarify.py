import requests
import json

url = "http://127.0.0.1:8000/api/design/clarify"

payload = {
    "description": "Design a network",
    "conversation_history": [
        {"role": "user", "content": "Design a network"},
        {"role": "assistant", "content": "How many users?"},
        {"role": "user", "content": "100 users"}
    ]
}

try:
    response = requests.post(url, json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
