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
    'import { APP_TITLEBAR_HEIGHT, IS_LINUX_RUNTIME } from "./lib/platform";',
    'import { APP_TITLEBAR_HEIGHT, IS_LINUX_RUNTIME, IS_MOBILE_RUNTIME } from "./lib/platform";',
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
    "  const [isBoosting, setIsBoosting] = useState(false);\n",
    "  const [isBoosting, setIsBoosting] = useState(false);\n"
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

# 6b. A finger touching down must not reveal the controls: a drag (scrub, swipe, pinch) starts with a
#     touch-down, so revealing there flashes the controls over every gesture. A tap still toggles
#     them, from the click (onTapToggleControls); a mouse or trackpad on iPad keeps the desktop behaviour.
replace(
    OVERLAY,
    "    clearClickTimer();\n"
    "    onRevealControls();\n"
    "    menuClosingPressRef.current = Boolean(contextMenu) || settingsOpen;\n",
    "    clearClickTimer();\n"
    "    if (!IS_MOBILE_RUNTIME || event.pointerType !== \"touch\") onRevealControls();\n"
    "    menuClosingPressRef.current = Boolean(contextMenu) || settingsOpen;\n",
)

# 7. App-wide touch behaviour, as on Android: hold for the menu a right click opens, swipe in from
#    the left edge to go back, pull a page down to refresh it (Home and Subscriptions), and keep
#    hover-only buttons visible. The logic lives in src/lib/touchNavigation.ts.
replace(
    "src/App.tsx",
    'import { useTabHistoryMouseButtons } from "./lib/tabs/useTabHistoryMouseButtons";\n',
    'import { useTabHistoryMouseButtons } from "./lib/tabs/useTabHistoryMouseButtons";\n'
    'import { useTouchNavigation } from "./lib/touchNavigation";\n',
)
replace(
    "src/App.tsx",
    "  useTabHistoryMouseButtons();\n",
    "  useTabHistoryMouseButtons();\n  useTouchNavigation();\n",
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
# 10. Touch-first player and Android's rail-or-bar rule for the main navigation.
write_file(
    "src/lib/windowSizeClass.ts",
    r'''import { useMediaQuery } from "./useMediaQuery";
import { IS_MOBILE_RUNTIME } from "./platform";

/**
 * Flow for Android shows a side rail on a wide window of medium height (a tablet on its side) and a
 * bottom bar everywhere else. Sizes are Android's window size classes in CSS pixels.
 */
export function useUsesNavigationRail(): boolean {
  const expandedWidth = useMediaQuery("(min-width: 840px)");
  const mediumHeight = useMediaQuery("(min-height: 480px) and (max-height: 899px)");
  const landscape = useMediaQuery("(orientation: landscape)");
  return IS_MOBILE_RUNTIME && ((expandedWidth && mediumHeight) || (landscape && !mediumHeight));
}
''',
)
replace(
    "src/components/layout/BottomNav.tsx",
    "import { IS_MOBILE_RUNTIME } from '../../lib/platform';\n",
    "import { IS_MOBILE_RUNTIME } from '../../lib/platform';\n"
    "import { useUsesNavigationRail } from '../../lib/windowSizeClass';\n",
)
replace(
    "src/components/layout/BottomNav.tsx",
    "  const musicEnabled = useMusicEnabled();\n\n  if (!IS_MOBILE_RUNTIME) return null;\n",
    "  const musicEnabled = useMusicEnabled();\n  const usesRail = useUsesNavigationRail();\n\n  if (!IS_MOBILE_RUNTIME || usesRail) return null;\n",
)
replace(
    "src/components/layout/Sidebar.tsx",
    "import { IS_MOBILE_RUNTIME } from '../../lib/platform';\n",
    "import { IS_MOBILE_RUNTIME } from '../../lib/platform';\n"
    "import { useUsesNavigationRail } from '../../lib/windowSizeClass';\n",
)
replace(
    "src/components/layout/Sidebar.tsx",
    "  if (\n    !isOverlay &&\n    (IS_MOBILE_RUNTIME ||\n",
    "  const usesMobileRail = useUsesNavigationRail();\n"
    "  if (\n    !isOverlay &&\n    ((IS_MOBILE_RUNTIME && !usesMobileRail) ||\n",
)
replace(
    "src/lib/useSidebarDrawer.ts",
    'import { IS_MOBILE_RUNTIME } from "./platform";\n',
    'import { IS_MOBILE_RUNTIME } from "./platform";\nimport { useUsesNavigationRail } from "./windowSizeClass";\n',
)
replace(
    "src/lib/useSidebarDrawer.ts",
    "  return IS_MOBILE_RUNTIME || narrow || ",
    "  const usesRail = useUsesNavigationRail();\n  return (IS_MOBILE_RUNTIME && !usesRail) || narrow || ",
)

# Player: a tap on the video shows or hides the controls, and a finger touching down or lifting
# must not do that by itself.
replace(
    "src/components/player/Player.tsx",
    "  const handlePointerEnter = useCallback(() => {\n    pointerInsideRef.current = true;\n    revealControls();\n  }, [revealControls]);\n",
    "  // On a touchscreen a tap on the video shows or hides the controls; a finger touching down or\n"
    "  // lifting must not do that on its own.\n"
    "  const toggleControlsOnTap = () => {\n"
    "    if (shouldShowControls) {\n"
    "      clearHideTimer();\n"
    "      setControlsVisible(false);\n"
    "    } else {\n"
    "      revealControls();\n"
    "    }\n"
    "  };\n"
    "\n"
    "  const handlePointerEnter = useCallback((event: React.PointerEvent) => {\n"
    "    if (event.pointerType === \"touch\") return;\n"
    "    pointerInsideRef.current = true;\n"
    "    revealControls();\n"
    "  }, [revealControls]);\n",
)
replace(
    "src/components/player/Player.tsx",
    "  const handlePointerLeave = useCallback(() => {\n    pointerInsideRef.current = false;\n",
    "  const handlePointerLeave = useCallback((event: React.PointerEvent) => {\n"
    "    if (event.pointerType === \"touch\") return;\n"
    "    pointerInsideRef.current = false;\n",
)
replace(
    "src/components/player/Player.tsx",
    "      onPointerEnter={handlePointerEnter}\n      onPointerMove={revealControls}\n      onPointerDown={revealControls}\n",
    "      onPointerEnter={handlePointerEnter}\n"
    "      onPointerMove={(event) => {\n"
    "        if (event.pointerType !== \"touch\") revealControls();\n"
    "      }}\n"
    "      onPointerDown={(event) => {\n"
    "        if (event.pointerType !== \"touch\") revealControls();\n"
    "      }}\n",
)
replace(
    "src/components/player/Player.tsx",
    "      <PlayerGestureOverlay\n",
    "      <PlayerGestureOverlay\n        onTapToggleControls={toggleControlsOnTap}\n",
)
replace(
    "src/components/player/gesture/overlay.tsx",
    "  togglePlay: () => void;\n",
    "  togglePlay: () => void;\n  /** On a touchscreen a single tap shows or hides the controls instead of pausing. */\n  onTapToggleControls?: () => void;\n",
)
replace(
    "src/components/player/gesture/overlay.tsx",
    "  togglePlay,\n",
    "  togglePlay,\n  onTapToggleControls,\n",
)
replace(
    "src/components/player/gesture/overlay.tsx",
    "      clickTimerRef.current = null;\n      toggledByFirstClickRef.current = true;\n      togglePlay();\n",
    "      clickTimerRef.current = null;\n"
    "      if (IS_MOBILE_RUNTIME && onTapToggleControls) {\n"
    "        onTapToggleControls();\n"
    "        return;\n"
    "      }\n"
    "      toggledByFirstClickRef.current = true;\n"
    "      togglePlay();\n",
)

# Player controls: large previous / play / next in the middle of the video, like Android.
replace(
    "src/components/player/FlowPlayerControls.tsx",
    '} from "../../lib/playerProgress";\n',
    '} from "../../lib/playerProgress";\nimport { IS_MOBILE_RUNTIME } from "../../lib/platform";\n',
)
replace(
    "src/components/player/FlowPlayerControls.tsx",
    '      <div\n        className={cx(\n          "pointer-events-none absolute inset-0 z-20 flex h-full w-full flex-col justify-end',
    """      {IS_MOBILE_RUNTIME && (
        <div
          className={cx(
            "pointer-events-none absolute inset-0 z-20 flex items-center justify-center gap-10 transition-opacity duration-200",
            shouldShowControls ? "opacity-100" : "opacity-0",
          )}
        >
          {showNextPrevious && (
            <button
              type="button"
              title={getString('previous')}
              onClick={playPrevious}
              className={cx(
                "grid h-14 w-14 place-items-center rounded-full bg-chrome-black/45 text-chrome-white transition-transform active:scale-90",
                shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
              )}
            >
              <SkipBack size={28} fill="currentColor" />
            </button>
          )}
          <button
            type="button"
            title={isPlaying ? "Pause" : "Play"}
            onClick={togglePlay}
            className={cx(
              "grid h-[72px] w-[72px] place-items-center rounded-full bg-chrome-black/45 text-chrome-white transition-transform active:scale-90",
              shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
            )}
          >
            {isPlaying ? (
              <Pause size={38} fill="currentColor" />
            ) : (
              <Play size={38} fill="currentColor" className="ml-1" />
            )}
          </button>
          {showNextPrevious && (
            <button
              type="button"
              onClick={() => playNext()}
              className={cx(
                "grid h-14 w-14 place-items-center rounded-full bg-chrome-black/45 text-chrome-white transition-transform active:scale-90",
                shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
              )}
            >
              <SkipForward size={28} fill="currentColor" />
            </button>
          )}
        </div>
      )}
      <div
        className={cx(
          "pointer-events-none absolute inset-0 z-20 flex h-full w-full flex-col justify-end""",
)
replace(
    "src/components/player/FlowPlayerControls.tsx",
    '<div className="flex items-center justify-between gap-3">',
    '<div data-touch-bar className="flex items-center justify-between gap-3">',
)
with open("src/App.css", "a", encoding="utf-8", newline="\n") as css:
    css.write(
        "\n/* Player controls on a touchscreen: bigger targets, a visible seek knob, no volume slider. */\n"
        "@media (hover: none) {\n"
        "  [data-progress-track] {\n"
        "    height: 2.75rem !important;\n"
        "  }\n"
        '  [data-progress-track] [class*="group-hover/seekbar:scale-100"] {\n'
        "    scale: 1 !important;\n"
        "    transform: scale(1) !important;\n"
        "  }\n"
        "  [data-touch-bar] .h-7.w-7 {\n"
        "    width: 2.5rem;\n"
        "    height: 2.5rem;\n"
        "  }\n"
        "  [data-touch-bar] .group\\/volume {\n"
        "    display: none !important;\n"
        "  }\n"
        "}\n"
    )
print("patched src/App.css (player controls)")
# 12. Phone-width top bar, as on Android's compact layout: a logo without its name, no settings
#     button (it is in the menu drawer), and no keyboard-shortcut hint in the search box.
replace(
    "src/components/layout/Topbar.tsx",
    "import { useSidebarDrawer } from '../../lib/useSidebarDrawer';\n",
    "import { useSidebarDrawer } from '../../lib/useSidebarDrawer';\n"
    "import { useMediaQuery } from '../../lib/useMediaQuery';\n"
    "import { IS_MOBILE_RUNTIME } from '../../lib/platform';\n",
)
replace(
    "src/components/layout/Topbar.tsx",
    "  const usesDrawer = useSidebarDrawer();\n",
    "  const usesDrawer = useSidebarDrawer();\n"
    "  const narrowWindow = useMediaQuery('(max-width: 639px)');\n"
    "  const isPhone = IS_MOBILE_RUNTIME && narrowWindow;\n",
)
replace(
    "src/components/layout/Topbar.tsx",
    "<Logo size={36} showText={true} />",
    "<Logo size={36} showText={!isPhone} />",
)
replace(
    "src/components/layout/Topbar.tsx",
    "        <IconButton onClick={() => navigate('/settings')} title={getString('settings_title')} aria-label={getString('settings_title')}>\n"
    "          <Settings />\n"
    "        </IconButton>\n",
    "        {!isPhone && (\n"
    "          <IconButton onClick={() => navigate('/settings')} title={getString('settings_title')} aria-label={getString('settings_title')}>\n"
    "            <Settings />\n"
    "          </IconButton>\n"
    "        )}\n",
)
replace(
    "src/components/layout/TopbarSearch.tsx",
    "import { useRunSearch } from '../../lib/useRunSearch';\n",
    "import { useRunSearch } from '../../lib/useRunSearch';\n"
    "import { IS_MOBILE_RUNTIME } from '../../lib/platform';\n",
)
replace(
    "src/components/layout/TopbarSearch.tsx",
    '        ) : searchKey ? (\n          <kbd dir="ltr"',
    '        ) : searchKey && !IS_MOBILE_RUNTIME ? (\n          <kbd dir="ltr"',
)
# 13. Android's tablet watch page (the page layout itself is in ios-adaptive.py): the video runs edge
#     to edge, the channel row puts Subscribe at the far end, the action buttons scroll in one row, the related videos are large cards, and the
#     video has an overlay top row (collapse, settings). The page also clears iPadOS's multitasking
#     button at the top centre.
replace(
    "src/App.tsx",
    '        paddingTop: "env(safe-area-inset-top, 0px)",\n',
    '        paddingTop: "max(env(safe-area-inset-top, 0px), 22px)",\n',
)
replace(
    "src/components/watch/WatchPlayerSlot.tsx",
    'import { useAppSettingsStore } from "../../store/useAppSettingsStore";\n',
    'import { useAppSettingsStore } from "../../store/useAppSettingsStore";\nimport { IS_MOBILE_RUNTIME } from "../../lib/platform";\n',
)
replace(
    "src/components/watch/WatchPlayerSlot.tsx",
    '          : "relative w-full aspect-video overflow-hidden rounded-xl bg-chrome-black"\n',
    '          : IS_MOBILE_RUNTIME\n'
    '          ? "relative w-full aspect-video overflow-hidden bg-chrome-black"\n'
    '          : "relative w-full aspect-video overflow-hidden rounded-xl bg-chrome-black"\n',
)
replace(
    "src/components/watch/GlobalVideoPlayer.tsx",
    'import { FullscreenPanelHost } from "./FullscreenPanelHost";\n',
    'import { FullscreenPanelHost } from "./FullscreenPanelHost";\nimport { IS_MOBILE_RUNTIME } from "../../lib/platform";\n',
)
replace(
    "src/components/watch/GlobalVideoPlayer.tsx",
    '            : "fixed z-30 rounded-xl bg-chrome-black"\n',
    '            : IS_MOBILE_RUNTIME\n'
    '            ? "fixed z-30 bg-chrome-black"\n'
    '            : "fixed z-30 rounded-xl bg-chrome-black"\n',
)
replace(
    "src/components/watch/WatchMetadata.tsx",
    'import { youtubeWatchUrl } from "../../lib/youtubeUrl";\n',
    'import { youtubeWatchUrl } from "../../lib/youtubeUrl";\nimport { IS_MOBILE_RUNTIME } from "../../lib/platform";\n',
)
replace(
    "src/components/watch/WatchMetadata.tsx",
    '      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">\n',
    '      <div\n'
    '        className={\n'
    '          IS_MOBILE_RUNTIME ? "flex flex-col gap-3" : "flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between"\n'
    '        }\n'
    '      >\n',
)
replace(
    "src/components/watch/WatchMetadata.tsx",
    '        <div className="flex flex-wrap items-center gap-2">\n',
    '        <div\n'
    '          className={\n'
    '            IS_MOBILE_RUNTIME\n'
    '              ? "flex flex-nowrap items-center gap-2 overflow-x-auto pb-1 [scrollbar-width:none] [&>*]:shrink-0"\n'
    '              : "flex flex-wrap items-center gap-2"\n'
    '          }\n'
    '        >\n',
)
replace(
    "src/components/watch/WatchOwner.tsx",
    'import { joinIsolated } from "../../lib/direction";\n',
    'import { joinIsolated } from "../../lib/direction";\nimport { IS_MOBILE_RUNTIME } from "../../lib/platform";\n',
)
replace(
    "src/components/watch/WatchOwner.tsx",
    '      <div className="flex shrink-0 items-center gap-3">\n        <button onClick={() => goToChannel(channelId)} className="transition-opacity hover:opacity-80">\n',
    '      <div className={IS_MOBILE_RUNTIME ? "flex w-full items-center gap-3" : "flex shrink-0 items-center gap-3"}>\n'
    '        <button onClick={() => goToChannel(channelId)} className="transition-opacity hover:opacity-80">\n',
)
replace(
    "src/components/watch/WatchOwner.tsx",
    '<button onClick={() => goToChannel(channelId)} className="min-w-0 pe-2 text-start">',
    '<button\n'
    '          onClick={() => goToChannel(channelId)}\n'
    '          className={IS_MOBILE_RUNTIME ? "min-w-0 flex-1 pe-2 text-start" : "min-w-0 pe-2 text-start"}\n'
    '        >',
)
replace(
    "src/components/watch/RelatedVideos.tsx",
    'import type { RelatedVideosProps } from "./types";\n',
    'import type { RelatedVideosProps } from "./types";\nimport { IS_MOBILE_RUNTIME } from "../../lib/platform";\n',
)
replace(
    "src/components/watch/RelatedVideos.tsx",
    '            variant="compact"\n',
    '            variant={IS_MOBILE_RUNTIME ? "default" : "compact"}\n',
)
replace(
    "src/components/player/FlowPlayerControls.tsx",
    "  Pause,\n  PictureInPicture2,\n",
    "  ChevronDown,\n  Pause,\n  PictureInPicture2,\n",
)
replace(
    "src/components/player/FlowPlayerControls.tsx",
    'import { IS_MOBILE_RUNTIME } from "../../lib/platform";\n',
    'import { IS_MOBILE_RUNTIME } from "../../lib/platform";\nimport { useTabsStore } from "../../store/useTabsStore";\n',
)
replace(
    "src/components/player/FlowPlayerControls.tsx",
    '      {IS_MOBILE_RUNTIME && (\n        <div\n          className={cx(\n            "pointer-events-none absolute inset-0 z-20 flex items-center justify-center gap-10',
    """      {IS_MOBILE_RUNTIME && (
        <div
          className={cx(
            "pointer-events-none absolute inset-x-0 top-0 z-20 flex items-center justify-between px-3 pt-3 transition-opacity duration-200",
            shouldShowControls ? "opacity-100" : "opacity-0",
          )}
        >
          <button
            type="button"
            title={getString('topbar_back')}
            aria-label={getString('topbar_back')}
            onClick={() => {
              if (isFullscreen) toggleFullscreen();
              else useTabsStore.getState().go(-1);
            }}
            className={cx(
              "grid h-10 w-10 place-items-center rounded-full bg-chrome-black/45 text-chrome-white transition-transform active:scale-90",
              shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
            )}
          >
            <ChevronDown size={26} />
          </button>
          <button
            type="button"
            {...{ [PLAYER_MENU_OWNER_ATTR]: "" }}
            title={getString("player_menu_settings")}
            aria-label={getString("player_menu_settings")}
            onClick={() => {
              setSettingsOpen((value) => !value);
              setSettingsPane("root");
            }}
            className={cx(
              "grid h-10 w-10 place-items-center rounded-full bg-chrome-black/45 text-chrome-white transition-transform active:scale-90",
              shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
            )}
          >
            <SettingsIcon size={22} />
          </button>
        </div>
      )}
      {IS_MOBILE_RUNTIME && (
        <div
          className={cx(
            "pointer-events-none absolute inset-0 z-20 flex items-center justify-center gap-10""",
)
# 14. The player's controls the way Flow for Android draws them (see its PlayerBottomBar): bare icons
#     on a soft top scrim with collapse on the left and AirPlay and settings on the right, a quiet
#     previous / play / next in the middle, and along the bottom a row of pills (time, chapter,
#     quality, fullscreen) sitting on a seek bar that runs edge to edge. The desktop button row
#     is not drawn on touch devices.
PLAYER_FILE = "src/components/player/FlowPlayerControls.tsx"


def replace_between(rel, start, end, new):
    with open(rel, encoding="utf-8") as f:
        text = f.read()
    if text.count(start) != 1 or text.count(end) != 1:
        sys.exit(f"ios-ui: {rel}: markers found {text.count(start)} / {text.count(end)} for:\n{start}\n...\n{end}")
    a = text.index(start)
    b = text.index(end)
    if b < a:
        sys.exit(f"ios-ui: {rel}: end marker comes before start marker")
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text[:a] + new + text[b:])
    print(f"patched {rel} (block)")


