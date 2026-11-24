#!/usr/bin/env python3
"""Home page finishing touches. Run after ios-adaptive.py. A skipped edit only prints a warning.

1. A tap on a touch screen makes WebKit fire a synthetic `mouseenter`, which started the hover
   preview and left the colour wash behind the card until the next tap elsewhere. Where there is
   no hovering pointer the video card now ignores it.
2. Off-screen feed cards are held at a placeholder height; the Android-style card is taller.
3. Beside a rail the top bar sits in the content column and the rail runs the full height of the
   window, as in Flow for Android.
4. Sync, Extensions and Support, which only the old sidebar reached, join the profile menu.
"""

BUTTON = (
    '                <button type="button" role="menuitem" onClick={{() => {{ close(); navigate("{to}"); }}}} className={{ROW}}>\n'
    '                  <{icon} className="h-5 w-5 text-chrome-neutral-400" />\n'
    '                  {{getString("{label}")}}\n'
    "                </button>\n"
)

GROUPS = [
    (
        "src/components/video/VideoCard.tsx",
        [
            (
                "import { useAdaptiveCard } from '../../lib/adaptive/useAdaptiveCard';\n",
                "import { useAdaptiveCard } from '../../lib/adaptive/useAdaptiveCard';\n"
                "import { IS_ADAPTIVE_LAYOUT } from '../../lib/adaptive/runtime';\n",
            ),
            (
                "  const handleMouseEnter = useCallback(() => {\n    setIsHovered(true);\n",
                "  const handleMouseEnter = useCallback(() => {\n"
                "    if (IS_ADAPTIVE_LAYOUT && !window.matchMedia('(hover: hover)').matches) return;\n"
                "    setIsHovered(true);\n",
            ),
        ],
        "touch hover",
    ),
    (
        "src/lib/useGridColumns.ts",
        [
            (
                "        '--flow-grid-gap': adaptive.gap,\n",
                "        '--flow-grid-gap': adaptive.gap,\n"
                "        // Android-style card: 12 + two title lines + 4 + two meta lines + 12 under the thumbnail.\n"
                "        '--flow-grid-meta': '6.5rem',\n",
            ),
        ],
        "placeholder card height",
    ),
    (
        "src/components/layout/PageWrapper.tsx",
        [
            (
                '    <div className="flex h-full flex-col bg-background text-chrome-zinc-100 overflow-hidden font-sans">\n'
                "      {IS_ADAPTIVE_LAYOUT ? <AdaptiveTopbar /> : <Topbar />}\n"
                '      <div className="flex flex-1 overflow-hidden">\n'
                "        {IS_ADAPTIVE_LAYOUT ? (\n"
                "          usesRail && <NavigationRail onOpenDrawer={() => setWatchSidebarOpen(true)} />\n"
                "        ) : (\n"
                "          <Sidebar />\n"
                "        )}\n",
                "    <div\n"
                "      className={`flex h-full bg-background text-chrome-zinc-100 overflow-hidden font-sans ${\n"
                '        IS_ADAPTIVE_LAYOUT && usesRail ? "flex-row" : "flex-col"\n'
                "      }`}\n"
                "    >\n"
                "      {IS_ADAPTIVE_LAYOUT && usesRail && <NavigationRail onOpenDrawer={() => setWatchSidebarOpen(true)} />}\n"
                '      <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">\n'
                "      {IS_ADAPTIVE_LAYOUT ? <AdaptiveTopbar /> : <Topbar />}\n"
                '      <div className="flex flex-1 overflow-hidden">\n'
                "        {!IS_ADAPTIVE_LAYOUT && <Sidebar />}\n",
            ),
            (
                "        </main>\n      </div>\n      {IS_ADAPTIVE_LAYOUT && !usesRail && <NavigationBar />}\n",
                "        </main>\n      </div>\n      </div>\n      {IS_ADAPTIVE_LAYOUT && !usesRail && <NavigationBar />}\n",
            ),
        ],
        "rail beside the top bar",
    ),
    (
        "src/components/profiles/ProfileMenuButton.tsx",
        [
            (
                'import { Check, Plus, UsersRound } from "lucide-react";\n',
                'import { Check, Heart, Plus, Puzzle, RefreshCw, UsersRound } from "lucide-react";\n'
                'import { IS_ADAPTIVE_LAYOUT } from "../../lib/adaptive/runtime";\n',
            ),
            (
                '            <p className="px-2.5 pb-1 pt-2 text-xs text-chrome-neutral-500">{getString("profiles_menu_footer")}</p>\n',
                "            {IS_ADAPTIVE_LAYOUT && (\n"
                "              <>\n"
                '                <div role="separator" className="mx-1.5 my-1.5 border-t border-chrome-neutral-800" />\n'
                + BUTTON.format(to="/sync", icon="RefreshCw", label="sidebar_sync")
                + BUTTON.format(to="/sponsorblock", icon="Puzzle", label="sidebar_extensions")
                + BUTTON.format(to="/support", icon="Heart", label="sidebar_support")
                + "              </>\n"
                "            )}\n"
                '            <p className="px-2.5 pb-1 pt-2 text-xs text-chrome-neutral-500">{getString("profiles_menu_footer")}</p>\n',
            ),
        ],
        "profile menu links",
    ),
]

for path, edits, what in GROUPS:
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        print(f"ios-home-cards: SKIPPED {what}: {path} not found")
        continue
    if any(text.count(old) != 1 for old, _ in edits):
        print(f"ios-home-cards: SKIPPED {what}: snippet not found once in {path}")
        continue
    for old, new in edits:
        text = text.replace(old, new)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"patched {path} ({what})")
