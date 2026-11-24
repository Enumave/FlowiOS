#!/usr/bin/env python3
"""Give Flow Desktop the phone and tablet layouts of Flow for Android.

Run from the repository root, after `ios-port.py` and `ios-ui.py` (it builds on the bottom bar,
rail rule and phone top bar that `ios-ui.py` already adds), before `pnpm build` /
`tauri ios build`. The layout rules themselves are ordinary source files in the repo
(`src/lib/adaptive/`, `AdaptiveNavigation.tsx`, `AdaptiveTopbar.tsx`); this script only wires them
into the pages that already exist. Every edit is an exact-text replacement and the script stops
with an error if a snippet is not found, so a changed upstream file shows up as a clear failure.

What it wires up, by window size (the window, not the display, so Split View and Stage Manager
windows lay out like the narrow device they behave as):

  compact  (< 600)           bottom bar, phone top bar, one column of cards, Settings as list -> page
  medium   (600-839)         bottom bar, two-column feed, single-column Watch with room for a grid
  expanded (>= 840)          start-edge rail, inline search, up to three columns, Settings list + page,
                             Watch split in two when the window is wider than tall
  large    (>= 1200)         the rail may open to show labels beside its icons
  phone on its side          rail too: a bottom bar would take a sixth of the height
"""
import sys


def replace(rel, old, new, count=1):
    with open(rel, encoding="utf-8") as f:
        text = f.read()
    found = text.count(old)
    if found != count:
        sys.exit(f"ios-adaptive: {rel}: expected {count} match(es), found {found} for:\n{old}")
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(old, new))
    print(f"patched {rel}")


def replace_group(rel, edits, what):
    """Cosmetic edits that must land together or not at all. If upstream moved a snippet the whole
    group is skipped with a warning instead of failing the build: the app still works, just unstyled.
    An edit's `old` may be a tuple of alternative spellings, and `new` a function of the one found."""
    try:
        with open(rel, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        print(f"ios-adaptive: SKIPPED {what}: {rel} not found")
        return
    plan = []
    for old, new in edits:
        candidates = old if isinstance(old, tuple) else (old,)
        hits = [c for c in candidates if text.count(c) == 1]
        if not hits:
            print(f"ios-adaptive: SKIPPED {what}: snippet not found once in {rel}:\n{candidates[0][:120]}")
            return
        plan.append((hits[0], new(hits[0]) if callable(new) else new))
    for old, new in plan:
        text = text.replace(old, new)
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"patched {rel} ({what})")


# 1. Page shell: the adaptive top bar, the rail or the bottom bar, and the width grids size from.
PW = "src/components/layout/PageWrapper.tsx"
replace(
    PW,
    "import { BottomNav } from './BottomNav';\n",
    "import { AdaptiveTopbar } from './AdaptiveTopbar';\n"
    "import { NavigationBar, NavigationRail } from './AdaptiveNavigation';\n"
    "import { IS_ADAPTIVE_LAYOUT } from '../../lib/adaptive/runtime';\n"
    "import { useReportContentWidth, useUsesNavigationRail } from '../../lib/adaptive/useWindowSizeClass';\n"
    "import { useReportBarVisibility } from '../../lib/adaptive/barVisibility';\n",
)
replace(
    PW,
    "  const usesDrawer = useSidebarDrawer();\n",
    "  const usesDrawer = useSidebarDrawer();\n  const usesRail = useUsesNavigationRail();\n",
)
replace(
    PW,
    "  const mainRef = useRef<HTMLElement>(null);\n",
    "  const mainRef = useRef<HTMLElement>(null);\n"
    "  useReportContentWidth(mainRef, IS_ADAPTIVE_LAYOUT);\n"
    "  useReportBarVisibility(mainRef, IS_ADAPTIVE_LAYOUT && !usesRail);\n",
)
replace(
    PW,
    "      <Topbar />\n      <div className=\"flex flex-1 overflow-hidden\">\n        <Sidebar />\n",
    "      {IS_ADAPTIVE_LAYOUT ? <AdaptiveTopbar /> : <Topbar />}\n"
    "      <div className=\"flex flex-1 overflow-hidden\">\n"
    "        {IS_ADAPTIVE_LAYOUT ? (\n"
    "          usesRail && <NavigationRail onOpenDrawer={() => setWatchSidebarOpen(true)} />\n"
    "        ) : (\n"
    "          <Sidebar />\n"
    "        )}\n",
)
replace(PW, "      <BottomNav />\n", "      {IS_ADAPTIVE_LAYOUT && !usesRail && <NavigationBar />}\n")

