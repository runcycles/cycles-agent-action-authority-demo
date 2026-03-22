#!/usr/bin/env python3
"""
Render the demo output without Docker or Cycles.
Used for recording the demo GIF via asciinema.
Simulates both modes with step-by-step timing.
"""
from __future__ import annotations

import sys
import time

sys.path.insert(0, "agent")

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

from display import ActionResult, DemoDisplay, DemoState
from tools import CASE

STEP_DELAY = 0.8  # Pause between steps for readability in GIF

console = Console()


def print_action_step(action: ActionResult, style: str) -> None:
    """Print a single action step inline (not in a panel)."""
    if action.allowed:
        marker = Text("  \u2713 ", style="bold green")
    else:
        marker = Text("  \u2717 ", style="bold red")

    header = Text()
    header.append_text(marker)
    header.append(action.name, style="bold")
    if action.toolset:
        header.append(f"  [{action.toolset}]", style="dim")
    console.print(header)

    if action.cycles_response:
        resp_style = "green" if action.allowed else "red"
        console.print(Text(f"    POST /v1/reservations \u2192 {action.cycles_response}", style=resp_style))

    if action.allowed:
        console.print(Text(f"    {action.detail}", style="dim"))
    else:
        console.print(Text(f"    {action.detail}", style="red bold"))

    console.print()


def run_mode(mode: str) -> None:
    state = DemoState(
        mode=mode,
        case_id=CASE["case_id"],
        customer=CASE["customer"],
        contact=CASE["contact"],
        email=CASE["email"],
        subject="Invoice shows $847, contract says $720",
    )
    display = DemoDisplay(state)
    display.print_header()

    steps = []

    # Step 1: Read case
    steps.append(ActionResult(
        name="read_case",
        toolset=None,
        allowed=True,
        detail=f"Loaded case #{CASE['case_id']} \u2014 {CASE['customer']}",
    ))

    # Step 2: Append internal note
    steps.append(ActionResult(
        name="append_internal_note",
        toolset="internal-notes",
        allowed=True,
        detail="Billing discrepancy: $847 invoiced vs $720 contract. Investigating.",
        cycles_response="200 ALLOW" if mode == "GUARDED" else None,
    ))

    # Step 3: Update CRM status
    steps.append(ActionResult(
        name="update_crm_status",
        toolset="crm-updates",
        allowed=True,
        detail="Status: Open \u2192 Investigating",
        cycles_response="200 ALLOW" if mode == "GUARDED" else None,
    ))

    # Step 4: Send customer email
    if mode == "GUARDED":
        steps.append(ActionResult(
            name="send_customer_email",
            toolset="send-email",
            allowed=False,
            detail="Email blocked \u2014 not approved for autonomous execution. Escalated to human review.",
            cycles_response="409 BUDGET_EXCEEDED",
        ))
    else:
        steps.append(ActionResult(
            name="send_customer_email",
            toolset="send-email",
            allowed=True,
            detail=f"Email sent to {CASE['email']}",
        ))

    # Print each step with a delay
    style = "red" if mode == "UNGUARDED" else "green"
    for step in steps:
        time.sleep(STEP_DELAY)
        state.actions.append(step)
        print_action_step(step, style)

    # Final result panel
    time.sleep(0.5)
    display.print_result()


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "both"

    print()
    print("\u26a1 Cycles \u2014 Action Authority Demo")
    print()

    if mode in ("unguarded", "both"):
        print("\u2501" * 43)
        print("  MODE 1: Without Cycles")
        print("\u2501" * 43)
        print()
        run_mode("UNGUARDED")

    if mode == "both":
        time.sleep(1.5)

    if mode in ("guarded", "both"):
        print()
        print("\u2501" * 43)
        print("  MODE 2: With Cycles (action authority)")
        print("\u2501" * 43)
        print()
        run_mode("GUARDED")

    print()
    print("Demo complete.")
    print("  Re-run:       ./demo.sh")
    print("  Stop stack:   ./teardown.sh")


if __name__ == "__main__":
    main()
