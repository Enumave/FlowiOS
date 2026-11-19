#!/usr/bin/env python3
"""Give Flow Desktop the phone and tablet layouts of Flow for Android.

Run from the repository root, after `ios-port.py` and `ios-ui.py` (it builds on the bottom bar,
rail rule and phone top bar that `ios-ui.py` already adds), before `pnpm build` /
`tauri ios build`. The layout rules themselves are ordinary source files in the repo
(`src/lib/adaptive/`, `AdaptiveNavigation.tsx`, `AdaptiveTopbar.tsx`); this script only wires them
into the pages that already exist. Every edit is an exact-text replacement and the script stops
with an error if a snippet is not found, so a changed upstream file shows up as a clear failure.
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


# 1. Page shell: the adaptive top bar, the rail or the bottom bar, and the width grids size from.
PW = "src/components/layout/PageWrapper.tsx"
replace(
    PW,
    "import { BottomNav } from './BottomNav';\n",
    "import { AdaptiveTopbar } from './AdaptiveTopbar';\n"
    "import { NavigationBar, NavigationRail } from './AdaptiveNavigation';\n"
    "import { IS_ADAPTIVE_LAYOUT } from '../../lib/adaptive/runtime';\n"
    "import { useReportContentWidth, useUsesNavigationRail } from '../../lib/adaptive/useWindowSizeClass';\n",
)
replace(
    PW,
    "  const usesDrawer = useSidebarDrawer();\n",
    "  const usesDrawer = useSidebarDrawer();\n  const usesRail = useUsesNavigationRail();\n",
)
replace(
    PW,
    "  const mainRef = useRef<HTMLElement>(null);\n",
    "  const mainRef = useRef<HTMLElement>(null);\n  useReportContentWidth(mainRef, IS_ADAPTIVE_LAYOUT);\n",
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
    "  const adaptive = useAdaptiveGridVars(columns, density, gapRem);\n",
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
    '            : cx(\n'
    '                IS_ADAPTIVE_LAYOUT ? "max-w-full px-0 pt-0" : "max-w-[1800px] px-4 pt-4 md:px-6 md:pt-6",\n'
    '                wide && "lg:grid-cols-[1fr_400px]",\n'
    '              ),\n',
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
    '            wide && (isTheaterMode ? "lg:col-start-2" : "lg:col-start-1"),\n'
    '            IS_ADAPTIVE_LAYOUT && "px-4",\n',
)
replace(
    WL,
    '            "relative z-[31] flex w-full min-h-0 flex-col gap-5 overscroll-contain lg:sticky lg:top-6 lg:max-h-[calc(100vh-6.5rem)] lg:self-start lg:overflow-y-auto lg:p-2",\n'
    '            isTheaterMode ? "lg:col-start-3 lg:row-start-2" : "lg:col-start-2 lg:row-span-2 lg:row-start-1",\n',
    '            "relative z-[31] flex w-full min-h-0 flex-col gap-5 overscroll-contain",\n'
    '            wide && "lg:sticky lg:top-6 lg:max-h-[calc(100vh-6.5rem)] lg:self-start lg:overflow-y-auto lg:p-2",\n'
    '            wide && (isTheaterMode ? "lg:col-start-3 lg:row-start-2" : "lg:col-start-2 lg:row-span-2 lg:row-start-1"),\n'
    '            IS_ADAPTIVE_LAYOUT && "px-4",\n',
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

print("ios-adaptive: done")
