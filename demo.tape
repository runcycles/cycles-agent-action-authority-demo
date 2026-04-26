# VHS tape for the Cycles action authority demo GIF — both modes side by side.
# https://github.com/charmbracelet/vhs
#
# record.sh pre-warms the stack and exports CYCLES_BASE_URL / CYCLES_API_KEY /
# CYCLES_TENANT before invoking vhs, so this tape skips docker entirely and
# starts at the MODE 1 banner.
#
# Resolution is rendered at 2x (2000x1200, FontSize 28) so the source matches
# a retina/HiDPI display 1:1 — browsers downscale to crisp 1x or render at
# native 2x. The character grid stays identical to a 1000x600 / FontSize 14
# layout (~71 cols × ~33 rows) so the existing rich panels render unchanged.

Output demo.gif

Set Width 2000
Set Height 1200
Set FontSize 28
Set Theme "Dracula"
Set PlaybackSpeed 1.0
# At 2x resolution chromium can't sustain VHS's default ~50fps capture loop,
# so frames get dropped while output metadata still claims default fps,
# making playback ~2x too fast. Setting Framerate explicitly to a rate
# chromium CAN sustain at this resolution keeps timing accurate. Rich panels
# render synchronously after each step (no live refresh), so 12fps is plenty.
Set Framerate 12

Hide
Type "clear"
Enter
Sleep 200ms
Show

Type "python3 agent/record_orchestrator.py"
Enter

# Total budget: ~6s unguarded (4 actions × 0.8s step delay + ~0.2s tool
# latency each + 2s final hold) + 1.5s interstitial + ~10s guarded
# (network round-trips to Cycles add ~0.4s/call) + 3.5s BUDGET_EXCEEDED
# hold + 5s summary + small startup + buffer ≈ 28s.
Sleep 28s
