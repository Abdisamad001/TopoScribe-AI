"""Unit tests for Topology escalated-tier reasoning_effort threshold (Lever 1/reasoning effort)."""
import pytest

from app.agents.topology_agent import (
    TOPOLOGY_LOW_EFFORT_MAX_DEPARTMENTS,
    _department_count,
    _escalated_reasoning_effort,
)


def _plan(n: int):
    return {
        "mode": "departmental",
        "departments": [
            {"name": f"D{i}", "users": 20, "vlan_id": 10 * (i + 1)} for i in range(n)
        ],
    }


def test_threshold_constant_is_five():
    assert TOPOLOGY_LOW_EFFORT_MAX_DEPARTMENTS == 5


@pytest.mark.parametrize(
    "n,expected",
    [
        (1, "low"),
        (5, "low"),   # at the boundary
        (6, None),    # just above — model default (medium)
        (10, None),
        (15, None),
    ],
)
def test_escalated_reasoning_effort_by_department_count(n, expected):
    assert _escalated_reasoning_effort(_plan(n)) == expected
    assert _department_count(_plan(n)) == n


def test_empty_plan_is_at_or_below_threshold():
    # 0 departments ≤ 5 → low (harmless; escalated path still has a plan in practice)
    assert _escalated_reasoning_effort({}) == "low"
    assert _escalated_reasoning_effort({"departments": []}) == "low"
