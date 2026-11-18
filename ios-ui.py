#!/usr/bin/env python3
"""Make Flow Desktop's interface behave like an iPad app.

Run from the repository root, before `pnpm build` / `tauri ios build`. It hides the custom
desktop title bar (minimize / maximize / close), skips the desktop window-control calls, and
keeps the page clear of the iPad status bar and home indicator.
"""
import sys


def replace(rel, old, new):
    with open(rel, encoding="utf-8") as f:
        text = f.read()
    found = text.count(old)
    if found != 1:
        sys.exit(f"ios-ui: {rel}: expected 1 match, found {found} for:\n{old}")
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(old, new))
    print(f"patched {rel}")


# 1. One flag that says "this is a phone or tablet".
replace(
    "src/lib/platform.ts",
    "// Native macOS chrome sits outside the webview's content area.\n"
    "export const APP_TITLEBAR_HEIGHT = IS_MACOS_RUNTIME ? 0 : 32;",
    "export const IS_MOBILE_RUNTIME = (() => {\n"
    "  try {\n"
    "    const os = platform();\n"
    "    return os === \"ios\" || os === \"android\";\n"
    "  } catch {\n"
    "    return false;\n"
    "  }\n"
    "})();\n"
    "\n"
    "// Native macOS chrome sits outside the webview's content area, and phones have no title bar.\n"
    "export const APP_TITLEBAR_HEIGHT = IS_MACOS_RUNTIME || IS_MOBILE_RUNTIME ? 0 : 32;",
)

# 2. No custom title bar with window buttons.
replace(
    "src/components/layout/TitleBar.tsx",
    'import { IS_MACOS_RUNTIME } from "../../lib/platform";',
    'import { IS_MACOS_RUNTIME, IS_MOBILE_RUNTIME } from "../../lib/platform";',
)
replace(
    "src/components/layout/TitleBar.tsx",
    "  if (IS_MACOS_RUNTIME) return null;",
    "  if (IS_MACOS_RUNTIME || IS_MOBILE_RUNTIME) return null;",
)

# 3. Do not watch desktop window state (maximized / resized) on iOS.
replace(
    "src/lib/useWindowControls.ts",
    'import { IS_MACOS_RUNTIME } from "./platform";',
    'import { IS_MACOS_RUNTIME, IS_MOBILE_RUNTIME } from "./platform";',
)
replace(
    "src/lib/useWindowControls.ts",
    "    if (IS_MACOS_RUNTIME) return;",
    "    if (IS_MACOS_RUNTIME || IS_MOBILE_RUNTIME) return;",
)

# 4. Keep content out from under the status bar and home indicator.
replace(
    "src/App.tsx",
    'import { APP_TITLEBAR_HEIGHT } from "./lib/platform";',
    'import { APP_TITLEBAR_HEIGHT, IS_MOBILE_RUNTIME } from "./lib/platform";',
)
replace(
    "src/App.tsx",
    'const windowLayoutStyle = { "--app-titlebar-height": `${APP_TITLEBAR_HEIGHT}px` } as CSSProperties;',
    "const windowLayoutStyle = {\n"
    '  "--app-titlebar-height": `${APP_TITLEBAR_HEIGHT}px`,\n'
    "  ...(IS_MOBILE_RUNTIME\n"
    "    ? {\n"
    '        paddingTop: "env(safe-area-inset-top, 0px)",\n'
    '        paddingBottom: "env(safe-area-inset-bottom, 0px)",\n'
    "      }\n"
    "    : {}),\n"
    "} as CSSProperties;",
)
replace(
    "index.html",
    '<meta name="viewport" content="width=device-width, initial-scale=1.0" />',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />',
)

# 5. Player fullscreen: iPadOS has no window fullscreen to ask for, so just switch the layout.
replace(
    "src/components/player/Player.tsx",
    'import { IS_LINUX_RUNTIME } from "../../lib/platform";',
    'import { IS_LINUX_RUNTIME, IS_MOBILE_RUNTIME } from "../../lib/platform";',
)
replace(
    "src/components/player/Player.tsx",
    "    const active = !isFullscreen;\n"
    "    // The layout follows the native window rather than leading it: flipping the\n",
    "    const active = !isFullscreen;\n"
    "    if (IS_MOBILE_RUNTIME) {\n"
    "      setIsFullscreen(active);\n"
    "      return;\n"
    "    }\n"
    "    // The layout follows the native window rather than leading it: flipping the\n",
)
replace(
    "src/components/player/Player.tsx",
    "    const controller = windowFullscreenControllerRef.current;\n"
    "    if (!controller) return;\n"
    "\n"
    "    let disposed = false;\n"
    "    let unlisten: (() => void) | null = null;\n",
    "    const controller = windowFullscreenControllerRef.current;\n"
    "    if (!controller || IS_MOBILE_RUNTIME) return;\n"
    "\n"
    "    let disposed = false;\n"
    "    let unlisten: (() => void) | null = null;\n",
)

