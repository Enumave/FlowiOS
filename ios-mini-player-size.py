#!/usr/bin/env python3
"""Make the mini player land in its corner when it is minimized from the Watch page.

Run from the repository root after `ios-mini-player.py`.

Cause: `useMiniPlayerDrag` works out the mini player's resting place from the frame's size at that
moment. Minimizing from the Watch page the frame is still the size of the video (or part of the way
down to the mini size) when the place is worked out, so a bottom-right corner calculated for a
616 px wide frame leaves the 420 px mini player 196 px short of the right edge: it ends up
somewhere that is not a corner.

Fix: on the adaptive layouts the mini player's size is its own (the same width setting the sheet
animation aims for), never whatever size the frame happens to be at the time.

If useMiniPlayerDrag.ts has changed so the line no longer matches, this is skipped with a warning.
"""

REL = "src/lib/useMiniPlayerDrag.ts"
OLD = "  const getPlayerDimensions = () => {\n    const frame = frameRef.current;\n"
NEW = (
    "  const getPlayerDimensions = () => {\n"
    "    if (IS_ADAPTIVE_LAYOUT) {\n"
    "      // The mini player's own size, never the frame's size at the time: while the frame is still\n"
    "      // growing or shrinking into place a corner worked out from it is not the corner.\n"
    "      const width = Math.min(miniPlayerWidthPx(miniPlayerSize), window.innerWidth - 32);\n"
    "      return { width, height: (width * 9) / 16 };\n"
    "    }\n"
    "    const frame = frameRef.current;\n"
)

try:
    with open(REL, encoding="utf-8") as f:
        text = f.read()
except OSError:
    print(f"ios-mini-player-size: SKIPPED: {REL} not found")
else:
    if "IS_ADAPTIVE_LAYOUT" not in text:
        print(f"ios-mini-player-size: SKIPPED: {REL} does not use IS_ADAPTIVE_LAYOUT (ios-mini-player.py did not run?)")
    elif text.count(OLD) != 1:
        print(f"ios-mini-player-size: SKIPPED: snippet not found once in {REL}")
    else:
        with open(REL, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace(OLD, NEW))
        print(f"patched {REL}")
        print("ios-mini-player-size: done")
