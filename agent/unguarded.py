"""
Unguarded agent — no action authority.

All tool calls execute unconditionally.
The customer email goes out without any approval gate.
"""
from __future__ import annotations

from display import ActionResult, DemoDisplay, DemoState
from tools import CASE, CUSTOMER_REPLY, read_case, append_internal_note, update_crm_status, send_customer_email


def run() -> None:
    state = DemoState(
        mode="UNGUARDED",
        case_id=CASE["case_id"],
        customer=CASE["customer"],
        contact=CASE["contact"],
        email=CASE["email"],
        subject=f"Invoice shows $847, contract says $720",
    )
    display = DemoDisplay(state)
    display.print_header()

    # Step 1: Read case (local)
    case = read_case(CASE["case_id"])
    state.actions.append(ActionResult(
        name="read_case",
        toolset=None,
        allowed=True,
        detail=f"Loaded case #{case['case_id']} — {case['customer']}",
    ))

    # Step 2: Append internal note
    note = "Billing discrepancy: $847 invoiced vs $720 contract. Investigating."
    result = append_internal_note(case["case_id"], note)
    state.actions.append(ActionResult(
        name="append_internal_note",
        toolset="internal-notes",
        allowed=True,
        detail=note,
    ))

    # Step 3: Update CRM status
    result = update_crm_status(case["case_id"], "Open", "Investigating")
    state.actions.append(ActionResult(
        name="update_crm_status",
        toolset="crm-updates",
        allowed=True,
        detail="Status: Open \u2192 Investigating",
    ))

    # Step 4: Send customer email — no gate, goes out directly
    result = send_customer_email(
        case["case_id"],
        CASE["email"],
        "Re: Invoice discrepancy — case #4782",
        CUSTOMER_REPLY,
    )
    state.actions.append(ActionResult(
        name="send_customer_email",
        toolset="send-email",
        allowed=True,
        detail=f"Email sent to {CASE['email']}",
    ))

    state.finished = True
    display.print_action_log()
    display.print_result()


if __name__ == "__main__":
    run()
