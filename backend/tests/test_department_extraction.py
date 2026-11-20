"""Regression tests
"""
import pytest

from app.agents.planning_agent import (
    _apply_sme_defaults,
    _explicit_departments_from_user,
    _extract_department_names,
    _infer_departments_from_free_text,
    _is_user_delegation,
    _requested_department_count,
)
from app.utils.dept_labels import is_plausible_department_name


def _names(plan):
    return [d["name"] for d in plan["departments"]]


# --- defect 1: "N-department <Org>" 


def test_org_descriptor_is_not_captured_as_a_department():

    assert _infer_departments_from_free_text("Design a 4-department SME with 50 users each") == []
    assert _explicit_departments_from_user("Design a 4-department SME with 50 users each", []) == []


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Design a 4-department SME with 50 users each", 4),
        ("we need a 3-department office", 3),
        ("build a four departments company", 4),
        ("set up 10 departments", 10),
        ("a network for our office", 0),
        ("departments IT and OP", 0),
    ],
)
def test_requested_department_count(text, expected):
    assert _requested_department_count(text) == expected


def test_stated_count_is_honoured_when_no_names_given():
    plan = _apply_sme_defaults({}, "Design a 4-department SME with 50 users each", [])
    names = _names(plan)
    assert len(names) == 4
    assert "SME" not in names
    assert all(d["users"] == 50 for d in plan["departments"])
    assert len({d["vlan_id"] for d in plan["departments"]}) == 4


def test_spaced_count_form_still_reads_the_list():
   
    assert _infer_departments_from_free_text("4 departments IT, Finance") == ["IT", "Finance"]


def test_named_departments_beat_a_smaller_stated_count():
    plan = _apply_sme_defaults({}, "two departments HR, IT and Finance", [])
    assert _names(plan) == ["HR", "IT", "Finance"]


# --- defect 2: lowercase and multi-word names 


def test_lowercase_department_is_extracted_alongside_an_acronym():
    """The Phase 7 failure: 'finance and JS with five Pcs' yielded ['JS']."""
    assert _explicit_departments_from_user("finance and JS with five Pcs", []) == ["Finance", "JS"]


@pytest.mark.parametrize(
    "text,expected",
    [
        ("finance and JS with five Pcs", ["Finance", "JS"]),
        ("we have sales, marketing and legal", ["Sales", "Marketing", "Legal"]),
        ("hr and it only", ["HR", "IT"]),
        ("Finance, Human Resources and Engineering", ["Finance", "Human Resources", "Engineering"]),
        ("accounting plus QA", ["Accounting", "QA"]),
    ],
)
def test_varied_phrasings_extract_correctly(text, expected):
    assert _explicit_departments_from_user(text, []) == expected


def test_request_verbs_never_become_departments():
    """'Design'/'network'/'office' head most prompts and must not be departments."""
    assert _explicit_departments_from_user("Design a campus network for our office", []) == []
    assert _is_user_delegation("Design a campus network, please recommend everything", []) is True


def test_pcs_quantity_is_not_a_department():
    assert "Pcs" not in _explicit_departments_from_user("finance and JS with five Pcs", [])





def test_correct_llm_proposal_survives_a_narrower_deterministic_match():
    """The regression: a valid model list must not be replaced by a smaller match."""
    llm_plan = {
        "departments": [
            {"name": "Finance", "users": 5, "vlan_id": 10},
            {"name": "JS", "users": 5, "vlan_id": 20},
        ]
    }
    plan = _apply_sme_defaults(llm_plan, "finance and JS with five Pcs", [])
    assert _names(plan) == ["Finance", "JS"]
   
    assert [d["users"] for d in plan["departments"]] == [5, 5]


def test_hallucinated_departments_are_still_dropped():
    llm_plan = {
        "departments": [
            {"name": "HR", "users": 20, "vlan_id": 10},
            {"name": "IT", "users": 20, "vlan_id": 20},
            {"name": "Finance", "users": 20, "vlan_id": 30},
            {"name": "OP", "users": 20, "vlan_id": 40},
        ]
    }
    plan = _apply_sme_defaults(llm_plan, "Design a network of office to departments IT and OP", [])
    assert _names(plan) == ["IT", "OP"]


def test_department_the_model_missed_is_added_back():
    llm_plan = {"departments": [{"name": "JS", "users": 5, "vlan_id": 10}]}
    plan = _apply_sme_defaults(llm_plan, "finance and JS with five Pcs", [])
    assert _names(plan) == ["JS", "Finance"]


def test_vlan_ids_stay_unique_after_merging():
    llm_plan = {"departments": [{"name": "JS", "users": 5, "vlan_id": 10}]}
    plan = _apply_sme_defaults(llm_plan, "finance and JS with five Pcs", [])
    ids = [d["vlan_id"] for d in plan["departments"]]
    assert len(ids) == len(set(ids))
    assert all(2 <= i <= 4094 for i in ids)


def test_delegated_request_keeps_the_models_invented_names():
    """With no user-named departments there is nothing to ground against."""
    llm_plan = {
        "departments": [
            {"name": "Warehouse", "users": 20, "vlan_id": 10},
            {"name": "Dispatch", "users": 20, "vlan_id": 20},
        ]
    }
    plan = _apply_sme_defaults(llm_plan, "Design a logistics depot network, you choose", [])
    assert _names(plan) == ["Warehouse", "Dispatch"]


# --- multi-turn


def test_multi_turn_answer_extracts_both_departments():
    history = [
        {"role": "user", "content": "design network design for two offices"},
        {"role": "assistant", "content": "Please list your departments (e.g., HR, IT, Finance)."},
    ]
    assert _explicit_departments_from_user("finance and JS with five Pcs", history) == ["Finance", "JS"]


def test_assistant_examples_still_ignored_with_the_wider_vocabulary():
    """The broader matcher must not start reading HR/IT/Finance out of our own prompt."""
    history = [
        {"role": "assistant", "content": "Please list your departments (e.g., HR, IT, Finance)."},
    ]
    assert _explicit_departments_from_user("finance and JS with five Pcs", history) == ["Finance", "JS"]


# --- ghost department: trailing ", with N PCs each" must not become a name ----


@pytest.mark.parametrize(
    "text,expected",
    [
        ("departments HR, IT, with 5 PCs each", ["HR", "IT"]),
        ("departments: HR, IT, Finance, with 5 PCs each", ["HR", "IT", "Finance"]),
        ("departments HR, IT, with 10 employees, with 3 PCs each", ["HR", "IT"]),
        ("departments Sales and Marketing having 5 computers each", ["Sales", "Marketing"]),
        ("departments HR and IT using 8 hosts each", ["HR", "IT"]),
        ("departments Legal, Finance including 4 workstations each", ["Legal", "Finance"]),
        ("departments HR, IT, Finance, 20 users each", ["HR", "IT", "Finance"]),
    ],
)
def test_trailing_qualifier_is_not_a_department(text, expected):
    names = _extract_department_names(text)
    assert names == expected
    assert "with" not in [n.lower() for n in names]
    plan_names = _names(_apply_sme_defaults({}, text, []))
    assert plan_names == expected
    assert "with" not in [n.lower() for n in plan_names]


def test_closed_class_single_words_are_not_plausible_departments():
    for word in ("with", "having", "using", "including", "and", "for", "of"):
        assert is_plausible_department_name(word) is False
    assert is_plausible_department_name("IT") is True
    assert is_plausible_department_name("Human Resources") is True