replace(PLAYER_FILE, "  ChevronDown,\n  Pause,\n", "  Airplay,\n  ChevronDown,\n  Pause,\n")
replace_between(
    PLAYER_FILE,
    '      {IS_MOBILE_RUNTIME && (\n        <div\n          className={cx(\n            "pointer-events-none absolute inset-x-0 top-0 z-20',
    '      <div\n        className={cx(\n          "pointer-events-none absolute inset-0 z-20 flex h-full w-full flex-col justify-end',
    """      {IS_MOBILE_RUNTIME && (
        <div
          className={cx(
            "pointer-events-none absolute inset-x-0 top-0 z-20 flex items-center justify-between bg-gradient-to-b from-chrome-black/55 to-transparent px-2 pb-6 pt-2 transition-opacity duration-200",
            shouldShowControls ? "opacity-100" : "opacity-0",
          )}
        >
          <button
            type="button"
            title={getString('topbar_back')}
            aria-label={getString('topbar_back')}
            onClick={() => {
              if (isFullscreen) toggleFullscreen();
              else useTabsStore.getState().go(-1);
            }}
            className={cx(
              "grid h-11 w-11 place-items-center text-chrome-white drop-shadow-md transition-transform active:scale-90",
              shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
            )}
          >
            <ChevronDown size={30} />
          </button>
          <div className="flex items-center">
            {"webkitShowPlaybackTargetPicker" in HTMLVideoElement.prototype && (
              <button
                type="button"
                title="AirPlay"
                aria-label="AirPlay"
                onClick={() => {
                  const video = containerRef.current?.querySelector("video") as
                    | (HTMLVideoElement & { webkitShowPlaybackTargetPicker?: () => void })
                    | null
                    | undefined;
                  video?.webkitShowPlaybackTargetPicker?.();
                }}
                className={cx(
                  "grid h-11 w-11 place-items-center text-chrome-white drop-shadow-md transition-transform active:scale-90",
                  shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
                )}
              >
                <Airplay size={24} />
              </button>
            )}
            <button
              type="button"
              {...{ [PLAYER_MENU_OWNER_ATTR]: "" }}
              title={getString("player_menu_settings")}
              aria-label={getString("player_menu_settings")}
              onClick={() => {
                setSettingsOpen((value) => !value);
                setSettingsPane("root");
              }}
              className={cx(
                "grid h-11 w-11 place-items-center text-chrome-white drop-shadow-md transition-transform active:scale-90",
                shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
              )}
            >
              <SettingsIcon size={24} />
            </button>
          </div>
        </div>
      )}
      {IS_MOBILE_RUNTIME && (
        <div
          className={cx(
            "pointer-events-none absolute inset-0 z-20 flex items-center justify-center gap-8 transition-opacity duration-200",
            shouldShowControls ? "opacity-100" : "opacity-0",
          )}
        >
          {showNextPrevious && (
            <button
              type="button"
              title={getString('previous')}
              onClick={playPrevious}
              className={cx(
                "grid h-14 w-14 place-items-center text-chrome-white/85 drop-shadow-md transition-transform active:scale-90",
                shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
              )}
            >
              <SkipBack size={34} fill="currentColor" />
            </button>
          )}
          <button
            type="button"
            title={isPlaying ? "Pause" : "Play"}
            onClick={togglePlay}
            className={cx(
              "grid h-16 w-16 place-items-center rounded-full bg-chrome-black/50 text-chrome-white transition-transform active:scale-90",
              shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
            )}
          >
            {isPlaying ? (
              <Pause size={34} fill="currentColor" />
            ) : (
              <Play size={34} fill="currentColor" className="ml-1" />
            )}
          </button>
          {showNextPrevious && (
            <button
              type="button"
              onClick={() => playNext()}
              className={cx(
                "grid h-14 w-14 place-items-center text-chrome-white/85 drop-shadow-md transition-transform active:scale-90",
                shouldShowControls ? "pointer-events-auto" : "pointer-events-none",
              )}
            >
              <SkipForward size={34} fill="currentColor" />
            </button>
          )}
        </div>
      )}
""",
)
# The controls sit flush with the bottom and side edges, as the seek bar does on Android.
replace(
    PLAYER_FILE,
    '          isTheaterMode ? "px-4 pb-3 sm:px-6 sm:pb-4 lg:px-8" : "px-3 pb-3 sm:px-5 sm:pb-4",\n',
    '          IS_MOBILE_RUNTIME\n'
    '            ? "px-0 pb-0"\n'
    '            : isTheaterMode\n'
    '              ? "px-4 pb-3 sm:px-6 sm:pb-4 lg:px-8"\n'
    '              : "px-3 pb-3 sm:px-5 sm:pb-4",\n',
)
# The row of pills above the seek bar.
replace(
    PLAYER_FILE,
    "          <div\n            ref={seekWheelRef}\n            data-progress-track\n",
    """          {IS_MOBILE_RUNTIME && (
            <div className="flex items-center justify-between gap-2 px-3 pb-1">
              <div className="flex min-w-0 items-center gap-2">
                <div
                  ref={timePillRef}
                  role={isLive ? undefined : "button"}
                  onClick={isLive ? undefined : () => setShowRemaining((value) => !value)}
                  className="whitespace-nowrap rounded-full bg-chrome-black/55 px-3 py-1 text-xs font-semibold tabular-nums text-chrome-white"
                >
                  <span ref={currentTimeRef} />
                  {!isLive && (
                    <>
                      {" "}
                      <span className="text-chrome-zinc-400">/</span>{" "}
                      <span ref={durationTimeRef} />
                    </>
                  )}
                </div>
                {isLive && (
                  <button
                    type="button"
                    onClick={seekToLiveEdge}
                    className="flex items-center gap-1 whitespace-nowrap rounded-full bg-chrome-black/55 px-3 py-1 text-xs font-bold uppercase tracking-wide text-chrome-white"
                  >
                    <span ref={liveDotRef} className="h-1.5 w-1.5 rounded-full bg-chrome-red-500 animate-pulse" />
                    {getString("live_badge")}
                  </button>
                )}
                <button
                  ref={showChapters ? chapterPillRef : undefined}
                  type="button"
                  onClick={() => togglePanel("chapters")}
                  className="hidden max-w-[240px] items-center gap-1 truncate rounded-full bg-chrome-black/55 px-3 py-1 text-xs font-medium text-chrome-white select-none"
                >
                  <span className="chapter-title truncate"></span>
                  <ChevronRight size={14} className="shrink-0 text-chrome-zinc-400" />
                </button>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  {...{ [PLAYER_MENU_OWNER_ATTR]: "" }}
                  title={getString("player_menu_quality")}
                  onClick={() => {
                    if (settingsOpen && settingsPane === "quality") {
                      setSettingsOpen(false);
                      setSettingsPane("root");
                    } else {
                      setSettingsOpen(true);
                      setSettingsPane("quality");
                    }
                  }}
                  className="rounded-full bg-chrome-black/55 px-3 py-1 text-xs font-bold text-chrome-white"
                >
                  {qualityLabel(selectedQualityId || "auto", supportedQualities, activeQualityLabel)}
                </button>
                {showFullscreen && (
                  <button
                    type="button"
                    title={getString('player_fullscreen')}
                    onClick={toggleFullscreen}
                    className="grid h-8 w-8 place-items-center rounded-full bg-chrome-black/55 text-chrome-white"
                  >
                    {isFullscreen ? <Minimize2 size={17} /> : <Maximize2 size={17} />}
                  </button>
                )}
              </div>
            </div>
          )}
          <div
            ref={seekWheelRef}
            data-progress-track
""",
)
# The desktop row of small buttons is not drawn on touch devices.
replace(
    PLAYER_FILE,
    '          <div data-touch-bar className="flex items-center justify-between gap-3">\n',
    '          {!IS_MOBILE_RUNTIME && (\n          <div data-touch-bar className="flex items-center justify-between gap-3">\n',
)
replace(
    PLAYER_FILE,
    "            </div>\n          </div>\n        </div>\n      </div>\n\n      <PlayerSettingsMenu\n",
    "            </div>\n          </div>\n          )}\n        </div>\n      </div>\n\n      <PlayerSettingsMenu\n",
)

