"""
Rich-based terminal display for the action authority demo.
Shows a step-by-step action log with approve/deny status per action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text


@dataclass
class ActionResult:
    name: str
    toolset: Optional[str]  # None for local actions (no Cycles check)
    allowed: bool
    detail: str  # What happened (e.g. "Note added..." or "BudgetExceededError")
    cycles_response: Optional[str] = None  # e.g. "200 ALLOW" or "409 BUDGET_EXCEEDED"


@dataclass
class DemoState:
    mode: str  # "UNGUARDED" or "GUARDED"
    case_id: str
    customer: str
    contact: str
    email: str
    subject: str
    actions: list[ActionResult] = field(default_factory=list)
    finished: bool = False
    error: Optional[str] = None

    @property
    def approved_count(self) -> int:
        return sum(1 for a in self.actions if a.allowed)

    @property
    def blocked_count(self) -> int:
        return sum(1 for a in self.actions if not a.allowed)


class DemoDisplay:
    """Renders the step-by-step action log using Rich panels."""

    def __init__(self, state: DemoState) -> None:
        self.state = state
        self.console = Console()

    def print_header(self) -> None:
        s = self.state
        style = "red" if s.mode == "UNGUARDED" else "green"

        lines: list[Text] = []
        lines.append(Text.assemble(("Customer:  ", "bold"), s.customer, (f" ({s.email})", "dim")))
        lines.append(Text.assemble(("Subject:   ", "bold"), s.subject))
        lines.append(Text.assemble(("Agent:     ", "bold"), "support-bot"))
        lines.append(Text.assemble(("Mode:      ", "bold"), (s.mode, f"bold {style}")))

        self.console.print(Panel(
            Group(*lines),
            title=f"[bold]Support Case #{s.case_id}[/bold]",
            border_style=style,
        ))
        self.console.print()

    def print_action_log(self) -> None:
        s = self.state
        style = "red" if s.mode == "UNGUARDED" else "green"

        lines: list[Text] = []

        for action in s.actions:
            lines.append(Text(""))

            # Action header line
            if action.allowed:
                marker = Text("  \u2713 ", style="bold green")
            else:
                marker = Text("  \u2717 ", style="bold red")

            header = Text()
            header.append_text(marker)
            header.append(action.name, style="bold")
            if action.toolset:
                header.append(f"  [{action.toolset}]", style="dim")
            lines.append(header)

            # Cycles response line (if applicable)
            if action.cycles_response:
                resp_style = "green" if action.allowed else "red"
                lines.append(Text(f"    POST /v1/reservations \u2192 {action.cycles_response}", style=resp_style))

            # Detail line
            if action.allowed:
                lines.append(Text(f"    {action.detail}", style="dim"))
            else:
                lines.append(Text(f"    {action.detail}", style="red bold"))

        lines.append(Text(""))

        self.console.print(Panel(
            Group(*lines),
            title="[bold]Action Log[/bold]",
            border_style=style,
        ))

    def print_result(self) -> None:
        s = self.state
        style = "red" if s.mode == "UNGUARDED" else "green"

        lines: list[Text] = []

        if s.error:
            lines.append(Text(f"Error: {s.error}", style="red bold"))
        elif s.blocked_count > 0:
            lines.append(Text(
                "Cycles blocked the customer email before it was sent.",
                style="bold orange1",
            ))
            lines.append(Text(
                "Internal actions proceeded. Customer-facing action not approved for autonomous execution.",
                style="dim",
            ))
        else:
            if s.mode == "UNGUARDED":
                lines.append(Text(
                    "All actions executed \u2014 including the customer email.",
                    style="red bold",
                ))
                lines.append(Text(
                    "In production: no authorization gate existed. The email went out unchecked.",
                    style="red",
                ))
            else:
                lines.append(Text("All actions approved.", style="green bold"))

        lines.append(Text(""))
        a_word = "action" if s.approved_count == 1 else "actions"
        b_word = "action" if s.blocked_count == 1 else "actions"
        lines.append(Text(
            f"{s.approved_count} {a_word} approved \u00b7 {s.blocked_count} {b_word} blocked",
            style="bold",
        ))

        self.console.print(Panel(
            Group(*lines),
            title=f"[bold]Result \u2014 {s.mode}[/bold]",
            border_style=style,
        ))
