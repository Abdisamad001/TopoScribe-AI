"""Planning agent department scope, delegation, and label sanitization tests."""
import pytest

from app.agents.planning_agent import (
    _apply_sme_defaults,
    _ensure_default_departments,
    _explicit_departments_from_user,
    _is_user_delegation,
)
from app.agents.topology_agent import _topology_department_scope_invalid
from app.utils.dept_labels import is_plausible_department_name


def test_explicit_departments_override_llm_extras():
    user = "Design a network of office to departments IT and OP"
    llm_plan = {
        "departments": [
            {"name": "HR", "users": 20, "vlan_id": 10},
            {"name": "IT", "users": 20, "vlan_id": 20},
            {"name": "Finance", "users": 20, "vlan_id": 30},
            {"name": "OP", "users": 20, "vlan_id": 40},
        ]
    }
    plan = _apply_sme_defaults(llm_plan, user, [])
    names = [d["name"] for d in plan["departments"]]
    assert names == ["IT", "OP"]


def test_history_contamination_assistant_examples_ignored():
    user = "departments IT and OP"
    history = [
        {
            "role": "assistant",
            "content": "Please list your departments (e.g., HR, IT, Finance).",
        }
    ]
    plan = _apply_sme_defaults({}, user, history)
    names = [d["name"] for d in plan["departments"]]
    assert names == ["IT", "OP"]


def test_delegation_language_does_not_override_explicit_departments():
    user = "departments IT and OP, you decide the rest"
    assert _explicit_departments_from_user(user, []) == ["IT", "OP"]
    assert _is_user_delegation(user, []) is False

    plan = _apply_sme_defaults({}, user, [])
    names = [d["name"] for d in plan["departments"]]
    assert names == ["IT", "OP"]

    plan_with_defaults = _ensure_default_departments(plan)
    assert [d["name"] for d in plan_with_defaults["departments"]] == ["IT", "OP"]


def test_ensure_default_departments_only_when_empty():
    empty = _ensure_default_departments({})
    assert [d["name"] for d in empty["departments"]] == ["HR", "IT", "Finance"]

    explicit = _apply_sme_defaults({}, "departments IT and OP", [])
    unchanged = _ensure_default_departments(explicit)
    assert [d["name"] for d in unchanged["departments"]] == ["IT", "OP"]


def test_delegation_without_named_departments_still_detected():
    user = "Design a campus network, please recommend everything"
    assert _explicit_departments_from_user(user, []) == []
    assert _is_user_delegation(user, []) is True


def test_is_plausible_department_name_rejects_prose_fragments():
    assert is_plausible_department_name("IT") is True
    assert is_plausible_department_name("OP") is True
    assert is_plausible_department_name("e.g.") is False
    assert is_plausible_department_name("Finance). 2 departments HR") is False


def test_topology_department_scope_invalid_detects_extra_vlan():
    design_plan = {
        "departments": [
            {"name": "IT", "vlan_id": 10},
            {"name": "OP", "vlan_id": 20},
        ]
    }
    topology = {
        "nodes": [
            {"id": "R1", "type": "router", "label": "Router", "config": {}},
            {
                "id": "H1",
                "type": "host",
                "label": "HR Host",
                "config": {"vlan_id": 30, "vlan_name": "HR"},
            },
        ],
        "metadata": {"vlans": [{"id": 30, "name": "HR"}]},
    }
    assert _topology_department_scope_invalid(topology, design_plan) is True
