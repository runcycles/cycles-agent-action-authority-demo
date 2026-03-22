# Cycles Action Authority Demo

An agent can use CRM, notes, and email — but Cycles decides which actions are allowed before execution.

Same agent. Same tools. The next unapproved action never executes.

## The scenario

A support automation agent handles customer case #4782 (invoice discrepancy). The agent's workflow has four steps:

1. **Read case** — load case details from the CRM
2. **Append internal note** — log an internal investigation note
3. **Update CRM status** — change the case from Open to Investigating
4. **Send customer email** — reply to the customer with an update

Steps 1–3 are internal, low-risk operations. Step 4 is a consequential, customer-facing action. In production, you want a human to approve outbound emails before they go out. Cycles enforces this by only provisioning budgets for approved toolsets.

Without Cycles, all four steps execute — including the email. With Cycles, the server returns `409 BUDGET_EXCEEDED` before the email send can proceed, and the agent reports: "Email blocked — not approved for autonomous execution. Escalated to human review."

No real CRM, email service, or ticketing system is used. All tools are mocked locally. The action authority is real.

## Run it

Prerequisites: Docker Compose v2+, Python 3.10+, `curl`

```bash
git clone https://github.com/runcycles/cycles-agent-action-authority-demo
cd cycles-agent-action-authority-demo
python3 -m venv .venv && source .venv/bin/activate
pip install -r agent/requirements.txt
./demo.sh
```

That's it. The script starts the Cycles stack (Redis + server + admin), provisions a tenant with toolset-scoped budgets, then runs both modes back to back.

Run a single mode:

```bash
./demo.sh unguarded    # without Cycles (all actions execute)
./demo.sh guarded      # with Cycles (email blocked)
./demo.sh both         # both back to back (default)
```

Re-runs just work — the script resets the stack automatically to ensure a clean state.

Stop the stack when done:

```bash
./teardown.sh
```

### Windows (WSL)

