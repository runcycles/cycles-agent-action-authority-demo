"""
Guarded agent — action authority enforced by Cycles.

Identical workflow to unguarded.py, but each tool call is wrapped
with @cycles using a toolset parameter. The Cycles server only has
budgets for approved toolsets (internal-notes, crm-updates).
The send-email toolset has no budget — Cycles blocks it.

Three decorators. One except. Only approved actions execute.
"""
from __future__ import annotations

import os
import sys

from runcycles import BudgetExceededError, CyclesClient, CyclesConfig, cycles, set_default_client
from runcycles.exceptions import CyclesError

from display import ActionResult, DemoDisplay, DemoState
from tools import (
    CASE, COST_PER_ACTION_MICROCENTS, CUSTOMER_REPLY,
    read_case as _read_case,
    append_internal_note as _append_note,
    update_crm_status as _update_status,
    send_customer_email as _send_email,
)


def _setup():
    missing = [v for v in ("CYCLES_BASE_URL", "CYCLES_API_KEY", "CYCLES_TENANT") if v not in os.environ]
    if missing:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}", file=sys.stderr)
        print("  These are set automatically by demo.sh.", file=sys.stderr)
        print("  Run the demo with: ./demo.sh guarded", file=sys.stderr)
        sys.exit(1)

    config = CyclesConfig(
        base_url=os.environ["CYCLES_BASE_URL"],
        api_key=os.environ["CYCLES_API_KEY"],
        tenant=os.environ["CYCLES_TENANT"],
        agent="support-bot",
    )
    set_default_client(CyclesClient(config))


# --- Three decorated tools, each with its own toolset scope ---

@cycles(estimate=COST_PER_ACTION_MICROCENTS, action_kind="tool.notes", action_name="append-note", toolset="internal-notes")
def append_internal_note(case_id: str, note: str) -> str:
    return _append_note(case_id, note)


@cycles(estimate=COST_PER_ACTION_MICROCENTS, action_kind="tool.crm", action_name="update-status", toolset="crm-updates")
def update_crm_status(case_id: str, old_status: str, new_status: str) -> str:
    return _update_status(case_id, old_status, new_status)


@cycles(estimate=COST_PER_ACTION_MICROCENTS, action_kind="tool.email", action_name="send-reply", toolset="send-email")
def send_customer_email(case_id: str, to: str, subject: str, body: str) -> str:
    return _send_email(case_id, to, subject, body)


def run() -> None:
    _setup()
    state = DemoState(
        mode="GUARDED",
        case_id=CASE["case_id"],
        customer=CASE["customer"],
        contact=CASE["contact"],
        email=CASE["email"],
        subject="Invoice shows $847, contract says $720",
    )
    display = DemoDisplay(state)
    display.print_header()

    exit_error: str | None = None

    try:
        # Step 1: Read case (local — no Cycles check needed)
        case = _read_case(CASE["case_id"])
        state.actions.append(ActionResult(
            name="read_case",
            toolset=None,
            allowed=True,
            detail=f"Loaded case #{case['case_id']} \u2014 {case['customer']}",
        ))

        # Step 2: Append internal note (toolset: internal-notes — approved)
        note = "Billing discrepancy: $847 invoiced vs $720 contract. Investigating."
        append_internal_note(case["case_id"], note)
        state.actions.append(ActionResult(
            name="append_internal_note",
            toolset="internal-notes",
            allowed=True,
            detail=note,
            cycles_response="200 ALLOW",
        ))

        # Step 3: Update CRM status (toolset: crm-updates — approved)
        update_crm_status(case["case_id"], "Open", "Investigating")
        state.actions.append(ActionResult(
            name="update_crm_status",
            toolset="crm-updates",
            allowed=True,
            detail="Status: Open \u2192 Investigating",
            cycles_response="200 ALLOW",
        ))

        # Step 4: Send customer email (toolset: send-email — NOT approved)
        try:
            send_customer_email(
                case["case_id"],
                CASE["email"],
                "Re: Invoice discrepancy \u2014 case #4782",
                CUSTOMER_REPLY,
            )
            # If we get here, the action was unexpectedly allowed
            state.actions.append(ActionResult(
                name="send_customer_email",
                toolset="send-email",
                allowed=True,
                detail=f"Email sent to {CASE['email']}",
                cycles_response="200 ALLOW",
            ))
        except BudgetExceededError:
            state.actions.append(ActionResult(
                name="send_customer_email",
                toolset="send-email",
                allowed=False,
                detail="Email NOT sent \u2014 escalated to human for approval.",
                cycles_response="409 BUDGET_EXCEEDED",
            ))

    except CyclesError as e:
        err_str = str(e)
        if "Connection refused" in err_str or "timed out" in err_str.lower():
            state.error = f"connection error \u2014 {err_str}"
            exit_error = (
                f"\nERROR: Cannot reach Cycles server at {os.environ['CYCLES_BASE_URL']}\n"
                f"  Is the stack running?  docker compose ps\n"
                f"  Check server logs:     docker compose logs cycles-server"
            )
        else:
            state.error = f"unexpected error \u2014 {err_str}"
            exit_error = (
                f"\nERROR: Cycles error: {err_str}\n"
                f"  Check server logs: docker compose logs cycles-server"
            )

    state.finished = True
    display.print_action_log()
    display.print_result()

    if exit_error:
        print(exit_error, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