# 6. Touch gestures on the video, as on Android: sideways drag to scrub, vertical drag to enter
#    or leave fullscreen, pinch to zoom. The logic lives in touchGestures.ts.
OVERLAY = "src/components/player/gesture/overlay.tsx"
replace(
    OVERLAY,
    'import { LONG_PRESS_MS, shouldStartDrag } from "../../../lib/pointerGesture";\n',
    'import { LONG_PRESS_MS, shouldStartDrag } from "../../../lib/pointerGesture";\n'
    'import { IS_MOBILE_RUNTIME } from "../../../lib/platform";\n'
    'import { useTouchPlayerGestures, type ScrubPreview } from "./touchGestures";\n',
)
replace(
    OVERLAY,
    "  const [statsVisible, setStatsVisible] = useState(false);\n",
    "  const [statsVisible, setStatsVisible] = useState(false);\n"
    "  const [scrubPreview, setScrubPreview] = useState<ScrubPreview>(null);\n",
)
replace(
    OVERLAY,
    "  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {\n",
    "  useTouchPlayerGestures({\n"
    "    enabled: IS_MOBILE_RUNTIME && !lookAround && !canDragWindow && !canDragFrame,\n"
    "    layerRef,\n"
    "    videoRef,\n"
    "    seekBy,\n"
    "    toggleFullscreen,\n"
    "    onGestureStart: restorePlaybackRate,\n"
    "    onScrub: setScrubPreview,\n"
    "    resetKey: src,\n"
    "  });\n"
    "\n"
    "  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {\n",
)
replace(
    OVERLAY,
    "      {seekFeedback && <SeekFeedback feedback={seekFeedback} compact={isCompact} />}\n",
    "      {scrubPreview && (\n"
    '        <div className="pointer-events-none absolute left-1/2 top-8 z-30 -translate-x-1/2 rounded-full bg-chrome-black/70 px-5 py-2 text-sm font-bold text-chrome-white">\n'
    "          {formatTime(scrubPreview.target)} ({scrubPreview.delta >= 0 ? \"+\" : \"-\"}\n"
    "          {Math.abs(Math.round(scrubPreview.delta))}s)\n"
    "        </div>\n"
    "      )}\n"
    "\n"
    "      {seekFeedback && <SeekFeedback feedback={seekFeedback} compact={isCompact} />}\n",
)

# 7. App-wide touch behaviour, as on Android: hold for the menu a right click opens, swipe in from
#    the left edge to go back, pull a page down to refresh it (Home and Subscriptions), and keep
#    hover-only buttons visible. The logic lives in src/lib/touchNavigation.ts.
replace(
    "src/App.tsx",
    'import { useTabHistoryShortcuts } from "./lib/tabs/useTabHistoryShortcuts";\n',
    'import { useTabHistoryShortcuts } from "./lib/tabs/useTabHistoryShortcuts";\n'
    'import { useTouchNavigation } from "./lib/touchNavigation";\n',
)
replace(
    "src/App.tsx",
    "  useTabHistoryShortcuts();\n",
    "  useTabHistoryShortcuts();\n  useTouchNavigation();\n",
)
replace(
    "src/pages/Home.tsx",
    'import { RefreshCw } from "lucide-react";\n',
    'import { RefreshCw } from "lucide-react";\n'
    'import { registerPullRefresh } from "../lib/touchNavigation";\n',
)
replace(
    "src/pages/Home.tsx",
    "    return () => window.removeEventListener(HOME_RESELECTED_EVENT, handleReselected);\n"
    "  }, [scrollContainer, refreshOnReselect, chipFeed, reloadChip, handleRefresh]);\n",
    "    return () => window.removeEventListener(HOME_RESELECTED_EVENT, handleReselected);\n"
    "  }, [scrollContainer, refreshOnReselect, chipFeed, reloadChip, handleRefresh]);\n"
    "\n"
    "  useEffect(\n"
    "    () =>\n"
    "      registerPullRefresh(() => {\n"
    "        if (chipFeed) reloadChip();\n"
    "        else handleRefresh();\n"
    "      }),\n"
    "    [chipFeed, reloadChip, handleRefresh],\n"
    "  );\n",
)
replace(
    "src/pages/Subscriptions.tsx",
    'import { ChevronDown, ChevronUp, ListChecks, Loader2, Pencil, Plus, RefreshCw, Trash2, Upload, User } from "lucide-react";\n',
    'import { ChevronDown, ChevronUp, ListChecks, Loader2, Pencil, Plus, RefreshCw, Trash2, Upload, User } from "lucide-react";\n'
    'import { registerPullRefresh } from "../lib/touchNavigation";\n',
)
replace(
    "src/pages/Subscriptions.tsx",
    "  const channelDetails = useSubscriptionChannelDetails(subscriptions);\n",
    "  useEffect(() => registerPullRefresh(() => void refreshFeed()), [refreshFeed]);\n"
    "  const channelDetails = useSubscriptionChannelDetails(subscriptions);\n",
)
with open("src/App.css", "a", encoding="utf-8", newline="\n") as css:
    css.write(
        "\n/* Touch screens have no hover, so controls that only appear on hover stay visible. */\n"
        "@media (hover: none) {\n"
        '  [class*="group-hover:opacity-100"] {\n'
        "    opacity: 1 !important;\n"
        "  }\n"
        "  body {\n"
        "    -webkit-touch-callout: none;\n"
        "  }\n"
        "}\n"
    )
