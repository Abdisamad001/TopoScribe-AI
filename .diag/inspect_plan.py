"""Read-only diagnostic: what does planning's post-processing capture from the two test inputs?"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.agents.planning_agent import (  # noqa: E402
    _apply_sme_defaults,
    _explicit_departments_from_user,
    _requested_users_each,
    _requested_department_count,
    _named_departments_in_text,
    _is_user_delegation,
)

CASES = [
    ("A: bare placeholder", "2 routers connected to a switch with 3 PCs", []),
    (
        "B: placeholder + 'HR, IT'",
        "2 routers connected to a switch with 3 PCs",
        [
            {"role": "user", "content": "2 routers connected to a switch with 3 PCs"},
            {"role": "assistant", "content": "Please list your departments (e.g., HR, IT, Finance)."},
            {"role": "user", "content": "HR, IT"},
        ],
    ),
    ("C: 10 users each", "HR, IT, Finance, 10 users each", []),
]

for title, user_input, history in CASES:
    print("=" * 70)
    print(title)
    print("  input:", repr(user_input))
    print("  named_departments_in_text :", _named_departments_in_text(user_input))
    print("  explicit_departments      :", _explicit_departments_from_user(user_input, history))
    print("  requested_users_each      :", _requested_users_each(user_input))
    print("  requested_department_count:", _requested_department_count(user_input))
    print("  is_user_delegation        :", _is_user_delegation(user_input, history))
    plan = _apply_sme_defaults({}, user_input, history)
    print("  design_plan after _apply_sme_defaults:")
    print(json.dumps(plan, indent=4))
