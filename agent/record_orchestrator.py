"""
Drives a single end-to-end recording: unguarded run (4 actions execute,
including the email), hard cut to a "MODE 2" interstitial, then guarded
run that blocks the customer email at the send-email toolset, ending on
a green two-column summary card.

Invoked by demo.tape inside vhs. Assumes the Cycles stack is up and
CYCLES_BASE_URL / CYCLES_API_KEY / CYCLES_TENANT are exported (record.sh
handles that before launching vhs).

Mirrors agent/record_orchestrator.py in the runaway demo: real code
paths, not a render-only stand-in. The unguarded segment calls the raw
tools from tools.py; the guarded segment calls the @cycles-decorated
wrappers from guarded.py — the same wrappers ./demo.sh exercises live.
"""
from __future__ import annotations

import time

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from display import ActionResult, DemoDisplay, DemoState
from tools import (
    CASE,
    CUSTOMER_REPLY,
    read_case,
    append_internal_note,
    update_crm_status,
    send_customer_email,
)
from guarded import (
    _setup as _guarded_setup,
    append_internal_note as _guarded_append_note,
    update_crm_status as _guarded_update_status,
    send_customer_email as _guarded_send_email,
)
from runcycles import BudgetExceededError

# Per-step delay between actions so each step is readable in the GIF.
# The live demo doesn't have a delay (panels render at the end), but for
# the recording we want each ✓/✗ to land visibly.
STEP_DELAY_S = 0.8

# Hold timings, mirroring the runaway demo's pacing.
UNGUARDED_FINAL_HOLD_S = 2.0
INTERSTITIAL_HOLD_S = 1.5
BUDGET_EXCEEDED_HOLD_S = 3.5
SUMMARY_HOLD_S = 5.0


def _print_mode_banner(console: Console, line1: str, line2: str | None = None,
                       border_style: str = "red") -> None:
    rule = "━" * 44
    console.print(rule, style=border_style)
    console.print(f"  {line1}", style=f"bold {border_style}")
    if line2:
        console.print(f"  {line2}", style=f"dim {border_style}")
    console.print(rule, style=border_style)
    console.print()


def _new_state(mode: str) -> DemoState:
    return DemoState(
        mode=mode,
        case_id=CASE["case_id"],
        customer=CASE["customer"],
        contact=CASE["contact"],
        email=CASE["email"],
        subject="Invoice shows $847, contract says $720",
    )


def run_unguarded(console: Console) -> DemoState:
    state = _new_state("UNGUARDED")
    display = DemoDisplay(state)
    display.print_header()

    # Step 1: read_case (local — no Cycles check either way).
    case = read_case(CASE["case_id"])
    step = ActionResult(
        name="read_case",
        toolset=None,
        allowed=True,
        detail=f"Loaded case #{case['case_id']} — {case['customer']}",
    )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    # Step 2: append_internal_note.
    note = "Billing discrepancy: $847 invoiced vs $720 contract. Investigating."
    append_internal_note(case["case_id"], note)
    step = ActionResult(
        name="append_internal_note",
        toolset="internal-notes",
        allowed=True,
        detail=note,
    )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    # Step 3: update_crm_status.
    update_crm_status(case["case_id"], "Open", "Investigating")
    step = ActionResult(
        name="update_crm_status",
        toolset="crm-updates",
        allowed=True,
        detail="Status: Open → Investigating",
    )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    # Step 4: send_customer_email — UNGUARDED, goes out unchecked.
    send_customer_email(
        case["case_id"],
        CASE["email"],
        "Re: Invoice discrepancy — case #4782",
        CUSTOMER_REPLY,
    )
    step = ActionResult(
        name="send_customer_email",
        toolset="send-email",
        allowed=True,
        detail=f"Email sent to {CASE['email']}",
    )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    state.finished = True
    display.print_result()
    return state


def run_guarded(console: Console) -> DemoState:
    _guarded_setup()
    state = _new_state("GUARDED")
    display = DemoDisplay(state)
    display.print_header()

    # Step 1: read_case (local).
    case = read_case(CASE["case_id"])
    step = ActionResult(
        name="read_case",
        toolset=None,
        allowed=True,
        detail=f"Loaded case #{case['case_id']} — {case['customer']}",
    )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    # Step 2: append_internal_note (toolset budget allows).
    note = "Billing discrepancy: $847 invoiced vs $720 contract. Investigating."
    _guarded_append_note(case["case_id"], note)
    step = ActionResult(
        name="append_internal_note",
        toolset="internal-notes",
        allowed=True,
        detail=note,
        cycles_response="200 ALLOW",
    )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    # Step 3: update_crm_status (toolset budget allows).
    _guarded_update_status(case["case_id"], "Open", "Investigating")
    step = ActionResult(
        name="update_crm_status",
        toolset="crm-updates",
        allowed=True,
        detail="Status: Open → Investigating",
        cycles_response="200 ALLOW",
    )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    # Step 4: send_customer_email — toolset budget is $0, expect 409.
    try:
        _guarded_send_email(
            case["case_id"],
            CASE["email"],
            "Re: Invoice discrepancy — case #4782",
            CUSTOMER_REPLY,
        )
        step = ActionResult(
            name="send_customer_email",
            toolset="send-email",
            allowed=True,
            detail=f"Email sent to {CASE['email']}",
            cycles_response="200 ALLOW",
        )
    except BudgetExceededError:
        step = ActionResult(
            name="send_customer_email",
            toolset="send-email",
            allowed=False,
            detail="Email blocked — not approved for autonomous execution. "
                   "Escalated to human review.",
            cycles_response="409 BUDGET_EXCEEDED",
        )
    state.actions.append(step)
    display.print_action_step(step)
    time.sleep(STEP_DELAY_S)

    state.finished = True
    display.print_result()
    return state


def main() -> None:
    console = Console()

    _print_mode_banner(console, "MODE 1: WITHOUT CYCLES", border_style="red")
    unguarded = run_unguarded(console)
    time.sleep(UNGUARDED_FINAL_HOLD_S)

    console.clear()
    interstitial = Panel(
        Text.from_markup(
            "[bold green]MODE 2: WITH CYCLES[/bold green]\n"
            "[dim]same agent · same workflow[/dim]"
        ),
        border_style="green",
        padding=(1, 4),
    )
    console.print(interstitial, justify="center")
    time.sleep(INTERSTITIAL_HOLD_S)
    console.clear()

    _print_mode_banner(
        console,
        "MODE 2: WITH CYCLES (action authority)",
        border_style="green",
    )
    guarded = run_guarded(console)

    time.sleep(BUDGET_EXCEEDED_HOLD_S)
    console.clear()
    summary = DemoDisplay.build_summary_panel(unguarded, guarded)
    console.print(summary)
    time.sleep(SUMMARY_HOLD_S)


if __name__ == "__main__":
    main()