print("patched src/App.css")

# 8. The project's TypeScript is strict about list lookups (a touch or pointer may be missing),
#    so the two gesture files need explicit checks.
replace(
    "src/lib/touchNavigation.ts",
    "      const touch = event.touches[0];\n      const target = event.target instanceof Element ? event.target : null;\n",
    "      const touch = event.touches[0];\n      if (!touch) return;\n      const target = event.target instanceof Element ? event.target : null;\n",
)
replace(
    "src/lib/touchNavigation.ts",
    "      const touch = event.touches[0];\n\n      if (\n        pressTimer !== undefined &&",
    "      const touch = event.touches[0];\n      if (!touch) return;\n\n      if (\n        pressTimer !== undefined &&",
)
replace(
    "src/components/player/gesture/touchGestures.ts",
    "      const [a, b] = Array.from(pointers.values());\n      return Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));",
    "      const [a, b] = Array.from(pointers.values());\n      if (!a || !b) return 1;\n      return Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));",
)
replace(
    "src/components/player/gesture/touchGestures.ts",
    "      const [a, b] = Array.from(pointers.values());\n      return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };",
    "      const [a, b] = Array.from(pointers.values());\n      if (!a || !b) return start;\n      return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };",
)
# 9. A phone/tablet layout like Flow for Android: no side rail, a bottom bar for the main places,
#    the menu button opens the drawer, and the drawer clears the status bar. The status bar is
#    also hidden in the app's Info.plist (see note below).
def write_file(rel, text):
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"wrote {rel}")


