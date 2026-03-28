"""Tests for tools.py — mock support tools, no server needed."""
from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import (
    CASE,
    COST_PER_ACTION_MICROCENTS,
    CUSTOMER_REPLY,
    append_internal_note,
    read_case,
    send_customer_email,
    update_crm_status,
)


def test_case_has_required_fields():
    required = {"case_id", "customer", "contact", "email", "subject", "description", "status", "priority"}
    assert required.issubset(CASE.keys())


def test_read_case_returns_copy():
    result = read_case("4782")
    assert result == CASE
    # Ensure it's a copy, not the original
    result["status"] = "Modified"
    assert CASE["status"] == "Open"


def test_read_case_returns_dict():
    result = read_case("4782")
    assert isinstance(result, dict)
    assert result["case_id"] == "4782"
    assert result["customer"] == "Acme Corp"


def test_append_internal_note():
    result = append_internal_note("4782", "Investigating invoice discrepancy")
    assert "4782" in result
    assert "Investigating" in result


def test_update_crm_status():
    result = update_crm_status("4782", "Open", "In Progress")
    assert "4782" in result
    assert "Open" in result
    assert "In Progress" in result


def test_send_customer_email():
    result = send_customer_email("4782", "jane@acme.com", "Re: Invoice", "body text")
    assert "jane@acme.com" in result
    assert "Re: Invoice" in result


def test_customer_reply_is_string():
    assert isinstance(CUSTOMER_REPLY, str)
    assert len(CUSTOMER_REPLY) > 0
    assert "Jane" in CUSTOMER_REPLY


def test_cost_per_action_is_positive():
    assert COST_PER_ACTION_MICROCENTS > 0
