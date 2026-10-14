""" LLM access layer"""

import os
from typing import Literal, Optional

from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

load_dotenv()

Tier = Literal["planning", "primary", "escalated"]

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]

# qwen/qwen3.6-27b was default model for Groq.
GROQ_DEFAULT_MODEL = "qwen/qwen3.8-27b"
OPENAI_FALLBACK_MODEL = "gpt-5.5"

_groq_client: Optional[Groq] = None
_openai_client: Optional[OpenAI] = None


_FIXED_TEMPERATURE_MODEL_PREFIXES = ("gpt-5",)

LLM_MAX_OUTPUT_TOKENS = 8000

GROQ_PRIMARY_MAX_OUTPUT_TOKENS = 5700

# gpt-5 class models 
_REASONING_TOKEN_ALLOWANCE = 2000


def _get_groq_client() -> Groq:
  
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise Exception("Groq call failed")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_openai_client() -> OpenAI:
    
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("OpenAI call failed")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _resolve_openai_model(env_var: str) -> str:
    return os.getenv(env_var) or OPENAI_FALLBACK_MODEL


def _requires_default_params(model: str) -> bool:
    return model.startswith(_FIXED_TEMPERATURE_MODEL_PREFIXES)


def _call_groq(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    reasoning_effort: Optional[ReasoningEffort] = None,
) -> str:
    client = _get_groq_client()
    kwargs = {}
    
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.choices[0].message.content
    except Exception as e:
        raise Exception(f"Groq call failed: {str(e)}")


def _openai_create(
    client: OpenAI,
    model: str,
    prompt: str,
    temperature: float,
    max_tokens: int,
    reasoning_effort: Optional[ReasoningEffort] = None,
):
    messages = [{"role": "user", "content": prompt}]
    kwargs = {}
    
    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if _requires_default_params(model):
        return client.chat.completions.create(
            model=model,
            messages=messages,
            max_completion_tokens=max_tokens + _REASONING_TOKEN_ALLOWANCE,
            **kwargs,
        )
    return client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        **kwargs,
    )


def _call_openai(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    reasoning_effort: Optional[ReasoningEffort] = None,
) -> str:
    client = _get_openai_client()
    try:
        response = _openai_create(
            client, model, prompt, temperature, max_tokens, reasoning_effort
        )
    except Exception as e:
        raise Exception(f"OpenAI call failed: {str(e)}")

    choice = response.choices[0]
    content = choice.message.content or ""
    if not content.strip():
       
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
    max_tokens: Optional[int] = None,
    reasoning_effort: Optional[ReasoningEffort] = None,
) -> str:
    
    if max_tokens is None:
        max_tokens = (
            GROQ_PRIMARY_MAX_OUTPUT_TOKENS
            if tier == "primary"
            else LLM_MAX_OUTPUT_TOKENS
        )
    if tier == "primary":
        return _call_groq(
            prompt, GROQ_DEFAULT_MODEL, temperature, max_tokens, reasoning_effort
        )
    if tier == "planning":
        return _call_openai(
            prompt,
            _resolve_openai_model("OPENAI_PLANNING_MODEL"),
            temperature,
            max_tokens,
            reasoning_effort,
        )
    if tier == "escalated":

        # leave at model default.
        return _call_openai(
            prompt,
            _resolve_openai_model("OPENAI_ESCALATION_MODEL"),
            temperature,
            max_tokens,
            reasoning_effort,
        )
    raise ValueError(f"Unknown LLM tier: {tier!r}")


def get_llm_response(
    prompt: str,
    model: str = GROQ_DEFAULT_MODEL,
    temperature: float = 0.25,
    max_tokens: int = 2000,
) -> str:
    return _call_groq(prompt, model, temperature, max_tokens)