# 15. Player fixes: no rounded corners on the video surface, whole-second swipe seeking (the seek
#     read-out showed the raw fraction), and the seek bar flush with the bottom edge like Android's.
replace(
    "src/components/player/Player.tsx",
    'const VIDEO_CORNERS = IS_LINUX_RUNTIME ? "rounded-none" : "rounded-xl";',
    'const VIDEO_CORNERS = IS_LINUX_RUNTIME || IS_MOBILE_RUNTIME ? "rounded-none" : "rounded-xl";',
)
replace(
    "src/components/player/gesture/touchGestures.ts",
    "        if (!cancelled && lastPreview) latest.current.seekBy(lastPreview.delta);\n",
    "        if (!cancelled && lastPreview) {\n"
    "          const seconds = Math.round(lastPreview.delta);\n"
    "          if (seconds !== 0) latest.current.seekBy(seconds);\n"
    "        }\n",
)
replace(
    PLAYER_FILE,
    '            ? "px-0 pb-0"\n',
    '            ? isFullscreen\n'
    '              ? "px-10 pb-7"\n'
    '              : "px-0 pb-0"\n',
)
with open("src/App.css", "a", encoding="utf-8", newline="\n") as css:
    css.write(
        "\n/* The seek bar sits on the bottom edge of the video, as on Android; the touch area reaches up. */\n"
        "@media (hover: none) {\n"
        "  [data-progress-track] {\n"
        "    height: 2.5rem !important;\n"
        "    margin-bottom: -1.1rem;\n"
        "  }\n"
        "}\n"
    )
