import requests
import sys

try:
    print("Sending request v2...")
    response = requests.post(
        "http://localhost:8000/api/design/generate",
        json={"description": "Design a small network", "conversation_history": []},
        timeout=10 # Add timeout
    )
    print(f"Response Status: {response.status_code}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
