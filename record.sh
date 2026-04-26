#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Check prerequisites ──────────────────────────────────────────────────────

if ! command -v vhs &> /dev/null; then
    echo "ERROR: 'vhs' not found." >&2
    echo "  Install it: brew install vhs" >&2
    exit 1
fi

if [[ -z "${VIRTUAL_ENV:-}" && -f "$SCRIPT_DIR/.venv/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.venv/bin/activate"
fi

# ── Bring the Cycles stack to a clean, provisioned state ─────────────────────
#
# The recording assumes:
#   - the stack is healthy
#   - a fresh tenant + toolset-scoped budgets are provisioned
#     (internal-notes $1.00, crm-updates $1.00, send-email $0)
#   - CYCLES_BASE_URL / CYCLES_API_KEY / CYCLES_TENANT are exported
#
# Reset every time so the guarded run starts with a clean send-email
# zero-budget — otherwise a previous run's reservation history could
# affect the 409 timing.

echo "Resetting stack for a clean state..."
docker compose down -v 2>/dev/null || true

echo "Starting Cycles stack..."
docker compose up -d --pull=missing > /dev/null

echo "Waiting for services to be healthy..."
bash scripts/wait_healthy.sh 7878 "Cycles server"
bash scripts/wait_healthy.sh 7979 "Cycles admin"

echo "Provisioning tenant and toolset budgets..."
API_KEY=$(bash scripts/provision.sh)
export CYCLES_API_KEY="$API_KEY"
export CYCLES_BASE_URL="http://localhost:7878"
export CYCLES_TENANT="demo-tenant"

# ── Record the demo ──────────────────────────────────────────────────────────

echo ""
echo "Recording demo.tape → demo.gif ..."
vhs demo.tape
echo "Done — demo.gif created."

# ── Transcode for homepage embedding ─────────────────────────────────────────

if command -v ffmpeg &> /dev/null; then
    echo ""
    echo "Transcoding demo.gif → demo.mp4 (H.264) ..."
    ffmpeg -y -loglevel error \
        -i demo.gif \
        -movflags +faststart -pix_fmt yuv420p \
        -c:v libx264 -preset slow -crf 22 \
        -vf "scale=trunc(iw/2)*2:trunc(ih/2)*2" \
        demo.mp4
    echo "Transcoding demo.gif → demo.webm (VP9) ..."
    ffmpeg -y -loglevel error \
        -i demo.gif \
        -c:v libvpx-vp9 -b:v 0 -crf 32 -row-mt 1 -pix_fmt yuv420p -an \
        demo.webm
    echo "Extracting poster frame → demo-action-authority-poster.png ..."
    # Last-frame summary card, sampled deep into the SUMMARY_HOLD_S window
    # (5s hold near the end of a ~30s clip). The orchestrator clears the
    # screen before printing the summary, so any frame inside that hold
    # is the two-column "Same agent. Same workflow. Two outcomes." card.
    ffmpeg -y -loglevel error \
        -sseof -3 -i demo.mp4 \
        -vframes 1 \
        demo-action-authority-poster.png
    echo ""
    ls -lh demo.gif demo.mp4 demo.webm demo-action-authority-poster.png
else
    echo ""
    echo "WARNING: ffmpeg not found — skipping demo.mp4 / demo.webm / poster."
    echo "  Install ffmpeg to regenerate the homepage video assets:"
    echo "    macOS: brew install ffmpeg"
    echo "    Linux: sudo apt install ffmpeg"
fi