# 2. The side menu is always a drawer where the adaptive layouts run (it holds Sync, Extensions...).
DRAWER = "src/lib/useSidebarDrawer.ts"
replace(
    DRAWER,
    'import { IS_MOBILE_RUNTIME } from "./platform";\n',
    'import { IS_MOBILE_RUNTIME } from "./platform";\nimport { IS_ADAPTIVE_LAYOUT } from "./adaptive/runtime";\n',
)
# ios-ui.py's own rule keeps the drawer for phones only; the rail's menu button needs it too.
replace(
    DRAWER,
    "  return (IS_MOBILE_RUNTIME && !usesRail) || narrow",
    "  return IS_ADAPTIVE_LAYOUT || (IS_MOBILE_RUNTIME && !usesRail) || narrow",
)

# ios-ui.py's rail rule only counts heights of 480-899, so an iPad Pro held upright (1366 tall)
# would get the bottom bar. Android counts every height from 480 up; hand everything that asks
# "rail or bar?" the same answer the new navigation uses.
with open("src/lib/windowSizeClass.ts", "w", encoding="utf-8", newline="\n") as shim:
    shim.write(
        '// Rail-or-bar rule shared with Flow for Android; see src/lib/adaptive.\n'
        'export { useUsesNavigationRail } from "./adaptive/useWindowSizeClass";\n'
    )
print("wrote src/lib/windowSizeClass.ts")

# 3. Feed grids: one column on a phone, two on a medium window, up to three on a tablet.
GRID = "src/lib/useGridColumns.ts"
replace(
    GRID,
    "import { useNumberPref } from './usePreference';\n",
    "import { useNumberPref } from './usePreference';\nimport { useAdaptiveGridVars } from './adaptive/useAdaptiveGrid';\nimport { IS_ADAPTIVE_LAYOUT } from './adaptive/runtime';\n",
)
replace(
    GRID,
    "  const [columns] = useNumberPref(SETTINGS.GRID_COLUMNS, GRID_COLUMNS_DEFAULT);\n",
    "  // Where the adaptive layouts run, no saved count means automatic (0), as on Android.\n"
    "  const [columns] = useNumberPref(SETTINGS.GRID_COLUMNS, IS_ADAPTIVE_LAYOUT ? 0 : GRID_COLUMNS_DEFAULT);\n"
    "  const adaptive = useAdaptiveGridVars(columns, density);\n",
)
replace(
    GRID,
    "  return useMemo(() => {\n    const target = density === 'dense' ? columns + DENSE_COLUMN_OFFSET : columns;\n",
    "  return useMemo(() => {\n"
    "    if (adaptive) {\n"
    "      return {\n"
    "        '--flow-grid-columns': String(adaptive.columns),\n"
    "        '--flow-grid-card-min': adaptive.cardMin,\n"
    "        '--flow-grid-gap': adaptive.gap,\n"
    "        paddingInline: adaptive.padding,\n"
    "      } as CSSProperties;\n"
    "    }\n"
    "    const target = density === 'dense' ? columns + DENSE_COLUMN_OFFSET : columns;\n",
)
replace(GRID, "  }, [columns, density, gapRem]);\n", "  }, [adaptive, columns, density, gapRem]);\n")

