# AUDIT

Tracks intentional changes to the demo's recorded artifacts and the wiring
that produces them. The live demo behavior (`./demo.sh`) and the agent code
(`agent/unguarded.py`, `agent/guarded.py`, `agent/tools.py`) are
intentionally unchanged by anything below — only the recording pipeline.

## 2026-04-26 — Side-by-side recording, 2× retina, video assets

Brings the recording pipeline to parity with `cycles-runaway-demo`'s
PRs #31–#34. The previous `demo.gif` recorded only `./demo.sh guarded`,
so first-time viewers saw a customer email getting blocked with no
visible "without Cycles" comparison to anchor the contrast against.
The new pipeline puts the unguarded send-email going out next to the
guarded send-email getting blocked, in ~30 seconds.

### What changed

- `demo.tape` — rewritten. Resolution bumped from 1000×600 / FontSize 14
  to 2000×1200 / FontSize 28 so the source matches a retina/HiDPI
  display 1:1; browsers downscale to crisp 1× or render natively at 2×.
  Character grid is unchanged (~71 cols × ~33 rows) so the existing
  rich panels render the same. `Set Framerate 12` added — at 2×
  resolution chromium can't sustain VHS's default ~50fps capture loop,
  so frames get dropped while output metadata still claims default fps,
  making playback ~2× too fast. 12fps gives chromium headroom and the
  rich panels render synchronously per step (no live refresh) so it's
  plenty smooth. The tape now invokes `python3 agent/record_orchestrator.py`
  rather than `./demo.sh guarded`; `record.sh` pre-warms the stack
  before launching `vhs` so the recording itself never sees docker
  output.

- `record.sh` — rewritten. Now pre-warms the Cycles stack
  (`docker compose down -v` → `up -d` → `wait_healthy` →
  `scripts/provision.sh`) and exports `CYCLES_BASE_URL`, `CYCLES_API_KEY`,
  `CYCLES_TENANT` before launching `vhs`. After the GIF is recorded,
  ffmpeg transcodes it to `demo.mp4` (H.264, CRF 22, faststart) and
  `demo.webm` (VP9, CRF 32), and extracts a last-frame poster image.
  ffmpeg is a soft dependency — if it's missing, record.sh prints a
  warning and continues without the video assets.

- `agent/record_orchestrator.py` — new. Drives end-to-end:
  1. MODE 1 banner (red), unguarded segment (4 actions execute,
     including the customer email), final UNGUARDED panel
  2. 1.5s "MODE 2: WITH CYCLES — same agent · same workflow"
     interstitial
  3. MODE 2 banner (green), guarded segment with `_setup()` + the
     `@cycles`-decorated wrappers from `guarded.py`. Catches
     `BudgetExceededError` on the `send_customer_email` step.
     Final GUARDED panel
  4. Green two-column summary card held for 5s

  Real code paths only — the unguarded segment calls the raw tools from
  `tools.py`; the guarded segment calls the same decorated wrappers
  `./demo.sh guarded` exercises live. No render-only stand-in.

- `agent/display.py` — gained two helpers:
  - `DemoDisplay.print_action_step(action)` — prints a single action
    inline (the step-by-step pattern previously inlined in
    `render_demo.py`). Used by the recording orchestrator so each ✓/✗
    lands visibly in the GIF rather than appearing all at once at the
    end via `print_action_log()`.
  - `DemoDisplay.build_summary_panel(unguarded, guarded)` — two-column
    green summary card structurally parallel to the runaway demo's
    summary card. Title: "Same agent. Same workflow. Two outcomes."
    Left column: 4/4 actions executed + per-toolset authority showing
    `send-email ▶ SENT`. Right column: 3/4 actions executed + per-
    toolset authority showing `send-email ✗ DENY`. Footer: "per-toolset
    budgets — set $0 to deny, $N to allow. No agent-code change needed."

- `AUDIT.md` — this file.

- `README.md` — added a `<video>` embed snippet (WebM-then-MP4 source
  order, GIF fallback, `poster="demo-action-authority-poster.png"`)
  and a one-line note that the GIF is recorded at 2× retina density.

### Out of scope (intentionally unchanged)

- `agent/unguarded.py`, `agent/guarded.py`, `agent/tools.py` — live
  agent code. The orchestrator imports from `guarded.py`; it does not
  modify it.
- `demo.sh`, `teardown.sh`, `docker-compose.yml`, `scripts/*.sh` — live
  demo orchestration.
- `render_demo.py` — kept as a docker-free render path. It now uses
  the shared `DemoDisplay.print_action_step()` helper but is otherwise
  unchanged.
- No ffmpeg speed manipulation. The orchestrator's natural pacing (~10s
  unguarded + 1.5s interstitial + ~10s guarded + 3.5s final hold + 5s
  summary ≈ 30s) fits the brief without `setpts` trickery. ffmpeg is
  used for transcode + poster extraction only.

### Recording-only timing constants

Defined at the top of `agent/record_orchestrator.py`:

| Constant | Value | Why |
|---|---|---|
| `STEP_DELAY_S` | 0.8 | Per-step pause so each ✓/✗ lands readably in the GIF. |
| `UNGUARDED_FINAL_HOLD_S` | 2.0 | Lets the UNGUARDED final panel register before the interstitial. |
| `INTERSTITIAL_HOLD_S` | 1.5 | "MODE 2: WITH CYCLES — same agent · same workflow" hold. |
| `BUDGET_EXCEEDED_HOLD_S` | 3.5 | Lets the GUARDED final panel ("Cycles blocked the customer email…") register before the summary. Mirrors runaway. |
| `SUMMARY_HOLD_S` | 5.0 | Final summary card hold. Mirrors runaway. |

### Asset sizes (target — matches runaway demo, regenerate to populate)

| Asset | Before | After (target) |
|---|---|---|
| `demo.gif` | 363K (1×, single-mode) | ~4M (2×, side-by-side) |
| `demo.mp4` | (n/a) | ~1M |
| `demo.webm` | (n/a) | ~1.5M |
| `demo-action-authority-poster.png` | (n/a) | ~300K |

### Verification performed in this change

- `python3 -m py_compile agent/record_orchestrator.py agent/display.py` —
  syntax checks pass.
- `bash -n record.sh` — no syntax errors.
- `python3 -c "from agent.display import DemoDisplay; …"` —
  `print_action_step` and `build_summary_panel` import cleanly.
- `python3 render_demo.py both` — the docker-free render path still
  works after the `print_action_step` move.
- Full end-to-end recording (`./record.sh` → docker + vhs + ffmpeg)
  is **deferred to a host with the toolchain**. The four binary
  artifacts (`demo.gif`, `demo.mp4`, `demo.webm`,
  `demo-action-authority-poster.png`) will land in a follow-up commit
  once they've been regenerated.
