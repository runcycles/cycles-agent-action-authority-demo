# VHS tape file for recording the Cycles action authority demo
# https://github.com/charmbracelet/vhs

Output demo.gif

Set Width 1000
Set Height 600
Set FontSize 14
Set Theme "Dracula"
Set PlaybackSpeed 2.0

Type "./demo.sh guarded"
Enter

# Docker startup (~20s) + guarded run (~5s) + buffer (10s)
Sleep 40s