print("patched src/App.css (seek bar position)")

# 16. Swipe-to-seek the way Flow for Android shows it (SeekDragOverlay): a dark rounded panel in the
#     middle of the video with the time the swipe will land on and, in the accent colour, how far
#     that is from where playback is. Nothing else is shown when the finger lifts.
OVERLAY_FILE = "src/components/player/gesture/overlay.tsx"
replace(
    OVERLAY_FILE,
    "function formatTime(seconds: number) {\n",
    "function formatScrubTime(seconds: number) {\n"
    "  if (!Number.isFinite(seconds) || seconds < 0) return \"00:00\";\n"
    "  const rounded = Math.floor(seconds);\n"
    "  const hours = Math.floor(rounded / 3600);\n"
    "  const minutes = Math.floor((rounded % 3600) / 60);\n"
    "  const secs = rounded % 60;\n"
    "  const pad = (value: number) => value.toString().padStart(2, \"0\");\n"
    "  return hours > 0 ? `${hours}:${pad(minutes)}:${pad(secs)}` : `${pad(minutes)}:${pad(secs)}`;\n"
    "}\n"
    "\n"
    "function formatTime(seconds: number) {\n",
)
replace(
    OVERLAY_FILE,
    '      {scrubPreview && (\n'
    '        <div className="pointer-events-none absolute left-1/2 top-8 z-30 -translate-x-1/2 rounded-full bg-chrome-black/70 px-5 py-2 text-sm font-bold text-chrome-white">\n'
    '          {formatTime(scrubPreview.target)} ({scrubPreview.delta >= 0 ? "+" : "-"}\n'
    '          {Math.abs(Math.round(scrubPreview.delta))}s)\n'
    '        </div>\n'
    '      )}\n',
    '      {scrubPreview && (\n'
    '        <div className="pointer-events-none absolute left-1/2 top-1/2 z-30 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center rounded-3xl bg-chrome-black/55 px-[22px] py-[14px]">\n'
    '          <span className="text-2xl font-bold tabular-nums text-chrome-white">{formatScrubTime(scrubPreview.target)}</span>\n'
    '          <span className="mt-0.5 text-sm font-semibold tabular-nums text-[var(--color-primary)]">\n'
    '            {scrubPreview.delta < 0 ? "-" : "+"}\n'
    '            {formatTime(Math.abs(scrubPreview.delta))}\n'
    '          </span>\n'
    '        </div>\n'
    '      )}\n',
)
replace(
    OVERLAY_FILE,
    "  seekBy: (delta: number) => void;\n",
    "  seekBy: (delta: number, silent?: boolean) => void;\n",
)
replace(
    "src/components/player/Player.tsx",
    "  const seekBy = useCallback((delta: number) => {\n"
    "    const video = videoRef.current;\n"
    "    const baseTime = video ? video.currentTime : usePlayerStore.getState().currentTime;\n"
    "    seekTo(baseTime + delta);\n"
    "    showSeekFeedback(delta > 0 ? \"forward\" : \"backward\", Math.abs(delta));\n",
    "  const seekBy = useCallback((delta: number, silent = false) => {\n"
    "    const video = videoRef.current;\n"
    "    const baseTime = video ? video.currentTime : usePlayerStore.getState().currentTime;\n"
    "    seekTo(baseTime + delta);\n"
    "    if (!silent) showSeekFeedback(delta > 0 ? \"forward\" : \"backward\", Math.abs(delta));\n",
)
GESTURES_FILE = "src/components/player/gesture/touchGestures.ts"
replace(
    GESTURES_FILE,
    "  seekBy: (delta: number) => void;\n",
    "  seekBy: (delta: number, silent?: boolean) => void;\n",
)
replace(
    GESTURES_FILE,
    "        if (!cancelled && lastPreview) {\n"
    "          const seconds = Math.round(lastPreview.delta);\n"
    "          if (seconds !== 0) latest.current.seekBy(seconds);\n"
    "        }\n",
    "        if (!cancelled && lastPreview) {\n"
    "          // Land on the time that was shown, even though playback kept moving during the swipe.\n"
    "          const seconds = lastPreview.target - (video()?.currentTime ?? baseTime);\n"
    "          if (Math.abs(seconds) >= 0.5) latest.current.seekBy(seconds, true);\n"
    "        }\n",
)

