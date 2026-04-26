"""
Rich-based terminal display for the action authority demo.
Shows a step-by-step action log with approve/deny status per action.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
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

    def print_action_step(self, action: ActionResult) -> None:
        """Print a single action step inline (not in a panel).

        Used by the recording orchestrator and render_demo.py to stream
        each step into the terminal as the agent executes it, so the GIF
        shows the action log filling in over time. The end-of-run
        ``print_action_log`` panel is the alternative path used by
        ``unguarded.py`` / ``guarded.py`` for the live demo.
        """
        if action.allowed:
            marker = Text("  ✓ ", style="bold green")
        else:
            marker = Text("  ✗ ", style="bold red")

        header = Text()
        header.append_text(marker)
        header.append(action.name, style="bold")
        if action.toolset:
            header.append(f"  [{action.toolset}]", style="dim")
        self.console.print(header)

        if action.cycles_response:
            resp_style = "green" if action.allowed else "red"
            self.console.print(Text(
                f"    POST /v1/reservations → {action.cycles_response}",
                style=resp_style,
            ))

        if action.allowed:
            self.console.print(Text(f"    {action.detail}", style="dim"))
        else:
            self.console.print(Text(f"    {action.detail}", style="red bold"))

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

    @staticmethod
    def build_summary_panel(unguarded: "DemoState", guarded: "DemoState") -> Panel:
        """Two-column green summary card shown at the end of the recording.

        Structurally parallel to the runaway demo's summary card: same
        "Same agent \u00b7 same workflow \u00b7 two outcomes" frame, but the
        contrast is binary (email sent vs blocked) rather than dollar
        projections. The visceral payload here is action authority:
        per-toolset budgets stop the consequential action without
        touching the internal ones.
        """
        col_w = 24

        def line(label: str, value: str, style: str) -> Text:
            return Text(
                f"{label.ljust(col_w - len(value))}{value}",
                style=style,
            )

        t = Table.grid(padding=(0, 4), expand=True)
        t.add_column(justify="center", ratio=1)
        t.add_column(justify="center", ratio=1)

        u_total = len(unguarded.actions)
        u_blocked = unguarded.blocked_count
        g_total = len(guarded.actions)
        g_blocked = guarded.blocked_count

        left = Group(
            Text("Without Cycles", style="bold red"),
            Text(f"{u_total - u_blocked} / {u_total} actions executed",
                 style="bold red"),
            Text("(including the customer email)", style="dim red"),
            Text(""),
            Text("Per-toolset authority:", style="bold red"),
            line("internal-notes",  "\u25b6 ran",  "red"),
            line("crm-updates",     "\u25b6 ran",  "red"),
            line("send-email",      "\u25b6 SENT", "red bold"),
            Text(""),
            Text("no authorization gate", style="red"),
        )
        right = Group(
            Text("With Cycles", style="bold green"),
            Text(f"{g_total - g_blocked} / {g_total} actions executed \u00b7 "
                 f"{g_blocked} blocked", style="bold green"),
            Text("(customer email blocked before send)", style="dim green"),
            Text(""),
            Text("Per-toolset authority:", style="bold green"),
            line("internal-notes",  "\u2713 ALLOW", "green"),
            line("crm-updates",     "\u2713 ALLOW", "green"),
            line("send-email",      "\u2717 DENY",  "green bold"),
            Text(""),
            Text("escalated to human review", style="green"),
        )
        t.add_row(left, right)

        body = Group(
            t,
            Text(""),
            Text(
                "Action authority: per-toolset budgets \u2014 set $0 to deny, "
                "$N to allow. No agent-code change needed.",
                style="dim",
                justify="center",
            ),
        )

        return Panel(
            body,
            title="[bold green]Same agent. Same workflow. Two outcomes.[/bold green]",
            border_style="green",
        )
