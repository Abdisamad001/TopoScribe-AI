import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_llm_response(
    prompt: str,
    model: str = "llama-3.3-70b-versatile", # Updated to latest model avail in Groq
    temperature: float = 0.7,
    max_tokens: int = 2000
) -> str:
    """
    Calls Groq API and returns response text.
    """
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"LLM call failed: {str(e)}")
