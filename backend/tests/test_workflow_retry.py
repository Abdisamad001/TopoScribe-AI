import json

import pytest
from langgraph.graph import StateGraph, END

from app.graph.state import NetworkDesignState
from app.graph.workflow import (
    MAX_VALIDATION_RETRIES,
    should_end_or_continue,
    should_retry_topology,
    workflow as production_workflow,
)
from app.agents.topology_agent import MAX_TOPOLOGY_RETRIES
from app.models.network import Topology


def _topology():
    return Topology(
        nodes=[{"id": "R1", "type": "router", "label": "Router"}],
        links=[],
    )


def _rejected(attempt):
    return {
        "topology_quality_ok": False,
        "topology_retry_count": attempt + 1,
        "agent_trace": [{"agent": "topology", "attempt": attempt, "status": "rejected", "outcome": "too sparse"}],
    }


def _succeeded(attempt, source):
    return {
        "topology": _topology(),
        "topology_source": source,
        "topology_quality_ok": True,
        "topology_retry_count": attempt,
        "agent_trace": [{"agent": "topology", "attempt": attempt, "status": "success", "outcome": "accepted"}],
    }


def _fell_back(attempt):
    return {
        "topology": _topology(),
        "topology_source": "deterministic_fallback",
        "topology_quality_ok": False,
        "topology_retry_count": attempt + 1,
        "agent_trace": [{"agent": "topology", "attempt": attempt, "status": "fallback", "outcome": "too sparse"}],
    }


def _fallback_threw(attempt):
    """topology_node's catastrophic branch: budget spent and the SME layout raised."""
    return {
        "topology_quality_ok": False,
        "topology_retry_count": attempt + 1,
        "errors": ["Topology generation failed: too sparse"],
        "agent_trace": [{"agent": "topology", "attempt": attempt, "status": "failed", "outcome": "fallback also failed"}],
    }


def _build_graph(topology_script, validation_results=None):
    """
    Rebuilds the production wiring with scripted agents so routing and
    termination can be exercised without any LLM calls.
    """
    calls = {"topology": 0, "config": 0, "validation": 0}

    def fake_topology(state):
        i = calls["topology"]
        calls["topology"] += 1
        return topology_script[i]

    def fake_config(state):
        calls["config"] += 1
        return {"configurations": {"R1": {}}}

    def fake_validation(state):
        i = calls["validation"]
        calls["validation"] += 1
        if validation_results is None:
            return {"validation_result": {"status": "passed"}}
        return validation_results(i, state)

    g = StateGraph(NetworkDesignState)
    g.add_node("topology_gen", fake_topology)
    g.add_node("config", fake_config)
    g.add_node("validation", fake_validation)
    g.set_entry_point("topology_gen")
    g.add_conditional_edges(
        "topology_gen",
        should_retry_topology,
        {"config": "config", "topology_gen": "topology_gen", "end_failed": END},
    )
    g.add_edge("config", "validation")
    g.add_conditional_edges(
        "validation", should_end_or_continue, {"config": "config", "end": END}
    )
    return g.compile(), calls


def _initial_state():
    return {
        "topology": None,
        "topology_retry_count": 0,
        "topology_quality_ok": True,
        "errors": [],
        "retry_count": 0,
        "agent_trace": [],
    }


# router unit behaviour 


def test_router_sends_usable_topology_to_config():
    state = {"topology": _topology(), "topology_quality_ok": True, "topology_retry_count": 0}
    assert should_retry_topology(state) == "config"


def test_router_sends_fallback_topology_to_config():
    state = {
        "topology": _topology(),
        "topology_quality_ok": False,
        "topology_retry_count": MAX_TOPOLOGY_RETRIES + 1,
    }
    assert should_retry_topology(state) == "config"


@pytest.mark.parametrize("retry_count", [1, 2, 3])
def test_router_loops_back_while_budget_remains(retry_count):
    state = {"topology": None, "topology_quality_ok": False, "topology_retry_count": retry_count}
    assert should_retry_topology(state) == "topology_gen"


