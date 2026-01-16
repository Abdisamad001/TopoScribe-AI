try:
    user_input = "I want a {network}"
    prompt = f"""
    User said: "{user_input}"
    """
    print("Success")
except Exception as e:
    print(f"Bust detected: {e}")