The demo runs on Windows 11 via WSL. Install [Docker Desktop for Windows](https://docs.docker.com/get-docker/) with the WSL 2 backend enabled (the default), then inside your WSL terminal:

```bash
sudo apt update && sudo apt install -y python3-full curl
git clone https://github.com/runcycles/cycles-agent-action-authority-demo
cd cycles-agent-action-authority-demo
python3 -m venv .venv && source .venv/bin/activate
pip install -r agent/requirements.txt
./demo.sh
```

Docker Desktop shares the daemon between Windows and WSL automatically — no extra configuration needed.

> **Note:** Ubuntu 23.04+ requires `python3-full` (not just `python3`) so that venvs get their own pip. Without it, even `pip` inside a venv hits the PEP 668 "externally-managed-environment" error.

### First run notes

The first run pulls three Docker images (~200MB total). You'll see Docker's pull progress. Subsequent runs start in seconds.

## What you'll see

![Cycles Action Authority Demo](demo.gif)

### Without Cycles

All four actions execute with green checkmarks — including the customer email. The final panel reads:
> *"All actions executed — including the customer email. In production: no authorization gate existed. The email went out unchecked."*

### With Cycles (action authority)

The first three actions execute with green checkmarks. The fourth (send email) shows a red X. The final panel reads:
> *"Cycles blocked the customer email before it was sent. Internal actions proceeded. Customer-facing action not approved for autonomous execution."*

### Expected output

```
⚡ Cycles — Action Authority Demo

Starting Cycles stack...
Stack is up.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE 1: Without Cycles
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭──────────── Support Case #4782 ───────────────╮
│ Customer:  Acme Corp (jane@acme.com)          │
│ Subject:   Invoice shows $847, contract $720  │
│ Agent:     support-bot                        │
│ Mode:      UNGUARDED                          │
╰───────────────────────────────────────────────╯

╭──────────── Action Log ───────────────────────╮
│  ✓ read_case                                  │
│  ✓ append_internal_note  [internal-notes]     │
│  ✓ update_crm_status     [crm-updates]        │
│  ✓ send_customer_email   [send-email]         │
╰───────────────────────────────────────────────╯

╭──────────── Result — UNGUARDED ───────────────╮
│ All actions executed — including the email.   │
│ 4 actions approved · 0 actions blocked        │
╰───────────────────────────────────────────────╯

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  MODE 2: With Cycles (action authority)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

╭──────────── Support Case #4782 ───────────────╮
│ Customer:  Acme Corp (jane@acme.com)          │
│ Subject:   Invoice shows $847, contract $720  │
│ Agent:     support-bot                        │
│ Mode:      GUARDED                            │
╰───────────────────────────────────────────────╯

╭──────────── Action Log ───────────────────────╮
│  ✓ read_case                                  │
│    Loaded case #4782 — Acme Corp              │
│                                               │
│  ✓ append_internal_note  [internal-notes]     │
│    POST /v1/reservations → 200 ALLOW          │
│    Billing discrepancy: $847 vs $720          │
│                                               │
│  ✓ update_crm_status     [crm-updates]        │
│    POST /v1/reservations → 200 ALLOW          │
│    Status: Open → Investigating               │
│                                               │
│  ✗ send_customer_email   [send-email]         │
│    POST /v1/reservations → 409 BUDGET_EXCEEDED│
│    Email blocked — not approved autonomously. │
╰───────────────────────────────────────────────╯

╭──────────── Result — GUARDED ─────────────────╮
│ Cycles blocked the customer email before it   │
│ was sent.                                     │
│ 3 actions approved · 1 action blocked         │
╰───────────────────────────────────────────────╯

Demo complete.
  Swagger UI:   http://localhost:7878/swagger-ui.html
  Stop stack:   ./teardown.sh
```

## The code change

The diff between `agent/unguarded.py` and `agent/guarded.py` is exactly this:

```python
# --- Import the SDK ---
from runcycles import BudgetExceededError, CyclesClient, CyclesConfig, cycles, set_default_client

# --- Initialize the client ---
config = CyclesConfig(
    base_url=os.environ["CYCLES_BASE_URL"],
    api_key=os.environ["CYCLES_API_KEY"],
    tenant=os.environ["CYCLES_TENANT"],
    agent="support-bot",
)
set_default_client(CyclesClient(config))

# --- Add three decorators with toolset scoping ---
@cycles(estimate=COST, action_kind="tool.notes", action_name="append-note", toolset="internal-notes")
def append_internal_note(...): ...

@cycles(estimate=COST, action_kind="tool.crm", action_name="update-status", toolset="crm-updates")
def update_crm_status(...): ...

@cycles(estimate=COST, action_kind="tool.email", action_name="send-reply", toolset="send-email")
def send_customer_email(...): ...

# --- Catch the budget exception ---
except BudgetExceededError:
    # email blocked — not approved for autonomous execution
```

Three decorators. One except. The next unapproved action never executes.

## How it works

The key mechanism is **toolset-scoped budgets**. The provisioning script creates budgets for:

| Toolset | Budget | Result |
|---------|--------|--------|
| `internal-notes` | $1.00 | ✓ Agent can append notes |
| `crm-updates` | $1.00 | ✓ Agent can update CRM |
| `send-email` | *none* | ✗ No budget → 409 |

When the `@cycles` decorator tries to reserve budget in a scope with no budget, the Cycles server returns `409 BUDGET_EXCEEDED`. The decorator raises `BudgetExceededError`, and the action never executes.

This means you control agent capabilities at the budget provisioning level — no code changes needed to approve or revoke a tool. Add a budget for `send-email` and the agent can send emails. Remove it and the agent can't.

## Why this matters

Static tool allowlists can't adapt at runtime. API keys grant blanket access. Role-based permissions don't distinguish between "the agent CAN send email" and "this specific run SHOULD send email." Cycles enforces a runtime decision **before** each consequential action — without changing agent code.

## Next steps

After running the demo, explore how to add Cycles to your own application:

- [What is Cycles?](https://runcycles.io/quickstart/what-is-cycles) — understand the problem and the solution
- [End-to-End Tutorial](https://runcycles.io/quickstart/end-to-end-tutorial) — zero to a working budget-guarded app in 10 minutes
- [Adding Cycles to an Existing App](https://runcycles.io/how-to/adding-cycles-to-an-existing-application) — incremental adoption guide
- [Full Documentation](https://runcycles.io) — complete docs at runcycles.io

## Links

- Protocol: https://github.com/runcycles/cycles-protocol
- Server:   https://github.com/runcycles/cycles-server
- Python:   `pip install runcycles`
- Java:     `io.runcycles:cycles-client-java-spring`
- Node.js:  `npm install runcycles`
