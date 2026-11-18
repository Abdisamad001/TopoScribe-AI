import os
from typing import Any, Dict, Literal, Optional
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI

load_dotenv()

Tier = Literal["planning", "primary", "escalated"]

ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh", "max"]

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_PRIMARY_MODEL = "qwen/qwen3.8-27b"
OPENROUTER_GPT55_MODEL = "openai/gpt-5.5"

# [GROQ] model id (same string on OpenRouter); alias kept for imports
GROQ_DEFAULT_MODEL = OPENROUTER_PRIMARY_MODEL
OPENAI_FALLBACK_MODEL = "gpt-5.5"

_groq_client: Optional[Groq] = None
_openai_client: Optional[OpenAI] = None
_openrouter_client: Optional[OpenAI] = None

_FIXED_TEMPERATURE_MODEL_PREFIXES = ("gpt-5",)

LLM_MAX_OUTPUT_TOKENS = 8000

PRIMARY_MAX_OUTPUT_TOKENS = 5700
GROQ_PRIMARY_MAX_OUTPUT_TOKENS = PRIMARY_MAX_OUTPUT_TOKENS

# gpt-5 class models
_REASONING_TOKEN_ALLOWANCE = 2000


def _get_groq_client() -> Groq:
    # [GROQ] setup — GROQ_API_KEY; leave live so uncommenting call_llm works
    global _groq_client
    if _groq_client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise Exception("Groq call failed")
        _groq_client = Groq(api_key=api_key)
    return _groq_client


def _get_openai_client() -> OpenAI:
    # [OPENAI] setup — OPENAI_API_KEY → api.openai.com; leave live for toggle
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("OpenAI call failed")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def _get_openrouter_client() -> OpenAI:
    # [OPENROUTER] setup — OPENROUTER_API_KEY → openrouter.ai/api/v1
    global _openrouter_client
    if _openrouter_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise Exception("OpenRouter call failed")
        _openrouter_client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://toposcribe.local",
                "X-Title": "TopoScribe AI",
            },
        )
    return _openrouter_client


def _resolve_openai_model(env_var: str) -> str:
    # [OPENROUTER] only — maps gpt-5.5 → openai/gpt-5.5; [OPENAI] uses short id
    raw = (os.getenv(env_var) or OPENAI_FALLBACK_MODEL).strip()
    if raw.startswith("openai/") or raw.startswith("qwen/"):
        return raw
    if raw.startswith("gpt-5"):
        return f"openai/{raw}"
    return raw


def _model_basename(model: str) -> str:
    return model.split("/")[-1]


def _requires_default_params(model: str) -> bool:
    return _model_basename(model).startswith(_FIXED_TEMPERATURE_MODEL_PREFIXES)


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
    extra_body: Optional[Dict[str, Any]] = None,
):
    messages = [{"role": "user", "content": prompt}]
    kwargs: Dict[str, Any] = {}

    if reasoning_effort is not None:
        kwargs["reasoning_effort"] = reasoning_effort
    if extra_body:
        kwargs["extra_body"] = extra_body
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
    # [OPENAI] Platform chat.completions (planning / escalation)
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


def _call_openrouter(
    prompt: str,
    model: str,
    temperature: float,
    max_tokens: int,
    reasoning_effort: Optional[ReasoningEffort] = None,
) -> str:
    # [OPENROUTER] chat.completions for all live tiers
    client = _get_openrouter_client()
    extra_body: Dict[str, Any] = {}
    create_effort: Optional[ReasoningEffort] = None

    if reasoning_effort is not None:
        if _requires_default_params(model):
            create_effort = reasoning_effort
        else:
            extra_body["reasoning"] = {"effort": reasoning_effort}

    try:
        response = _openai_create(
            client,
            model,
            prompt,
            temperature,
            max_tokens,
            reasoning_effort=create_effort,
            extra_body=extra_body or None,
        )
    except Exception as e:
        raise Exception(f"OpenRouter call failed: {str(e)}")

    choice = response.choices[0]
    content = choice.message.content or ""
    if not content.strip():
        raise Exception(
            f"OpenRouter call failed: {model} returned no content "
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
            PRIMARY_MAX_OUTPUT_TOKENS
            if tier == "primary"
            else LLM_MAX_OUTPUT_TOKENS
        )

    # --- REPORT (Groq + OpenAI) 
    # if tier == "primary":
    #     return _call_groq(
    #         prompt, GROQ_DEFAULT_MODEL, temperature, max_tokens, reasoning_effort
    #     )
    # if tier == "planning":
    #     return _call_openai(
    #         prompt,
    #         (os.getenv("OPENAI_PLANNING_MODEL") or OPENAI_FALLBACK_MODEL),
    #         temperature, max_tokens, reasoning_effort,
    #     )
    # if tier == "escalated":
    #     return _call_openai(
    #         prompt,
    #         (os.getenv("OPENAI_ESCALATION_MODEL") or OPENAI_FALLBACK_MODEL),
    #         temperature, max_tokens, reasoning_effort,
    #     )
    # raise ValueError(f"Unknown LLM tier: {tier!r}")

    # --- LIVE (OpenRouter) 
    if tier == "primary":
        return _call_openrouter(
            prompt, OPENROUTER_PRIMARY_MODEL, temperature, max_tokens, reasoning_effort
        )
    if tier == "planning":
        return _call_openrouter(
            prompt,
            _resolve_openai_model("OPENAI_PLANNING_MODEL"),
            temperature, max_tokens, reasoning_effort,
        )
    if tier == "escalated":
        return _call_openrouter(
            prompt,
            _resolve_openai_model("OPENAI_ESCALATION_MODEL"),
            temperature, max_tokens, reasoning_effort,
        )
    raise ValueError(f"Unknown LLM tier: {tier!r}")