def test_router_ends_when_budget_spent_without_topology():
    state = {
        "topology": None,
        "topology_quality_ok": False,
        "topology_retry_count": MAX_TOPOLOGY_RETRIES + 1,
    }
    assert should_retry_topology(state) == "end_failed"


# graph termination 


def test_success_on_first_attempt():
    graph, calls = _build_graph([_succeeded(0, "groq")])
    result = graph.invoke(_initial_state())

    assert calls["topology"] == 1
    assert calls["config"] == 1
    assert result["topology_source"] == "groq"
    assert result["validation_result"]["status"] == "passed"


def test_success_after_two_rejections():
    graph, calls = _build_graph(
        [_rejected(0), _rejected(1), _succeeded(2, "openai_escalated")]
    )
    result = graph.invoke(_initial_state())

    assert calls["topology"] == 3
    assert calls["config"] == 1
    assert result["topology_source"] == "openai_escalated"
    assert result["topology_retry_count"] == 2
    assert len(result["agent_trace"]) == 3


def test_fallback_after_full_retry_budget():
    graph, calls = _build_graph(
        [_rejected(0), _rejected(1), _rejected(2), _fell_back(3)]
    )
    result = graph.invoke(_initial_state())

    assert calls["topology"] == MAX_TOPOLOGY_RETRIES + 1
    assert calls["config"] == 1
    assert result["topology_source"] == "deterministic_fallback"
    assert result["topology_quality_ok"] is False
    assert result["topology"] is not None


def test_fallback_exception_ends_without_reaching_config():
    graph, calls = _build_graph(
        [_rejected(0), _rejected(1), _rejected(2), _fallback_threw(3)]
    )
    result = graph.invoke(_initial_state())

    assert calls["topology"] == MAX_TOPOLOGY_RETRIES + 1
    assert calls["config"] == 0
    assert result.get("topology") is None
    assert result["errors"] == ["Topology generation failed: too sparse"]

#topology not producing graph 
def test_topology_loop_cannot_outrun_the_recursion_limit():
    
    script = [_rejected(i) for i in range(10)]
    graph, calls = _build_graph(script)
    graph.invoke(_initial_state())

    assert calls["topology"] == MAX_TOPOLOGY_RETRIES + 1
    assert calls["config"] == 0


# validation -> config cap 


def _always_failing_validation(i, state):
    return {
        "errors": [f"validation failure {i + 1}"],
        "validation_result": {"status": "failed", "errors": ["bad"]},
        "retry_count": int(state.get("retry_count", 0)) + 1,
    }


def test_validation_loop_stops_at_the_cap():
    graph, calls = _build_graph(
        [_succeeded(0, "groq")], validation_results=_always_failing_validation
    )
    result = graph.invoke(_initial_state())

    # First config pass plus MAX_VALIDATION_RETRIES
    assert calls["config"] == MAX_VALIDATION_RETRIES + 1
    assert calls["validation"] == MAX_VALIDATION_RETRIES + 1
    assert result["retry_count"] == MAX_VALIDATION_RETRIES + 1
    assert len(result["errors"]) == MAX_VALIDATION_RETRIES + 1


def test_validation_router_ends_once_retries_are_spent():
    state = {"errors": ["boom"], "retry_count": MAX_VALIDATION_RETRIES + 1, "validation_result": {"status": "failed"}}
    assert should_end_or_continue(state) == "end"


def test_validation_router_still_retries_within_budget():
    state = {"errors": ["boom"], "retry_count": 1, "validation_result": {"status": "failed"}}
    assert should_end_or_continue(state) == "config"


def test_fatal_validation_still_ends_immediately():
    state = {"errors": ["boom"], "retry_count": 0, "validation_result": {"status": "failed_fatal"}}
    assert should_end_or_continue(state) == "end"


# real nodes inside the real graph 


