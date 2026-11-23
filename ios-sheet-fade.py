#!/usr/bin/env python3
"""Fade the Watch page while the player is dragged down into the mini player, as on Android.

Run from the repository root after `ios-adaptive.py`. If `playerSheet.ts` or the Watch page has
changed so that an edit no longer matches, that group is skipped with a warning and the build
carries on.
"""


def replace_group(rel, edits, what):
    try:
        with open(rel, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        print(f"ios-sheet-fade: SKIPPED {what}: {rel} not found")
        return
    for old, _ in edits:
        if text.count(old) != 1:
            print(f"ios-sheet-fade: SKIPPED {what}: snippet not found once in {rel}:\n{old[:120]}")
            return
    for old, new in edits:
        text = text.replace(old, new)
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"patched {rel} ({what})")


replace_group(
    "src/components/watch/WatchLayout.tsx",
    [
        (
            '    <div className="min-h-screen bg-background pb-32 text-chrome-neutral-100">\n',
            '    <div data-flow-watch-body className="min-h-screen bg-background pb-32 text-chrome-neutral-100">\n',
        ),
    ],
    "watch page fade target",
)
replace_group(
    "src/lib/playerSheet.ts",
    [
        (
            'import type { FrameBox } from "./theaterGlide";\n',
            'import type { FrameBox } from "./theaterGlide";\n'
            'import { animateSheetBodyFade, applySheetBodyFade, clearSheetBodyFade } from "./adaptive/sheetBodyFade";\n',
        ),
        (
            '    frame.removeAttribute(SHEET_ATTR);\n    document.body.removeAttribute(SHEET_SETTLING_ATTR);\n',
            '    frame.removeAttribute(SHEET_ATTR);\n    document.body.removeAttribute(SHEET_SETTLING_ATTR);\n    clearSheetBodyFade();\n',
        ),
        (
            '    const animation = frame.animate(keyframes, { duration: durationMs, easing: "linear" });\n',
            '    const animation = frame.animate(keyframes, { duration: durationMs, easing: "linear" });\n'
            '    if (to.action === "minimize") animateSheetBodyFade(values, durationMs);\n',
        ),
        (
            "        progress = 0;\n        box = origin;\n        radius = originRadius;\n      }\n      write();\n",
            "        progress = 0;\n        box = origin;\n        radius = originRadius;\n      }\n      write();\n"
            '      applySheetBodyFade(target && target === down && target.action === "minimize" ? progress : 0);\n',
        ),
    ],
    "player sheet page fade",
)

print("ios-sheet-fade: done")
