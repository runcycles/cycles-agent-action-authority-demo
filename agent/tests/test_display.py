"""Tests for display.py — ActionResult and DemoState logic, no terminal needed."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from display import ActionResult, DemoState


def test_action_result_allowed():
    action = ActionResult(
        name="read_case",
        toolset="read-only",
        allowed=True,
        detail="Case data retrieved",
        cycles_response="200 ALLOW",
    )
    assert action.allowed is True
    assert action.cycles_response == "200 ALLOW"


def test_action_result_blocked():
    action = ActionResult(
        name="send_customer_email",
        toolset="customer-facing",
        allowed=False,
        detail="BudgetExceededError",
        cycles_response="409 BUDGET_EXCEEDED",
    )
    assert action.allowed is False


def test_demo_state_initial():
    state = DemoState(
        mode="GUARDED",
        case_id="4782",
        customer="Acme Corp",
        contact="Jane Lee",
        email="jane@acme.com",
        subject="Invoice discrepancy",
    )
    assert state.approved_count == 0
    assert state.blocked_count == 0
    assert state.finished is False
    assert state.error is None


def test_demo_state_counts():
    state = DemoState(
        mode="GUARDED",
        case_id="4782",
        customer="Acme Corp",
        contact="Jane Lee",
        email="jane@acme.com",
        subject="Invoice discrepancy",
    )
    state.actions.append(ActionResult("read_case", "read-only", True, "ok"))
    state.actions.append(ActionResult("append_note", "internal", True, "ok"))
    state.actions.append(ActionResult("send_email", "customer-facing", False, "blocked"))

    assert state.approved_count == 2
    assert state.blocked_count == 1


def test_demo_state_all_approved():
    state = DemoState(
        mode="UNGUARDED",
        case_id="4782",
        customer="Acme Corp",
        contact="Jane Lee",
        email="jane@acme.com",
        subject="Invoice discrepancy",
    )
    state.actions.append(ActionResult("read_case", None, True, "ok"))
    state.actions.append(ActionResult("send_email", None, True, "ok"))

    assert state.approved_count == 2
    assert state.blocked_count == 0
