"""Tests for the Part 2"""
import csv

import pytest

from app.api import design

# Redirects the run log so tests never touch the real dataset
@pytest.fixture
def run_log(tmp_path, monkeypatch):

    path = tmp_path / "scenario_runs_part2.csv"
    monkeypatch.setattr(design, "RUN_LOG_PATH", path)
    return path


def _rows(path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# --- run log 


def test_headers_extend_part1_with_three_columns(run_log):
    design._append_run_row(True, 0, True, 0, 8.0, "Success", topology_source="groq")
    with run_log.open(newline="", encoding="utf-8") as f:
        headers = next(csv.reader(f))
    assert headers[:7] == [
        "Run #",
        "Requirements Clear?",
        "Questions Asked?",
        "Design Generated?",
        "Retries",
        "Runtime (Seconds)",
        "Result",
    ]
    assert headers[7:] == ["Topology Source", "Topology Retries", "Escalated"]


def test_run_numbering_restarts_at_one(run_log):
    for _ in range(3):
        design._append_run_row(True, 0, True, 0, 1.0, "Success", topology_source="groq")
    assert [r["Run #"] for r in _rows(run_log)] == ["1", "2", "3"]


def test_writes_target_the_part2_file_by_default():
    assert design.RUN_LOG_PATH.name == "scenario_runs_part2.csv"


@pytest.mark.parametrize(
    "source,expected",
    [
        ("groq", "No"),
        ("openai_escalated", "Yes"),
        ("deterministic_fallback", "Yes"),
    ],
)
def test_escalated_flag_derived_from_source(run_log, source, expected):
    design._append_run_row(True, 0, True, 0, 1.0, "Success", topology_source=source)
    assert _rows(run_log)[0]["Escalated"] == expected


def test_run_without_topology_is_not_counted_as_escalated(run_log):
    """A clarification run has no source; absent must not read as 'not groq'."""
    design._append_run_row(False, 1, False, 0, 8.7, "Needs Clarification")
    row = _rows(run_log)[0]
    assert row["Topology Source"] == ""
    assert row["Escalated"] == "No"


def test_topology_retries_recorded_separately_from_validation_retries(run_log):
    design._append_run_row(
        True, 0, True, 2, 40.0, "Success",
        topology_source="openai_escalated", topology_retries=3,
    )
    row = _rows(run_log)[0]
    assert row["Retries"] == "2"
    assert row["Topology Retries"] == "3"


# --- agent_trace

def test_compact_trace_keeps_only_documented_keys():
    out = design._compact_trace({
        "agent_trace": [{
            "agent": "topology",
            "model": "escalated",
            "attempt": 1,
            "status": "success",
            "outcome": "accepted",
            "internal_scratch": "must not leak",
        }]
    })
    assert out == [{
        "agent": "topology",
        "model": "escalated",
        "attempt": 1,
        "outcome": "accepted",
        "status": "success",
    }]


def test_compact_trace_tolerates_missing_and_malformed_entries():
    assert design._compact_trace({}) == []
    assert design._compact_trace({"agent_trace": None}) == []
    out = design._compact_trace({"agent_trace": ["nope", {"agent": "topology"}]})
    assert len(out) == 1
    assert out[0]["agent"] == "topology"
    assert out[0]["outcome"] is None