# 17. Tapping the video hides the controls while paused too, as in the YouTube app. Paused used to
#     force them on (`!isPlaying`), so a tap could never hide them. A tap that hides them while paused
#     is remembered until anything reveals them again (a tap, pausing, playing, a key press).
PLAYER = "src/components/player/Player.tsx"
replace(
    PLAYER,
    "  const [controlsVisible, setControlsVisible] = useState(true);\n",
    "  const [controlsVisible, setControlsVisible] = useState(true);\n"
    "  const [pausedControlsHidden, setPausedControlsHidden] = useState(false);\n",
)
replace(
    PLAYER,
    "  const shouldShowControls = controlsVisible || !isPlaying || settingsOpen || isScrubbing;\n",
    "  const shouldShowControls =\n"
    "    controlsVisible || (!isPlaying && !pausedControlsHidden) || settingsOpen || isScrubbing;\n",
)
replace(
    PLAYER,
    "  const revealControls = useCallback(() => {\n    setControlsVisible(true);\n",
    "  const revealControls = useCallback(() => {\n    setControlsVisible(true);\n    setPausedControlsHidden(false);\n",
)
replace(
    PLAYER,
    "    if (shouldShowControls) {\n      clearHideTimer();\n      setControlsVisible(false);\n",
    "    if (shouldShowControls) {\n      clearHideTimer();\n      setControlsVisible(false);\n      if (!isPlaying) setPausedControlsHidden(true);\n",
)

