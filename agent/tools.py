"""
Mock support tools. No real CRM, email service, or ticketing system.

Each tool simulates a 200ms latency and returns a realistic string.
The cost math is real — the tool authorization is the point of the demo.
"""
from __future__ import annotations

import time

ACTION_LATENCY_S: float = 0.2
COST_PER_ACTION_MICROCENTS: int = 1_000_000  # $0.01 per action

CASE = {
    "case_id": "4782",
    "customer": "Acme Corp",
    "contact": "Jane Lee",
    "email": "jane@acme.com",
    "subject": "Invoice discrepancy",
    "description": "Invoice for March shows $847 but contract says $720.",
    "status": "Open",
    "priority": "High",
}

CUSTOMER_REPLY = (
    "Hi Jane,\n\n"
    "Thank you for reaching out. We've identified a discrepancy between your\n"
    "March invoice ($847) and your contract rate ($720). We're investigating\n"
    "this now and will follow up within 24 hours with a corrected invoice.\n\n"
    "Best regards,\n"
    "Support Bot"
)


def read_case(case_id: str) -> dict:
    time.sleep(ACTION_LATENCY_S)
    return dict(CASE)


def append_internal_note(case_id: str, note: str) -> str:
    time.sleep(ACTION_LATENCY_S)
    return f"Note added to case #{case_id}: {note}"


def update_crm_status(case_id: str, old_status: str, new_status: str) -> str:
    time.sleep(ACTION_LATENCY_S)
    return f"Case #{case_id} status: {old_status} → {new_status}"


def send_customer_email(case_id: str, to: str, subject: str, body: str) -> str:
    time.sleep(ACTION_LATENCY_S)
    return f"Email sent to {to}: {subject}"
