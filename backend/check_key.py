import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GROQ_API_KEY")
if key:
    print(f"Key found: {key[:5]}...{key[-5:]}")
else:
    print("Key NOT found")