def _plan_json():
    return json.dumps(
        {
            "requirements_clear": True,
            "design_plan": {
                "departments": [
                    {"name": "IT", "users": 20, "vlan_id": 10},
                    {"name": "OP", "users": 20, "vlan_id": 20},
                ]
            },
        }
    )


def _sparse_json():
    return json.dumps(
        {
            "nodes": [
                {"id": "R1", "type": "router", "label": "Router"},
                {"id": "SW1", "type": "switch", "label": "Switch"},
            ],
            "links": [{"id": "l1", "source": "R1", "target": "SW1"}],
        }
    )


def _full_json():
    nodes = [
        {"id": "R1", "type": "router", "label": "Router", "interfaces": [], "config": {}},
        {"id": "SW_CORE", "type": "switch", "label": "Core Switch", "interfaces": [], "config": {}},
    ]
    links = [{"id": "l0", "source": "R1", "target": "SW_CORE", "bandwidth": 1000}]
    for i, (dept, vlan) in enumerate((("IT", 10), ("OP", 20))):
        nodes.append({
            "id": f"SW_{dept}", "type": "switch", "label": f"{dept} Access Switch",
            "interfaces": [], "config": {"vlan_id": vlan, "vlan_name": dept},
        })
        nodes.append({
            "id": f"H_{dept}", "type": "host", "label": f"{dept} Host",
            "interfaces": [{"name": "eth0", "ip": f"192.168.{vlan}.10", "mask": "255.255.255.192"}],
            "config": {"vlan_id": vlan, "vlan_name": dept},
        })
        links.append({"id": f"lc{i}", "source": "SW_CORE", "target": f"SW_{dept}", "bandwidth": 1000})
        links.append({"id": f"lh{i}", "source": f"SW_{dept}", "target": f"H_{dept}", "bandwidth": 1000})
    return json.dumps({
        "nodes": nodes,
        "links": links,
        "protocols": [],
        "metadata": {"vlans": [{"id": 10, "name": "IT"}, {"id": 20, "name": "OP"}]},
    })


def test_real_topology_node_escalates_inside_the_production_graph(monkeypatch):
   
    from app.agents import planning_agent, topology_agent
    from app.graph.workflow import app as production_app

    monkeypatch.setattr(planning_agent, "call_llm", lambda prompt, **kw: _plan_json())

    script = [_sparse_json(), _sparse_json(), _full_json()]
    tiers = []

    def fake_topology_llm(prompt, *, tier, **kw):
        tiers.append(tier)
        return script[len(tiers) - 1]

    monkeypatch.setattr(topology_agent, "call_llm", fake_topology_llm)

    state = _initial_state()
    state.update({
        "user_input": "Design a network for one office with departments IT and OP",
        "conversation_history": [],
        "requirements_clear": False,
        "clarifying_questions": None,
        "design_plan": None,
        "configurations": None,
        "validation_result": None,
        "cisco_configs": None,
        "report": None,
    })
    result = production_app.invoke(state)

    assert tiers == ["primary", "escalated", "escalated"]
    assert result["topology_source"] == "openai_escalated"
    assert result["topology_retry_count"] == 2
    assert result["topology_quality_ok"] is True
    assert [n.id for n in result["topology"].nodes] == [
        "R1", "SW_CORE", "SW_IT", "H_IT", "SW_OP", "H_OP"
    ]

    # The two rejections no retry repeated blindly.
    rejections = [e for e in result["agent_trace"] if e.get("status") == "rejected"]
    assert len(rejections) == 2


# production wiring


def test_production_graph_has_no_linear_topology_edge():
    assert ("topology_gen", "config") not in production_workflow.edges


def test_production_graph_wires_the_topology_gate():
    branch = next(iter(production_workflow.branches["topology_gen"].values()))
    assert branch.ends == {
        "config": "config",
        "topology_gen": "topology_gen",
        "end_failed": "__end__",
    }