# 4. Watch: split in two only when the window is wider than tall (an upright tablet keeps one column).
WL = "src/components/watch/WatchLayout.tsx"
replace(
    WL,
    'import type { WatchLayoutProps } from "./types";\n',
    'import type { WatchLayoutProps } from "./types";\n'
    'import { IS_ADAPTIVE_LAYOUT } from "../../lib/adaptive/runtime";\n'
    'import { usePlayerLayoutMode } from "../../lib/adaptive/useWindowSizeClass";\n',
)
replace(
    WL,
    "  const isTheaterMode = usePlayerStore((s) => s.isTheaterMode);\n",
    "  const isTheaterMode = usePlayerStore((s) => s.isTheaterMode);\n"
    "  // Desktop always splits from `lg`; the adaptive layouts split only a landscape expanded window.\n"
    '  const wide = !IS_ADAPTIVE_LAYOUT || usePlayerLayoutMode() === "wide";\n',
)
replace(
    WL,
    '          "mx-auto grid w-full grid-cols-1 items-start gap-x-6 gap-y-5 lg:grid-rows-[auto_1fr]",\n'
    "          isTheaterMode\n"
    '            ? "max-w-full px-0 pt-0 lg:grid-cols-[minmax(0,1fr)_minmax(0,1100px)_400px_minmax(0,1fr)]"\n'
    '            : "max-w-[1800px] px-4 pt-4 md:px-6 md:pt-6 lg:grid-cols-[1fr_400px]",\n',
    '          "mx-auto grid w-full grid-cols-1 items-start gap-x-6 gap-y-5",\n'
    '          wide && "lg:grid-rows-[auto_1fr]",\n'
    "          isTheaterMode\n"
    '            ? cx("max-w-full px-0 pt-0", wide && "lg:grid-cols-[minmax(0,1fr)_minmax(0,1100px)_400px_minmax(0,1fr)]")\n'
    '            : cx("max-w-[1800px] px-4 pt-4 md:px-6 md:pt-6", wide && "lg:grid-cols-[1fr_400px]"),\n',
)
replace(
    WL,
    '            "w-full min-w-0 lg:row-start-1",\n'
    '            isTheaterMode ? "z-10 bg-chrome-black lg:col-span-full" : "lg:col-start-1",\n',
    '            "w-full min-w-0",\n'
    '            wide && "lg:row-start-1",\n'
    '            isTheaterMode ? cx("z-10 bg-chrome-black", wide && "lg:col-span-full") : wide && "lg:col-start-1",\n',
)
replace(
    WL,
    '            "relative z-[31] flex w-full min-w-0 flex-col gap-5 lg:row-start-2",\n'
    '            isTheaterMode ? "lg:col-start-2" : "lg:col-start-1",\n',
    '            "relative z-[31] flex w-full min-w-0 flex-col gap-5",\n'
    '            wide && "lg:row-start-2",\n'
    '            wide && (isTheaterMode ? "lg:col-start-2" : "lg:col-start-1"),\n',
)
replace(
    WL,
    '            "relative z-[31] flex w-full min-h-0 flex-col gap-5 overscroll-contain lg:sticky lg:top-6 lg:max-h-[calc(100vh-6.5rem)] lg:self-start lg:overflow-y-auto lg:p-2",\n'
    '            isTheaterMode ? "lg:col-start-3 lg:row-start-2" : "lg:col-start-2 lg:row-span-2 lg:row-start-1",\n',
    '            "relative z-[31] flex w-full min-h-0 flex-col gap-5 overscroll-contain",\n'
    '            wide && "lg:sticky lg:top-6 lg:max-h-[calc(100vh-6.5rem)] lg:self-start lg:overflow-y-auto lg:p-2",\n'
    '            wide && (isTheaterMode ? "lg:col-start-3 lg:row-start-2" : "lg:col-start-2 lg:row-span-2 lg:row-start-1"),\n',
)

# 5. Settings: a list beside the page on expanded windows, a list and then a page otherwise.
SL = "src/components/settings/SettingsLayout.tsx"
replace(
    SL,
    "import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';\n",
    "import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';\n"
    "import { ChevronLeft } from 'lucide-react';\n"
    "import { IS_ADAPTIVE_LAYOUT } from '../../lib/adaptive/runtime';\n"
    "import { useWindowSizeClass } from '../../lib/adaptive/useWindowSizeClass';\n"
    "import { isExpandedWidth } from '../../lib/adaptive/windowSizeClass';\n",
)
replace(
    SL,
    "  const [highlight, setHighlight] = useState<string | null>(null);\n",
    "  const [highlight, setHighlight] = useState<string | null>(null);\n"
    "  const sizeClass = useWindowSizeClass();\n"
    "  const stacked = IS_ADAPTIVE_LAYOUT && !isExpandedWidth(sizeClass);\n"
    "  const [showDetail, setShowDetail] = useState(Boolean(requested));\n",
)
replace(
    SL,
    "  const searching = debouncedQuery.trim().length > 0;\n",
    "  const searching = debouncedQuery.trim().length > 0;\n  const detailShown = !stacked || showDetail || searching;\n",
)
replace(
    SL,
    '    <div className="mx-auto w-full h-[calc(100vh-64px)] flex">\n'
    '      <nav className="w-56 shrink-0 border-e border-chrome-neutral-800 overflow-y-auto py-6 px-3 flex flex-col gap-1">\n',
    "    <div className={`mx-auto w-full flex ${IS_ADAPTIVE_LAYOUT ? 'h-full' : 'h-[calc(100vh-64px)]'}`}>\n"
    "      <nav\n"
    "        className={\n"
    "          stacked && detailShown\n"
    "            ? 'hidden'\n"
    "            : `${stacked ? 'w-full' : 'w-56 shrink-0 border-e border-chrome-neutral-800'} overflow-y-auto py-6 px-3 flex flex-col gap-1`\n"
    "        }\n"
    "      >\n",
)
replace(
    SL,
    "              setActiveTab(cat.id);\n              clearQuery();\n",
    "              setActiveTab(cat.id);\n              setShowDetail(true);\n              clearQuery();\n",
)
replace(
    SL,
    '      <div ref={paneRef} className="flex-1 overflow-y-auto py-6 ps-10 pe-4">\n'
    "        {searching ? <SettingsSearchResults results={results} onOpen={openResult} /> : children(activeTab)}\n",
    "      <div\n"
    "        ref={paneRef}\n"
    "        className={`${stacked && !detailShown ? 'hidden' : 'flex-1'} overflow-y-auto py-6 ${stacked ? 'px-4' : 'ps-10 pe-4'}`}\n"
    "      >\n"
    "        {stacked && !searching && (\n"
    "          <button\n"
    "            type=\"button\"\n"
    "            aria-label={getString('topbar_back')}\n"
    "            onClick={() => setShowDetail(false)}\n"
    "            className=\"-ms-2 mb-4 flex items-center gap-1 rounded-full px-2 py-1.5 text-sm font-medium text-chrome-neutral-300\"\n"
    "          >\n"
    "            <ChevronLeft size={20} className=\"rtl:-scale-x-100\" />\n"
    "            {getString(SETTINGS_CATEGORY_LABELS[activeTab])}\n"
    "          </button>\n"
    "        )}\n"
    "        {searching ? <SettingsSearchResults results={results} onOpen={openResult} /> : children(activeTab)}\n",
)