write_file(
    "src/components/layout/BottomNav.tsx",
    r'''import type { ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { SidebarNavIcon, type SidebarNavIconName } from '../ui/SidebarNavIcon';
import { ShortsIcon, ShortsAIcon } from '../ui/ShortsIcon';
import { useAppSettingsStore } from '../../store/useAppSettingsStore';
import { getString } from '../../lib/i18n/index';
import { announceHomeReselected } from '../../lib/homeReselect';
import { useShortsEnabled } from '../../lib/useShortsContent';
import { useMusicEnabled } from '../../lib/useMusicContent';
import { SETTINGS } from '../../lib/settings/schema';
import { IS_MOBILE_RUNTIME } from '../../lib/platform';

type Destination = {
  to: string;
  label: string;
  icon: ReactNode;
  activeIcon: ReactNode;
  end?: boolean;
  onReselect?: () => void;
};

function navIcons(name: SidebarNavIconName) {
  return {
    icon: <SidebarNavIcon name={name} variant="outline" className="h-6 w-6 shrink-0" />,
    activeIcon: <SidebarNavIcon name={name} variant="filled" className="h-6 w-6 shrink-0" />,
  };
}

/** The main places to go on a phone or tablet, as the bottom bar of Flow for Android. */
export function BottomNav() {
  const location = useLocation();
  const shortsNavEnabled = useAppSettingsStore((state) => state.values[SETTINGS.SHORTS_NAVIGATION_ENABLED] !== 'false');
  const shortsEnabled = useShortsEnabled();
  const musicNavEnabled = useAppSettingsStore((state) => state.values[SETTINGS.MUSIC_NAVIGATION_ENABLED] !== 'false');
  const musicEnabled = useMusicEnabled();

  if (!IS_MOBILE_RUNTIME) return null;
  if (location.pathname.startsWith('/watch/') || location.pathname.startsWith('/settings')) return null;

  const destinations: Destination[] = [
    {
      to: '/',
      end: true,
      label: getString('home'),
      ...navIcons('home'),
      onReselect: () => {
        if (location.pathname === '/') announceHomeReselected();
      },
    },
  ];
  if (shortsEnabled && shortsNavEnabled) {
    destinations.push({
      to: '/shorts',
      label: getString('sidebar_shorts'),
      icon: <ShortsIcon className="h-6 w-6 shrink-0" />,
      activeIcon: <ShortsAIcon className="h-6 w-6 shrink-0" />,
    });
  }
  if (musicEnabled && musicNavEnabled) {
    destinations.push({ to: '/music', label: getString('sidebar_music'), ...navIcons('music') });
  }
  destinations.push(
    { to: '/subscriptions', label: getString('sidebar_subscriptions'), ...navIcons('subscriptions') },
    { to: '/library', label: getString('sidebar_you'), ...navIcons('you') },
  );

  return (
    <nav className="flex h-14 shrink-0 items-stretch border-t border-chrome-neutral-800/50 bg-background">
      {destinations.map((destination) => (
        <NavLink
          key={destination.to}
          to={destination.to}
          end={destination.end}
          onClick={destination.onReselect}
          className="flex min-w-0 flex-1 flex-col items-center justify-center gap-0.5 px-1 text-[11px]"
        >
          {({ isActive }) => (
            <>
              <span className={isActive ? 'text-[var(--color-primary)]' : 'text-chrome-neutral-300'}>
                {isActive ? destination.activeIcon : destination.icon}
              </span>
              <span
                className={`max-w-full truncate ${
                  isActive ? 'font-medium text-chrome-neutral-100' : 'text-chrome-neutral-300'
                }`}
              >
                {destination.label}
              </span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
''',
)
replace(
    "src/components/layout/Sidebar.tsx",
    "import { useNotesEnabled } from '../../lib/useNotes';\n",
    "import { useNotesEnabled } from '../../lib/useNotes';\n"
    "import { IS_MOBILE_RUNTIME } from '../../lib/platform';\n",
)
replace(
    "src/components/layout/Sidebar.tsx",
    "    !isOverlay &&\n    (location.pathname.startsWith('/watch/') ||\n",
    "    !isOverlay &&\n    (IS_MOBILE_RUNTIME ||\n      location.pathname.startsWith('/watch/') ||\n",
)
replace(
    "src/lib/useSidebarDrawer.ts",
    'import { useMediaQuery } from "./useMediaQuery";\n',
    'import { useMediaQuery } from "./useMediaQuery";\nimport { IS_MOBILE_RUNTIME } from "./platform";\n',
)
replace(
    "src/lib/useSidebarDrawer.ts",
    '  return narrow || pathname.startsWith("/watch/") || pathname.startsWith("/settings");',
    '  return IS_MOBILE_RUNTIME || narrow || pathname.startsWith("/watch/") || pathname.startsWith("/settings");',
)
replace(
    "src/components/layout/PageWrapper.tsx",
    "import { useSidebarDrawer } from '../../lib/useSidebarDrawer';\n",
    "import { useSidebarDrawer } from '../../lib/useSidebarDrawer';\nimport { BottomNav } from './BottomNav';\n",
)
replace(
    "src/components/layout/PageWrapper.tsx",
    "      </div>\n      {usesDrawer && (\n",
    "      </div>\n      <BottomNav />\n      {usesDrawer && (\n",
)
replace(
    "src/components/layout/PageWrapper.tsx",
    "top-[calc(var(--app-titlebar-height)+3.5rem)]",
    "top-[calc(var(--app-titlebar-height)+3.5rem+env(safe-area-inset-top,0px))]",
)
# Hide the iPad status bar and keep the app full screen (applies when installed on its own).
replace(
    "src-tauri/Info.ios.plist",
    "</dict>\n</plist>",
    "  <key>UIStatusBarHidden</key>\n  <true/>\n"
    "  <key>UIViewControllerBasedStatusBarAppearance</key>\n  <false/>\n"
    "  <key>UIRequiresFullScreen</key>\n  <true/>\n"
    "</dict>\n</plist>",
)
print("ios-ui: done")
