"""Topology agent quality-gate, escalation, and no-blind-retry tests."""
import json

import pytest

from app.agents import topology_agent
from app.agents.topology_agent import (
    MAX_TOPOLOGY_RETRIES,
    _build_topology_prompt,
    _missing_department_reason,
    _parse_and_validate_topology,
    _scope_reason,
    _sparse_reason,
    topology_node,
)

DESIGN_PLAN = {
    "departments": [
        {"name": "IT", "users": 20, "vlan_id": 10},
        {"name": "OP", "users": 20, "vlan_id": 20},
    ]
}


def _valid_topology_dict():
    """Router + core switch + one access switch and host per department."""
    return {
        "nodes": [
            {"id": "R1", "type": "router", "label": "Router", "interfaces": [], "config": {}},
            {"id": "SW_CORE", "type": "switch", "label": "Core Switch", "interfaces": [], "config": {}},
            {
                "id": "SW_IT",
                "type": "switch",
                "label": "IT Access Switch",
                "interfaces": [],
                "config": {"vlan_id": 10, "vlan_name": "IT"},
            },
            {
                "id": "SW_OP",
                "type": "switch",
                "label": "OP Access Switch",
                "interfaces": [],
                "config": {"vlan_id": 20, "vlan_name": "OP"},
            },
            {
                "id": "H_IT",
                "type": "host",
                "label": "IT Host",
                "interfaces": [{"name": "eth0", "ip": "192.168.10.10", "mask": "255.255.255.192"}],
                "config": {"vlan_id": 10, "vlan_name": "IT"},
            },
            {
                "id": "H_OP",
                "type": "host",
                "label": "OP Host",
                "interfaces": [{"name": "eth0", "ip": "192.168.20.10", "mask": "255.255.255.192"}],
                "config": {"vlan_id": 20, "vlan_name": "OP"},
            },
        ],
        "links": [
            {"id": "l1", "source": "R1", "target": "SW_CORE", "bandwidth": 1000},
            {"id": "l2", "source": "SW_CORE", "target": "SW_IT", "bandwidth": 1000},
            {"id": "l3", "source": "SW_CORE", "target": "SW_OP", "bandwidth": 1000},
            {"id": "l4", "source": "SW_IT", "target": "H_IT", "bandwidth": 1000},
            {"id": "l5", "source": "SW_OP", "target": "H_OP", "bandwidth": 1000},
        ],
        "protocols": [],
        "metadata": {"vlans": [{"id": 10, "name": "IT"}, {"id": 20, "name": "OP"}]},
    }


def _sparse_topology_dict():
    return {
        "nodes": [
            {"id": "R1", "type": "router", "label": "Router", "interfaces": [], "config": {}},
            {"id": "SW1", "type": "switch", "label": "Switch", "interfaces": [], "config": {}},
        ],
        "links": [{"id": "l1", "source": "R1", "target": "SW1", "bandwidth": 1000}],
        "metadata": {"vlans": [{"id": 10, "name": "IT"}, {"id": 20, "name": "OP"}]},
    }


def _state(retry_count=0, agent_trace=None):
    return {
        "design_plan": DESIGN_PLAN,
        "topology_retry_count": retry_count,
        "agent_trace": agent_trace or [],
    }


class _Recorder:
    """Stand-in for call_llm that records the prompt/tier it was asked for."""

    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def __call__(self, prompt, *, tier, **kwargs):
        self.calls.append({"prompt": prompt, "tier": tier})
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


@pytest.fixture
def patch_llm(monkeypatch):
    def _apply(payload):
        recorder = _Recorder(payload)
        monkeypatch.setattr(topology_agent, "call_llm", recorder)
        return recorder

    return _apply


# --- reason strings (no longer plain booleans) --------------------------------


def test_sparse_reason_reports_counts():
    reason = _sparse_reason(_sparse_topology_dict(), DESIGN_PLAN)
    assert reason is not None
    assert "2 nodes" in reason and "2 department(s)" in reason


def test_sparse_reason_none_for_valid_topology():
    assert _sparse_reason(_valid_topology_dict(), DESIGN_PLAN) is None


def test_scope_reason_names_the_offending_department():
    topo = _valid_topology_dict()
    topo["metadata"]["vlans"].append({"id": 30, "name": "HR"})
    reason = _scope_reason(topo, DESIGN_PLAN)
    assert reason is not None
    assert "HR" in reason and "VLAN 30" in reason


def test_missing_department_reason_names_the_absent_department():
    topo = _valid_topology_dict()
    topo["metadata"]["vlans"] = [{"id": 10, "name": "IT"}]
    for node in topo["nodes"]:
        if node["id"] in ("SW_OP", "H_OP"):
            node["config"] = {}
    reason = _missing_department_reason(topo, DESIGN_PLAN)
    assert reason is not None
    assert "op" in reason.lower()


def test_parse_reason_carries_json_error_text():
    topology_dict, reasons = _parse_and_validate_topology("{not json", DESIGN_PLAN)
    assert topology_dict is None
    assert len(reasons) == 1
    assert reasons[0].startswith("Response was not valid JSON:")


def test_parse_and_validate_accepts_good_topology():
    raw = "```json\n" + json.dumps(_valid_topology_dict()) + "\n```"
    topology_dict, reasons = _parse_and_validate_topology(raw, DESIGN_PLAN)
    assert reasons == []
    assert topology_dict is not None


# --- prompt threading ---------------------------------------------------------


def test_prompt_has_no_rejection_block_without_prior_errors():
    prompt = _build_topology_prompt(DESIGN_PLAN, None)
    assert "REJECTED" not in prompt


