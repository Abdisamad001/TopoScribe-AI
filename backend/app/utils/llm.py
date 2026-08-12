"""
LLM access layer.

Tier routing (Part 2 escalation scope):
- "planning"   -> OpenAI. Used unconditionally by the Planning Agent on every call.
                  This is Planning's assigned model, not a retry/escalation path.
- "primary"    -> Groq. Used by Topology attempt 0, Configuration, and Validation.
- "escalated"  -> OpenAI. Invoked only by the Topology Agent's retry path.
                  Never wired into Configuration or Validation.
"""
import os
from typing import Literal, Optional

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

load_dotenv()

Tier = Literal["planning", "primary", "escalated"]

GROQ_DEFAULT_MODEL = "llama-3.3-70b-versatile"
OPENAI_FALLBACK_MODEL = "gpt-5.5"

_groq_client: Optional[Groq] = None
_openai_client: Optional[OpenAI] = None

# Confirmed against the live API during Part 2 integration testing: gpt-5 class
# models accept only the default temperature (1) and replace `max_tokens` with
# `max_completion_tokens`.
_FIXED_TEMPERATURE_MODEL_PREFIXES = ("gpt-5",)

# Output budget every tier gets, so a retry that escalates does so because the
# stronger model produced better content, not because it was handed more room.
# Topology output scales with design size: 1425/2839/3556 content tokens for
# 5/10/15-department designs. At the previous 2000 cap Groq truncated a
# 15-department topology mid-JSON (finish_reason="length"), which the quality
# gate could only report as malformed JSON.
LLM_MAX_OUTPUT_TOKENS = 8000

# gpt-5 class models bill internal reasoning against the same budget, so they get
# an allowance on top to keep their *content* budget equal to the figure above.
# Reasoning is near-constant with design size (404/485/512 tokens for the three
# designs measured), so this is sized well clear of the observed range rather
# than scaled per request.
_REASONING_TOKEN_ALLOWANCE = 2000


def _get_groq_client() -> Groq:
    """Groq client, created on first use so a missing key never breaks imports."""
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise Exception("Groq call failed: GROQ_API_KEY is not set in the environment.")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_openai_client() -> OpenAI:
    """OpenAI client, created on first use so a missing key never breaks imports."""
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("OpenAI call failed: OPENAI_API_KEY is not set in the environment.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _resolve_openai_model(env_var: str) -> str:
    return os.getenv(env_var) or OPENAI_FALLBACK_MODEL


def _requires_default_params(model: str) -> bool:
    return model.startswith(_FIXED_TEMPERATURE_MODEL_PREFIXES)


def _call_groq(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    client = _get_groq_client()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Groq call failed: {str(e)}")


def _openai_create(client: OpenAI, model: str, prompt: str, temperature: float, max_tokens: int):
    messages = [{"role": "user", "content": prompt}]
    if _requires_default_params(model):
        return client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=max_tokens + _REASONING_TOKEN_ALLOWANCE,
        )
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _call_openai(prompt: str, model: str, temperature: float, max_tokens: int) -> str:
    client = _get_openai_client()
    try:
        response = _openai_create(client, model, prompt, temperature, max_tokens)
    except Exception as e:
        raise Exception(f"OpenAI call failed: {str(e)}")

    choice = response.choices[0]
    content = choice.message.content or ""
    if not content.strip():
        # Reported as its own failure rather than passed on as an empty string,
        # which downstream parsers would misdiagnose as malformed JSON.
        raise Exception(
            f"OpenAI call failed: {model} returned no content "
            f"(finish_reason={choice.finish_reason})."
        )
    return content


def call_llm(
    prompt: str,
    *,
    tier: Tier,
    temperature: float = 0.25,
    max_tokens: int = LLM_MAX_OUTPUT_TOKENS,
) -> str:
    """
    Routes a prompt to the provider and model assigned to the given tier.
    """
    if tier == "primary":
        return _call_groq(prompt, GROQ_DEFAULT_MODEL, temperature, max_tokens)
    if tier == "planning":
        return _call_openai(
            prompt, _resolve_openai_model("OPENAI_PLANNING_MODEL"), temperature, max_tokens
        )
    if tier == "escalated":
        return _call_openai(
            prompt, _resolve_openai_model("OPENAI_ESCALATION_MODEL"), temperature, max_tokens
        )
    raise ValueError(f"Unknown LLM tier: {tier!r}")


def get_llm_response(
    prompt: str,
    model: str = GROQ_DEFAULT_MODEL,
    temperature: float = 0.25,
    max_tokens: int = 2000,
) -> str:
    """
    Calls Groq API and returns response text.
    """
    return _call_groq(prompt, model, temperature, max_tokens)
