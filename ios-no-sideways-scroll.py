#!/usr/bin/env python3
"""Stop the app's pages from panning sideways on iPhone and iPad.

Run from the repository root after the other layout scripts.

Cause: the routed pages scroll inside <main class="overflow-y-auto">. CSS turns a scroll container's
other axis from `visible` into `auto` as soon as one axis scrolls, so anything that pokes a few
pixels past the edge makes the whole page pan sideways as well as up and down. On Home it was the
"next" arrow on the Continue Watching and Shorts shelves, which hangs 16 px past the right edge.

Fix, in two parts, both only where the adaptive layouts run:
  1. the page scroller never scrolls sideways (the shelves still scroll inside themselves);
  2. the shelves' mouse arrows are hidden on touch screens, where you swipe instead, as on Android.

If PageWrapper.tsx has changed so the line no longer matches, that part is skipped with a warning.
"""

PAGE = "src/components/layout/PageWrapper.tsx"
OLD = '              : "flex-1 overflow-y-auto"\n'
NEW = (
    "              : IS_ADAPTIVE_LAYOUT\n"
    '                ? "flex-1 overflow-y-auto overflow-x-hidden"\n'
    '                : "flex-1 overflow-y-auto"\n'
)

try:
    with open(PAGE, encoding="utf-8") as f:
        text = f.read()
    if text.count(OLD) != 1 or "IS_ADAPTIVE_LAYOUT" not in text:
        print(f"ios-no-sideways-scroll: SKIPPED page scroller: snippet not found once in {PAGE}")
    else:
        with open(PAGE, "w", encoding="utf-8", newline="\n") as f:
            f.write(text.replace(OLD, NEW))
        print(f"patched {PAGE}")
except OSError:
    print(f"ios-no-sideways-scroll: SKIPPED page scroller: {PAGE} not found")

with open("src/App.css", "a", encoding="utf-8", newline="\n") as css:
    css.write(
        "\n/* Touch screens swipe their shelves; the mouse arrows hang past the page's edge. */\n"
        "@media (hover: none) {\n"
        '  [class~="group/shelfnav"] > button {\n'
        "    display: none !important;\n"
        "  }\n"
        "}\n"
    )
print("patched src/App.css")
print("ios-no-sideways-scroll: done")
