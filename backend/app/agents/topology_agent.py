from app.graph.state import NetworkDesignState
from app.utils.llm import GROQ_PRIMARY_MAX_OUTPUT_TOKENS, call_llm
from app.generators.topology_layout import (
    _build_topology_prompt,
    _escalated_reasoning_effort,
    _fallback_topology_dict,
    _finalize_topology,
    _parse_and_validate_topology,
    merge_vlan_metadata,
)
from typing import Dict, Any, List

import langwatch

# Escalated retries 
MAX_TOPOLOGY_RETRIES = 3

# Rejection reasons recorded 
def _prior_topology_errors(state: NetworkDesignState) -> List[str]:
    
    out: List[str] = []
    for entry in state.get("agent_trace") or []:
        if not isinstance(entry, dict) or entry.get("agent") != "topology":
            continue
        outcome = entry.get("outcome")
        if outcome and entry.get("status") != "success":
            out.append(str(outcome))
    return out


def _trace(model: str, attempt: int, status: str, outcome: str) -> Dict[str, Any]:
    return {
        "agent": "topology",
        "model": model,
        "attempt": attempt,
        "status": status,
        "outcome": outcome,
    }


def _topology_span_meta(
    *,
    tier: str,
    effort: Any,
    attempt: int,
    topology_source: Any = None,
    gate_outcome: str,
    model_name: str = "",
) -> None:
    from app.utils.llm import OPENROUTER_GPT55_MODEL, OPENROUTER_PRIMARY_MODEL

    if not model_name:
        model_name = (
            OPENROUTER_PRIMARY_MODEL if tier == "primary" else OPENROUTER_GPT55_MODEL
        )
    langwatch.get_current_span().update(
        tier=tier,
        reasoning_effort=effort if effort is not None else "default",
        attempt=attempt,
        topology_source=topology_source if topology_source is not None else "",
        gate_outcome=gate_outcome,
        provider="openrouter",
        model=model_name,
    )


@langwatch.span(name="Topology Agent")
def topology_node(state: NetworkDesignState) -> Dict[str, Any]:
    design_plan = state.get("design_plan") or {}
    attempt = int(state.get("topology_retry_count", 0) or 0)
    tier = "primary" if attempt == 0 else "escalated"
    prior_errors = _prior_topology_errors(state)

    prompt = _build_topology_prompt(design_plan, prior_errors)

    # Primary (OpenRouter Qwen): reasoning_effort="none"
    # Escalated (OpenRouter GPT-5.5)
    if tier == "primary":
        effort = "none"
    else:
        effort = _escalated_reasoning_effort(design_plan)

    try:
        response_text = call_llm(
            prompt,
            tier=tier,
            reasoning_effort=effort,
            max_tokens=(
                GROQ_PRIMARY_MAX_OUTPUT_TOKENS if tier == "primary" else None
            ),
        )
    except Exception as e:
        reasons = [str(e)]
    else:
        topology_dict, reasons = _parse_and_validate_topology(response_text, design_plan)
        if topology_dict is not None:
            try:
                topology = _finalize_topology(topology_dict, design_plan)
            except Exception as e:
                reasons = [f"Topology failed schema validation: {e}"]
            else:
                # openrouter = primary Qwen; openrouter_escalated = GPT-5.5 via OpenRouter
                # (legacy rows may still say openai_escalated / groq)
                source = "openrouter" if attempt == 0 else "openrouter_escalated"
                _topology_span_meta(
                    tier=tier,
                    effort=effort,
                    attempt=attempt,
                    topology_source=source,
                    gate_outcome="accepted",
                )
                return {
                    "topology": topology,
                    "topology_source": source,
                    "topology_quality_ok": True,
                    "topology_retry_count": attempt,
                    "agent_trace": [_trace(tier, attempt, "success", f"accepted from {source}")],
                    "conversation_history": [
                        {
                            "role": "assistant",
                            "content": f"Topology generated successfully (attempt {attempt + 1}, {source}).",
                        }
                    ],
                }

    reason_text = " | ".join(reasons) if reasons else "Unknown topology failure."

    if attempt < MAX_TOPOLOGY_RETRIES:
       
        _topology_span_meta(
            tier=tier,
            effort=effort,
            attempt=attempt,
            topology_source=None,
            gate_outcome=f"rejected: {reason_text}",
        )
        return {
            "topology_quality_ok": False,
            "topology_retry_count": attempt + 1,
            "agent_trace": [_trace(tier, attempt, "rejected", reason_text)],
            "conversation_history": [
                {
                    "role": "assistant",
                    "content": f"Topology attempt {attempt + 1} rejected: {reason_text}",
                }
            ],
        }

    # Retry budget exhausted
    try:
        topology_dict = _fallback_topology_dict(design_plan)
        merge_vlan_metadata(design_plan, topology_dict)
        topology = _finalize_topology(topology_dict, design_plan)
    except Exception as e:
        _topology_span_meta(
            tier=tier,
            effort=effort,
            attempt=attempt,
            topology_source=None,
            gate_outcome=f"failed: {reason_text} | fallback also failed: {e}",
        )
        return {
            "topology_quality_ok": False,
            "topology_retry_count": attempt + 1,
            "errors": [f"Topology generation failed: {reason_text}"],
            "agent_trace": [_trace(tier, attempt, "failed", f"{reason_text} | fallback also failed: {e}")],
            "conversation_history": [
                {"role": "assistant", "content": f"Error: {reason_text}"}
            ],
        }

    _topology_span_meta(
        tier=tier,
        effort=effort,
        attempt=attempt,
        topology_source="deterministic_fallback",
        gate_outcome=f"fallback: {reason_text}",
    )
    return {
        "topology": topology,
        "topology_source": "deterministic_fallback",
        "topology_quality_ok": False,
        "topology_retry_count": attempt + 1,
        "agent_trace": [_trace(tier, attempt, "fallback", reason_text)],
        "conversation_history": [
            {
                "role": "assistant",
                "content": "Topology generated using built-in SME layout after "
                f"{attempt + 1} rejected attempts.",
            }
        ],
    }