# 7. Home and the shared video card, as Flow for Android draws them. These are cosmetic: if upstream
#    has moved a snippet the whole group is skipped with a warning and the build carries on.
replace_group(
    "src/pages/Home.tsx",
    [
        (
            'import { HomeChipRow } from "../components/home/HomeChipRow";\n',
            'import { HomeChipRow } from "../components/home/HomeChipRow";\n'
            'import { AdaptiveChipRow } from "../components/home/AdaptiveChipRow";\n'
            'import { IS_ADAPTIVE_LAYOUT } from "../lib/adaptive/runtime";\n',
        ),
        (
            '<div className="flex-1 space-y-6 px-8 py-6">',
            '<div className={IS_ADAPTIVE_LAYOUT ? "flex-1 pb-4" : "flex-1 space-y-6 px-8 py-6"}>',
        ),
        (
            "<HomeChipRow chips={chipOptions} selected={chips.selected} onSelect={chips.select} />",
            "IS_ADAPTIVE_LAYOUT ? (\n"
            "          <AdaptiveChipRow chips={chipOptions} selected={chips.selected} onSelect={chips.select} />\n"
            "        ) : (\n"
            "          <HomeChipRow chips={chipOptions} selected={chips.selected} onSelect={chips.select} />\n"
            "        )",
        ),
    ],
    "Home page",
)
replace_group(
    "src/components/video/VideoGrid.tsx",
    [
        (
            "import { useGridStyle, useResolvedGridColumns } from '../../lib/useGridColumns';\n",
            "import { useGridStyle, useResolvedGridColumns } from '../../lib/useGridColumns';\n"
            "import { IS_ADAPTIVE_LAYOUT } from '../../lib/adaptive/runtime';\n",
        ),
        (
            'const gridClass = "flow-grid gap-y-8 pb-8";',
            'const gridClass = IS_ADAPTIVE_LAYOUT ? "flow-grid gap-y-3 pb-4" : "flow-grid gap-y-8 pb-8";',
        ),
        (
            'className="flow-grid-card p-2 -m-2"',
            'className={IS_ADAPTIVE_LAYOUT ? "flow-grid-card" : "flow-grid-card p-2 -m-2"}',
        ),
    ],
    "video grid",
)
_CHANNEL_LINE = (
    "          <div\n"
    "            onClick={(e) => { void handleChannelNavigate(e); }}\n"
    "            className={`text-chrome-zinc-400 text-[13px] mt-0.5 truncate transition-colors ${isLocalFile ? \"\" : \"cursor-pointer hover:text-chrome-zinc-300\"}`}\n"
    "          >\n"
    "            <ChannelLabel name={byline} verified={video.isVerified} />\n"
    "          </div>\n"
)
replace_group(
    "src/components/video/VideoCard.tsx",
    [
        (
            "import { highlightTerms } from '../../lib/highlightTerms';\n",
            "import { highlightTerms } from '../../lib/highlightTerms';\n"
            "import { useAdaptiveCard } from '../../lib/adaptive/useAdaptiveCard';\n",
        ),
        (
            "  const showsProgressBar = isHistoryCard || isContinueCard || progressPercent > 0;\n",
            "  const showsProgressBar = isHistoryCard || isContinueCard || progressPercent > 0;\n"
            "  const adaptiveCard = useAdaptiveCard();\n",
        ),
        (
            "      className={`video-card flex flex-col gap-3 group ${COLOR_WASH_HOST} rounded-xl p-1.5 -m-1.5`}\n",
            "      className={\n"
            "        adaptiveCard.active\n"
            "          ? `video-card flex flex-col group ${COLOR_WASH_HOST} ${adaptiveCard.bleed ? '' : 'px-3'}`\n"
            "          : `video-card flex flex-col gap-3 group ${COLOR_WASH_HOST} rounded-xl p-1.5 -m-1.5`\n"
            "      }\n",
        ),
        (
            (
                '        className="relative w-full aspect-video rounded-xl overflow-hidden bg-chrome-zinc-900 cursor-pointer"\n',
                '        className="relative w-full aspect-video rounded-xl overflow-hidden bg-chrome-zinc-900 cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"\n',
            ),
            lambda matched: (
                "        className={`"
                + matched.split('className="')[1].split('"')[0].replace("rounded-xl", "${adaptiveCard.active ? 'rounded-2xl' : 'rounded-xl'}")
                + "`}\n"
            ),
        ),
        (
            '      <div className="flex gap-3 pe-1 relative z-10">\n',
            '      <div className={adaptiveCard.active ? "flex gap-2 ps-2 pt-3 pb-3 relative z-10" : "flex gap-3 pe-1 relative z-10"}>\n',
        ),
        (
            "            className={`w-9 h-9 shrink-0 flex items-center justify-center cursor-pointer mt-0.5 hover:opacity-80 transition-opacity ${\n",
            "            className={`${adaptiveCard.active ? 'w-10 h-10' : 'w-9 h-9 mt-0.5'} shrink-0 flex items-center justify-center cursor-pointer hover:opacity-80 transition-opacity ${\n",
        ),
        (
            '            className="text-chrome-zinc-100 text-sm font-medium leading-snug cursor-pointer hover:text-[var(--color-primary)] transition-colors"\n',
            "            className={`text-chrome-zinc-100 font-medium cursor-pointer hover:text-[var(--color-primary)] transition-colors ${adaptiveCard.active ? 'text-base leading-[22px]' : 'text-sm leading-snug'}`}\n",
        ),
        (
            # The byline: upstream now draws views and date with CardByline, older code inline.
            (
                _CHANNEL_LINE + "\n" + '          {/* View Count + Published */}\n'
                '          <CardByline views={video.viewCountText} published={publishedText} className="text-chrome-zinc-500 text-[13px]" />\n',
                _CHANNEL_LINE + "\n" + '          {/* View Count + Published */}\n'
                '          <div className="text-chrome-zinc-500 text-[13px]">\n'
                "            {video.viewCountText && <bdi>{video.viewCountText}</bdi>}\n"
                '            {video.viewCountText && publishedText && <span className="mx-1">•</span>}\n'
                "            {publishedText && <bdi>{publishedText}</bdi>}\n"
                "          </div>\n",
            ),
            lambda matched: (
                "          {adaptiveCard.active ? (\n"
                '            <div className="mt-1 line-clamp-2 text-xs leading-4 text-chrome-neutral-400">\n'
                '              <span onClick={(e) => { void handleChannelNavigate(e); }} className="inline-flex align-bottom">\n'
                "                <ChannelLabel name={byline} verified={video.isVerified} />\n"
                "              </span>\n"
                '              {video.viewCountText && <><span className="mx-1">•</span><bdi>{video.viewCountText}</bdi></>}\n'
                '              {publishedText && <><span className="mx-1">•</span><bdi>{publishedText}</bdi></>}\n'
                "            </div>\n"
                "          ) : (\n"
                "            <>\n" + matched + "            </>\n"
                "          )}\n"
            ),
        ),
        (
            '            className="p-1 rounded-full text-chrome-zinc-500 hover:text-chrome-zinc-200 hover:bg-chrome-zinc-800 opacity-0 group-hover:opacity-100 transition duration-150 ease-out mt-0.5"\n',
            '            className={adaptiveCard.active ? "-mt-1 -me-1 rounded-full p-3 text-chrome-neutral-300 active:bg-chrome-neutral-800" : "p-1 rounded-full text-chrome-zinc-500 hover:text-chrome-zinc-200 hover:bg-chrome-zinc-800 opacity-0 group-hover:opacity-100 transition duration-150 ease-out mt-0.5"}\n',
        ),
    ],
    "video card",
)
replace_group(
    "src/components/shelf/VideoShelf.tsx",
    [
        (
            'import type { VideoSummary } from "../../types/video";\n',
            'import type { VideoSummary } from "../../types/video";\n'
            'import { IS_ADAPTIVE_LAYOUT } from "../../lib/adaptive/runtime";\n'
            'import { useAdaptiveLaneStyle } from "../../lib/adaptive/useAdaptiveCard";\n',
        ),
        (
            "  if (!videos || videos.length === 0) return null;\n",
            "  const laneStyle = useAdaptiveLaneStyle();\n  if (!videos || videos.length === 0) return null;\n",
        ),
        (
            '    <div className="relative flex flex-col gap-4">\n',
            '    <div className={IS_ADAPTIVE_LAYOUT ? "relative flex flex-col gap-1" : "relative flex flex-col gap-4"}>\n',
        ),
        (
            '        <div className="flex items-center justify-between">\n',
            '        <div className={IS_ADAPTIVE_LAYOUT ? "flex items-center justify-between px-3 pt-2" : "flex items-center justify-between"}>\n',
        ),
        (
            '          <h2 className="text-lg font-bold text-chrome-zinc-100 tracking-tight flex items-center gap-2">\n',
            '          <h2 className={IS_ADAPTIVE_LAYOUT ? "text-base font-bold text-chrome-zinc-100 flex items-center gap-2" : "text-lg font-bold text-chrome-zinc-100 tracking-tight flex items-center gap-2"}>\n',
        ),
        (
            '            <span className="text-xs text-chrome-zinc-500 font-semibold bg-surface-container-low border border-chrome-neutral-800 px-2 py-0.5 rounded-full">\n',
            '            <span className={IS_ADAPTIVE_LAYOUT ? "hidden" : "text-xs text-chrome-zinc-500 font-semibold bg-surface-container-low border border-chrome-neutral-800 px-2 py-0.5 rounded-full"}>\n',
        ),
        (
            '<ShelfScroller className="flex gap-4 px-3 scroll-px-3 -mx-3 pt-3 -mt-2 pb-3 snap-x">',
            '<ShelfScroller className={IS_ADAPTIVE_LAYOUT ? "flex gap-[10px] px-3 scroll-px-3 pb-3 snap-x" : "flex gap-4 px-3 scroll-px-3 -mx-3 pt-3 -mt-2 pb-3 snap-x"}>',
        ),
        (
            (
                '            className="w-[280px] sm:w-[320px] shrink-0 transform transition-transform duration-300 hover:translate-y-[-2px]"\n',
                '            className={`w-[280px] sm:w-[320px] shrink-0 ${hoverMotion("transform transition-transform duration-300 hover:translate-y-[-2px]")}`}\n',
            ),
            lambda matched: matched + "            style={laneStyle}\n",
        ),
    ],
    "video shelf",
)

# 8. The thin progress strip the player keeps while its controls are hidden is for the windowed
#    player only on Android (PlayerControlsOverlay: `!isFullscreen`). In fullscreen, hiding the
#    controls hides everything, so nothing is left on screen without a touch.
replace_group(
    "src/components/player/FlowPlayerControls.tsx",
    [
        (
            "{idleStripEnabled && !isLive && !shouldShowControls && (",
            "{idleStripEnabled && !isLive && !shouldShowControls && !(IS_MOBILE_RUNTIME && isFullscreen) && (",
        ),
    ],
    "idle progress strip",
)

# 6. iOS draws the status bar (and the multitasking button in it) over the top of the app. Hiding
#    the bar left that button floating over the top bar; showing it makes the page start below it.
PLIST = "src-tauri/Info.ios.plist"
replace(PLIST, "  <key>UIStatusBarHidden</key>\n  <true/>\n", "  <key>UIStatusBarHidden</key>\n  <false/>\n"
        "  <key>UIStatusBarStyle</key>\n  <string>UIStatusBarStyleLightContent</string>\n")

print("ios-adaptive: done")