def test_prompt_lists_prior_errors_when_retrying():
    prompt = _build_topology_prompt(DESIGN_PLAN, ["Missing departments: OP.", "VLAN 40 never created"])
    assert "REJECTED" in prompt
    assert "1. Missing departments: OP." in prompt
    assert "2. VLAN 40 never created" in prompt


# --- attempt / tier routing ---------------------------------------------------


def test_attempt_zero_uses_primary_tier(patch_llm):
    recorder = patch_llm(json.dumps(_valid_topology_dict()))
    result = topology_node(_state(retry_count=0))

    assert recorder.calls[0]["tier"] == "primary"
    assert result["topology_source"] == "groq"
    assert result["topology_quality_ok"] is True
    assert result["topology_retry_count"] == 0


@pytest.mark.parametrize("retry_count", [1, 2, 3])
def test_retries_escalate(patch_llm, retry_count):
    recorder = patch_llm(json.dumps(_valid_topology_dict()))
    result = topology_node(_state(retry_count=retry_count))

    assert recorder.calls[0]["tier"] == "escalated"
    assert result["topology_source"] == "openai_escalated"
    assert result["topology_quality_ok"] is True


def test_success_trace_records_attempt_and_tier(patch_llm):
    patch_llm(json.dumps(_valid_topology_dict()))
    result = topology_node(_state(retry_count=2))

    trace = result["agent_trace"][0]
    assert trace["agent"] == "topology"
    assert trace["model"] == "escalated"
    assert trace["attempt"] == 2
    assert trace["status"] == "success"


# --- no fallback before the retry budget is spent -----------------------------


@pytest.mark.parametrize("retry_count", [0, 1, 2])
def test_no_fallback_before_max_retries(patch_llm, retry_count):
    patch_llm(json.dumps(_sparse_topology_dict()))
    result = topology_node(_state(retry_count=retry_count))

    assert "topology" not in result
    assert result["topology_quality_ok"] is False
    assert result["topology_retry_count"] == retry_count + 1
    assert result.get("topology_source") is None
    assert "errors" not in result

    trace = result["agent_trace"][0]
    assert trace["status"] == "rejected"
    assert trace["attempt"] == retry_count
    assert "2 nodes" in trace["outcome"]


def test_fallback_only_at_max_retries(patch_llm):
    patch_llm(json.dumps(_sparse_topology_dict()))
    result = topology_node(_state(retry_count=MAX_TOPOLOGY_RETRIES))

    assert result["topology"] is not None
    assert result["topology_source"] == "deterministic_fallback"
    assert result["topology_quality_ok"] is False
    assert result["topology_retry_count"] == MAX_TOPOLOGY_RETRIES + 1
    assert result["agent_trace"][0]["status"] == "fallback"


def test_fallback_topology_covers_plan_departments(patch_llm):
    patch_llm("not json at all")
    result = topology_node(_state(retry_count=MAX_TOPOLOGY_RETRIES))

    labels = " ".join(n.label or "" for n in result["topology"].nodes)
    assert "IT" in labels and "OP" in labels


# --- no-blind-retry: prior reasons reach the next prompt ----------------------


def test_prior_errors_threaded_into_escalated_prompt(patch_llm):
    prior_trace = [
        {
            "agent": "topology",
            "model": "primary",
            "attempt": 0,
            "status": "rejected",
            "outcome": "Only 2 nodes for 2 department(s); expected at least 6.",
        }
    ]
    recorder = patch_llm(json.dumps(_valid_topology_dict()))
    topology_node(_state(retry_count=1, agent_trace=prior_trace))

    prompt = recorder.calls[0]["prompt"]
    assert "REJECTED" in prompt
    assert "1. Only 2 nodes for 2 department(s); expected at least 6." in prompt


def test_prior_errors_accumulate_across_attempts(patch_llm):
    """Drive attempts 0->3 in sequence the way Phase 5's graph loop will."""
    recorder = patch_llm(json.dumps(_sparse_topology_dict()))
    state = _state(retry_count=0)

    for _ in range(MAX_TOPOLOGY_RETRIES + 1):
        result = topology_node(state)
        state["topology_retry_count"] = result["topology_retry_count"]
        state["agent_trace"] = state["agent_trace"] + result["agent_trace"]

    tiers = [c["tier"] for c in recorder.calls]
    assert tiers == ["primary", "escalated", "escalated", "escalated"]

    # Each retry carries every earlier rejection, so no attempt repeats blindly.
    assert "REJECTED" not in recorder.calls[0]["prompt"]
    assert recorder.calls[1]["prompt"].count("Only 2 nodes") == 1
    assert recorder.calls[3]["prompt"].count("Only 2 nodes") == 3

    assert result["topology_source"] == "deterministic_fallback"


def test_success_trace_not_replayed_as_a_failure_reason(patch_llm):
    prior_trace = [
        {
            "agent": "topology",
            "model": "primary",
            "attempt": 0,
            "status": "success",
            "outcome": "accepted from groq",
        }
    ]
    recorder = patch_llm(json.dumps(_valid_topology_dict()))
    topology_node(_state(retry_count=1, agent_trace=prior_trace))

    assert "REJECTED" not in recorder.calls[0]["prompt"]


# --- provider errors ----------------------------------------------------------


def test_provider_error_is_recorded_and_retried(patch_llm):
    patch_llm(Exception("OpenAI call failed: rate limit"))
    result = topology_node(_state(retry_count=1))

    assert "topology" not in result
    assert result["topology_retry_count"] == 2
    assert "rate limit" in result["agent_trace"][0]["outcome"]
