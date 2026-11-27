#!/usr/bin/env python3
"""Home page finishing touches. Run after ios-adaptive.py. A skipped edit only prints a warning.

1. A tap on a touch screen makes WebKit fire a synthetic `mouseenter`, which started the hover
   preview and left the colour wash behind the card until the next tap elsewhere. Where there is
   no hovering pointer the video card now ignores it.
2. Off-screen feed cards are held at a placeholder height; the Android-style card is taller.
3. Beside a rail the top bar sits in the content column and the rail runs the full height of the
   window, as in Flow for Android.
4. Sync, Extensions and Support, which only the old sidebar reached, join the profile menu.
5. The feed grid is automatic (three columns on a wide iPad) unless a count other than the desktop
   default was chosen; titles take two lines; Continue Watching is drawn as on Android; the Shorts
   shelf lines up with the other shelves.
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
    (
        "src/lib/useGridColumns.ts",
        [
            (
                "  const [columns] = useNumberPref(SETTINGS.GRID_COLUMNS, IS_ADAPTIVE_LAYOUT ? 0 : GRID_COLUMNS_DEFAULT);\n",
                "  const [storedColumns] = useNumberPref(SETTINGS.GRID_COLUMNS, IS_ADAPTIVE_LAYOUT ? 0 : GRID_COLUMNS_DEFAULT);\n"
                "  // Automatic on the adaptive layouts, as on Android. 4 is only what a pinch or the desktop default\n"
                "  // leaves behind, and pinning it would show four cramped columns on an iPad.\n"
                "  const columns = IS_ADAPTIVE_LAYOUT && storedColumns === GRID_COLUMNS_DEFAULT ? 0 : storedColumns;\n",
            ),
        ],
        "automatic column count",
    ),
    (
        "src/components/video/VideoCard.tsx",
        [
            (
                "Download, User, Share2 } from 'lucide-react';",
                "Download, User, Share2, X } from 'lucide-react';",
            ),
            # Two title lines whatever the desktop setting says, as Android's titleMedium.
            (
                "            style={titleClampStyle}\n"
                '            dir="auto"\n'
                "            className={`text-chrome-zinc-100 font-medium cursor-pointer hover:text-[var(--color-primary)] transition-colors ${adaptiveCard.active ? 'text-base leading-[22px]' : 'text-sm leading-snug'}`}\n",
                "            style={adaptiveCard.active ? undefined : titleClampStyle}\n"
                '            dir="auto"\n'
                "            className={`text-chrome-zinc-100 font-medium cursor-pointer hover:text-[var(--color-primary)] transition-colors ${adaptiveCard.active ? 'line-clamp-2 text-base leading-[22px]' : 'text-sm leading-snug'}`}\n",
            ),
            # Continue Watching thumbnails use the medium corner (12), not the large one.
            (
                "${adaptiveCard.active ? 'rounded-2xl' : 'rounded-xl'}",
                "${adaptiveCard.active && !isContinueCard ? 'rounded-2xl' : 'rounded-xl'}",
            ),
            # Android's Continue Watching card: no avatar, small bold title, channel, a close button.
            (
                '      <div className={adaptiveCard.active ? "flex gap-2 ps-2 pt-3 pb-3 relative z-10" : "flex gap-3 pe-1 relative z-10"}>\n',
                "      {adaptiveCard.active && isContinueCard ? (\n"
                '        <div className="relative z-10 flex items-start pt-1.5">\n'
                '          <div className="min-w-0 flex-1">\n'
                "            <h3\n"
                "              onClick={play}\n"
                "              {...tabClickProps}\n"
                '              dir="auto"\n'
                '              className="line-clamp-2 cursor-pointer text-xs font-semibold leading-[13.4px] text-chrome-neutral-100"\n'
                "            >\n"
                "              {displayTitle}\n"
                "            </h3>\n"
                '            <div className="mt-1 truncate text-[11px] leading-4 text-chrome-neutral-400">\n'
                "              <ChannelLabel name={byline} verified={video.isVerified} iconSize={11} />\n"
                "            </div>\n"
                "          </div>\n"
                "          <button\n"
                '            type="button"\n'
                "            title={getString('music_remove_from_history')}\n"
                "            aria-label={getString('music_remove_from_history')}\n"
                "            onClick={(e) => { e.stopPropagation(); onRemoveFromContinueWatching?.(video.id); }}\n"
                '            className="-me-1 -mt-1 shrink-0 rounded-full p-3.5 text-chrome-neutral-400 active:bg-chrome-neutral-800"\n'
                "          >\n"
                "            <X size={16} />\n"
                "          </button>\n"
                "        </div>\n"
                "      ) : (\n"
                '      <div className={adaptiveCard.active ? "flex gap-2 ps-2 pt-3 pb-3 relative z-10" : "flex gap-3 pe-1 relative z-10"}>\n',
            ),
            (
                "        </div>\n      </div>\n\n      {renderMenu()}\n",
                "        </div>\n      </div>\n      )}\n\n      {renderMenu()}\n",
            ),
        ],
        "continue watching card",
    ),
    (
        "src/components/shelf/VideoShelf.tsx",
        [
            (
                'import React, { useMemo } from "react";\n',
                'import React, { useMemo } from "react";\nimport { Link } from "react-router-dom";\n',
            ),
            (
                '          <h2 dir="auto" className={IS_ADAPTIVE_LAYOUT ? "flex items-center gap-2 text-base font-bold text-chrome-zinc-100" : "text-lg font-bold tracking-tight text-chrome-zinc-100"}>{title}</h2>\n',
                '          <h2 dir="auto" className={IS_ADAPTIVE_LAYOUT ? "flex items-center gap-2 text-base font-bold text-chrome-zinc-100" : "text-lg font-bold tracking-tight text-chrome-zinc-100"}>\n'
                "            {IS_ADAPTIVE_LAYOUT && variant === \"continue\" && (\n"
                '              <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6 shrink-0 fill-[var(--color-primary)]">\n'
                '                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z" />\n'
                "              </svg>\n"
                "            )}\n"
                "            <span>{title}</span>\n"
                "          </h2>\n",
            ),
            (
                "          {action}\n        </div>\n      ) : null}\n",
                "          {action}\n"
                "          {IS_ADAPTIVE_LAYOUT && variant === \"continue\" && !action && (\n"
                '            <Link to="/history" aria-label={title} className="-me-1 grid h-8 w-8 place-items-center text-chrome-neutral-400">\n'
                '              <svg viewBox="0 0 24 24" aria-hidden="true" className="h-6 w-6 fill-current rtl:-scale-x-100">\n'
                '                <path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z" />\n'
                "              </svg>\n"
                "            </Link>\n"
                "          )}\n"
                "        </div>\n      ) : null}\n",
            ),
        ],
        "continue watching header",
    ),
    (
        "src/components/shelf/ShortsShelf.tsx",
        [
            (
                'import { ShortCard } from "../shorts/ShortCard";\n',
                'import { ShortCard } from "../shorts/ShortCard";\nimport { IS_ADAPTIVE_LAYOUT } from "../../lib/adaptive/runtime";\n',
            ),
            (
                '      <div className="flex items-center justify-between">\n',
                '      <div className={IS_ADAPTIVE_LAYOUT ? "flex items-center justify-between px-3" : "flex items-center justify-between"}>\n',
            ),
            (
                '<ShelfScroller className="flex gap-4 px-3 -mx-3 pt-3 -mt-2 pb-3">',
                '<ShelfScroller className={IS_ADAPTIVE_LAYOUT ? "flex gap-[10px] px-3 pb-3" : "flex gap-4 px-3 -mx-3 pt-3 -mt-2 pb-3"}>',
            ),
        ],
        "shorts shelf",
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