# 18. Fullscreen swipes as on Android: a vertical drag on the left half changes the brightness, on
#     the right half the volume, and only the middle third pulls the player out of fullscreen. The
#     gesture logic is in touchGestures.ts, the native side in src-tauri/src/ios_chrome.rs and the
#     read-out (Android's circular style, in the middle of the picture) in LevelHud.tsx; this puts
#     the read-out into the overlay.
replace(
    OVERLAY,
    'import { useTouchPlayerGestures, type ScrubPreview } from "./touchGestures";\n',
    'import { useTouchPlayerGestures, type LevelPreview, type ScrubPreview } from "./touchGestures";\n'
    'import { LevelHud } from "./LevelHud";\n',
)
replace(
    OVERLAY,
    "  const [scrubPreview, setScrubPreview] = useState<ScrubPreview>(null);\n",
    "  const [scrubPreview, setScrubPreview] = useState<ScrubPreview>(null);\n"
    "  const [levelPreview, setLevelPreview] = useState<LevelPreview>(null);\n",
)
replace(
    OVERLAY,
    "    onScrub: setScrubPreview,\n",
    "    onScrub: setScrubPreview,\n    onLevel: setLevelPreview,\n",
)
replace(
    OVERLAY,
    "      {seekFeedback && <SeekFeedback feedback={seekFeedback} compact={isCompact} />}\n",
    "      <LevelHud preview={levelPreview} />\n"
    "\n"
    "      {seekFeedback && <SeekFeedback feedback={seekFeedback} compact={isCompact} />}\n",
)

print("ios-ui: done")
