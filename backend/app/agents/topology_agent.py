from app.graph.state import NetworkDesignState
from app.utils.llm import call_llm
from app.generators.topology_layout import (
    DEFAULT_COLUMN_SPACING_PX,
    HOST_CARD_WIDTH_PX,
    _annotate_representative_host_user_counts,
    _build_topology_prompt,
    _count_roles_in_nodes,
    _departmental_column_spacing,
    _fallback_topology_dict,
    _finalize_topology,
    _host_center_gap,
    _missing_department_reason,
    _missing_host_link_reason,
    _parse_and_validate_topology,
    _scope_reason,
    _sparse_reason,
    _topology_department_scope_invalid,
    merge_vlan_metadata,
)
from typing import Dict, Any, List

# Escalated retries allowed after the initial primary-tier attempt.
MAX_TOPOLOGY_RETRIES = 3


def _prior_topology_errors(state: NetworkDesignState) -> List[str]:
    """Rejection reasons recorded by earlier topology attempts in this run."""
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


def topology_node(state: NetworkDesignState) -> Dict[str, Any]:
    """
    Topology Agent: Converts design plan into network topology.

    Attempt 0 runs on the primary tier. Attempts 1-3 escalate, each prompted with
    the specific reasons earlier attempts were rejected. The deterministic layout
    is only used once the retry budget is exhausted.
    """
    design_plan = state.get("design_plan") or {}
    attempt = int(state.get("topology_retry_count", 0) or 0)
    tier = "primary" if attempt == 0 else "escalated"
    prior_errors = _prior_topology_errors(state)

    prompt = _build_topology_prompt(design_plan, prior_errors)

    try:
        response_text = call_llm(prompt, tier=tier)
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
                source = "groq" if attempt == 0 else "openai_escalated"
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
        # Hand control back to the graph so the next attempt can escalate with
        # this reason in its prompt. No fallback while retries remain.
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

    # Retry budget exhausted — fall back to the deterministic SME layout.
    try:
        topology_dict = _fallback_topology_dict(design_plan)
        merge_vlan_metadata(design_plan, topology_dict)
        topology = _finalize_topology(topology_dict, design_plan)
    except Exception as e:
        return {
            "topology_quality_ok": False,
            "topology_retry_count": attempt + 1,
            "errors": [f"Topology generation failed: {reason_text}"],
            "agent_trace": [_trace(tier, attempt, "failed", f"{reason_text} | fallback also failed: {e}")],
            "conversation_history": [
                {"role": "assistant", "content": f"Error: {reason_text}"}
            ],
        }

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
