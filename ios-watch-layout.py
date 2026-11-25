#!/usr/bin/env python3
"""Lay the Watch page out the way Flow for Android does, on iPhone and iPad.

Run from the repository root after the other layout scripts.

Android's player stays at the top of the window whatever is scrolled (its "scroll away" option is
off by default) and the page scrolls beneath it. The port let the video scroll up with the page,
so on an iPad it rode up under the top bar and showed through the status bar strip above it. This
pins the video, and tidies the spacing while it is there:

  * the video is flush to the left and top of its column, with no padding around it;
  * the information under it and the related list beside it carry a 12 px inset, as Android's
    do, so the video, the title and the first related card line up with each other;
  * the page's content sits beneath the video, not over it (z-29 under the player frame's z-30);
  * beside the video the related list scrolls by itself within the space under the top bar.

Only where the adaptive layouts run. If WatchLayout.tsx has changed so a line no longer matches,
the whole group is skipped with a warning and the build carries on.
"""

REL = "src/components/watch/WatchLayout.tsx"

EDITS = [
    (
        '          "mx-auto grid w-full grid-cols-1 items-start gap-x-6 gap-y-5",\n',
        "          IS_ADAPTIVE_LAYOUT\n"
        '            ? "mx-auto grid w-full grid-cols-1 items-start gap-x-0 gap-y-3"\n'
        '            : "mx-auto grid w-full grid-cols-1 items-start gap-x-6 gap-y-5",\n',
    ),
    (
        '            : cx("max-w-[1800px] px-4 pt-4 md:px-6 md:pt-6", wide && "lg:grid-cols-[1fr_400px]"),\n',
        "            : cx(\n"
        '                IS_ADAPTIVE_LAYOUT ? "max-w-full px-0 pt-0" : "max-w-[1800px] px-4 pt-4 md:px-6 md:pt-6",\n'
        '                wide && "lg:grid-cols-[1fr_400px]",\n'
        "              ),\n",
    ),
    (
        '            "w-full min-w-0",\n            wide && "lg:row-start-1",\n',
        '            "w-full min-w-0",\n'
        '            IS_ADAPTIVE_LAYOUT && !isTheaterMode && "sticky top-0 self-start",\n'
        '            wide && "lg:row-start-1",\n',
    ),
    (
        '            "relative z-[31] flex w-full min-w-0 flex-col gap-5",\n',
        "            IS_ADAPTIVE_LAYOUT\n"
        '              ? "relative z-[29] flex w-full min-w-0 flex-col gap-3 px-3"\n'
        '              : "relative z-[31] flex w-full min-w-0 flex-col gap-5",\n',
    ),
    (
        '            "relative z-[31] flex w-full min-h-0 flex-col gap-5 overscroll-contain",\n'
        '            wide && "lg:sticky lg:top-6 lg:max-h-[calc(100vh-6.5rem)] lg:self-start lg:overflow-y-auto lg:p-2",\n',
        "            IS_ADAPTIVE_LAYOUT\n"
        '              ? "relative z-[29] flex w-full min-h-0 flex-col gap-3 overscroll-contain px-3"\n'
        '              : "relative z-[31] flex w-full min-h-0 flex-col gap-5 overscroll-contain",\n'
        "            wide &&\n"
        "              (IS_ADAPTIVE_LAYOUT\n"
        '                ? "lg:sticky lg:top-0 lg:max-h-[calc(100vh-3.5rem-env(safe-area-inset-top,0px)-env(safe-area-inset-bottom,0px))] lg:self-start lg:overflow-y-auto lg:py-3"\n'
        '                : "lg:sticky lg:top-6 lg:max-h-[calc(100vh-6.5rem)] lg:self-start lg:overflow-y-auto lg:p-2"),\n',
    ),
]


def main():
    try:
        with open(REL, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        print(f"ios-watch-layout: SKIPPED: {REL} not found")
        return
    if "IS_ADAPTIVE_LAYOUT" not in text:
        print(f"ios-watch-layout: SKIPPED: {REL} does not use IS_ADAPTIVE_LAYOUT (ios-adaptive.py did not run?)")
        return
    for old, _ in EDITS:
        if text.count(old) != 1:
            print(f"ios-watch-layout: SKIPPED: snippet not found once in {REL}:\n{old[:140]}")
            return
    for old, new in EDITS:
        text = text.replace(old, new)
    with open(REL, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"patched {REL}")
    print("ios-watch-layout: done")


main()
