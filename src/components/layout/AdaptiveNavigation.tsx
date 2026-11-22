import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, MoreHorizontal, PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { SidebarNavIcon, type SidebarNavIconName } from "../ui/SidebarNavIcon";
import { ShortsAIcon, ShortsIcon } from "../ui/ShortsIcon";
import { AnchoredPortalMenu, type MenuAnchor } from "../ui/AnchoredPortalMenu";
import { IconButton } from "../ui/IconButton";
import { useAppSettingsStore } from "../../store/useAppSettingsStore";
import { getString } from "../../lib/i18n/index";
import { announceHomeReselected } from "../../lib/homeReselect";
import { useShortsEnabled } from "../../lib/useShortsContent";
import { useMusicEnabled } from "../../lib/useMusicContent";
import { SETTINGS } from "../../lib/settings/schema";
import { profileStorage } from "../../lib/storage/profileStorage";
import { MAX_BAR_TABS, railItemCapacity, splitTabsForOverflow } from "../../lib/adaptive/windowSizeClass";
import { useRailExpandable } from "../../lib/adaptive/useWindowSizeClass";
import { revealBar, useBarHidden } from "../../lib/adaptive/barVisibility";

/*
  Primary navigation as Flow for Android draws it (FlowNavigationBar / FlowNavigationRail):
  a Material 3 bottom bar with a pill behind the selected icon on phones and medium windows, and
  a start-edge rail on expanded tablet windows. Both show the same tabs, and both move what does
  not fit behind "More".
*/

export type NavTab = {
  id: "home" | "shorts" | "music" | "subscriptions" | "library" | "explore";
  to: string;
  label: string;
  icon: ReactNode;
  activeIcon: ReactNode;
  /** Whether this tab owns the current path, so a page opened from it keeps it selected. */
  owns: (pathname: string) => boolean;
  onReselect?: () => void;
};

const ICON = "h-6 w-6 shrink-0";

function pair(name: SidebarNavIconName) {
  return {
    icon: <SidebarNavIcon name={name} variant="outline" className={ICON} />,
    activeIcon: <SidebarNavIcon name={name} variant="filled" className={ICON} />,
  };
}

const startsWithAny = (pathname: string, prefixes: string[]) =>
  prefixes.some((prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`));

const LIBRARY_PATHS = [
  "/library",
  "/history",
  "/playlists",
  "/playlist",
  "/watch-later",
  "/liked",
  "/downloads",
  "/local-media",
  "/notes",
  "/saved-shorts",
  "/recap",
];

/**
 * The tabs to show, in Android's order. Search, Explore and Downloads are off by default there,
 * so Explore only joins when it is switched on; the drawer reaches everything else.
 */
export function useNavTabs(): NavTab[] {
  const location = useLocation();
  const shortsEnabled = useShortsEnabled();
  const shortsNavEnabled = useAppSettingsStore((s) => s.values[SETTINGS.SHORTS_NAVIGATION_ENABLED] !== "false");
  const musicEnabled = useMusicEnabled();
  const musicNavEnabled = useAppSettingsStore((s) => s.values[SETTINGS.MUSIC_NAVIGATION_ENABLED] !== "false");
  const exploreTabOn = useAppSettingsStore((s) => s.values[SETTINGS.CATEGORIES_NAV_TAB_ENABLED] === "true");

  const tabs: NavTab[] = [
    {
      id: "home",
      to: "/",
      label: getString("home"),
      ...pair("home"),
      owns: (path) => path === "/" || path === "/feed",
      onReselect: () => {
        if (location.pathname === "/") announceHomeReselected();
      },
    },
  ];
  if (shortsEnabled && shortsNavEnabled) {
    tabs.push({
      id: "shorts",
      to: "/shorts",
      label: getString("sidebar_shorts"),
      icon: <ShortsIcon className={ICON} />,
      activeIcon: <ShortsAIcon className={ICON} />,
      owns: (path) => startsWithAny(path, ["/shorts"]),
    });
  }
  if (musicEnabled && musicNavEnabled) {
    tabs.push({
      id: "music",
      to: "/music",
      label: getString("sidebar_music"),
      ...pair("music"),
      owns: (path) => startsWithAny(path, ["/music", "/albums"]),
    });
  }
  tabs.push(
    {
      id: "subscriptions",
      to: "/subscriptions",
      label: getString("sidebar_subscriptions"),
      ...pair("subscriptions"),
      owns: (path) => startsWithAny(path, ["/subscriptions", "/channel"]),
    },
    {
      id: "library",
      to: "/library",
      label: getString("sidebar_you"),
      ...pair("you"),
      owns: (path) => startsWithAny(path, LIBRARY_PATHS),
    },
  );
  if (exploreTabOn) {
    tabs.push({
      id: "explore",
      to: "/explore",
      label: getString("sidebar_explore"),
      ...pair("explore"),
      owns: (path) => startsWithAny(path, ["/explore"]),
    });
  }
  return tabs;
}

function selectedTabOf(tabs: NavTab[], pathname: string): NavTab | undefined {
  return tabs.find((tab) => tab.owns(pathname));
}

/** The page sits full screen over the chrome: Watch, and Settings, which has its own way back. */
export function navigationHiddenOn(pathname: string): boolean {
  return pathname.startsWith("/watch/") || pathname.startsWith("/settings");
}

const PILL_ACTIVE = "bg-surface-container-high text-chrome-neutral-100";
const PILL_IDLE = "text-chrome-neutral-300";

function OverflowMenu({
  anchor,
  tabs,
  selected,
  onClose,
}: {
  anchor: MenuAnchor;
  tabs: NavTab[];
  selected: NavTab | undefined;
  onClose: () => void;
}) {
  return (
    <AnchoredPortalMenu
      anchor={anchor}
      onClose={onClose}
      className="z-50 w-56 rounded-xl border border-chrome-neutral-800 bg-surface-container-high py-1.5"
    >
      {tabs.map((tab) => (
        <Link
          key={tab.id}
          to={tab.to}
          onClick={() => {
            tab.onReselect?.();
            onClose();
          }}
          className={`flex items-center gap-3 px-4 py-2.5 text-sm ${
            tab === selected ? "font-medium text-chrome-neutral-100" : "text-chrome-neutral-300"
          }`}
        >
          {tab === selected ? tab.activeIcon : tab.icon}
          <span className="truncate">{tab.label}</span>
        </Link>
      ))}
    </AnchoredPortalMenu>
  );
}

/** Opens the overflow menu from the button that was pressed, above it on a bar. */
function useOverflowMenu() {
  const [anchor, setAnchor] = useState<MenuAnchor | null>(null);
  const open = useCallback((button: HTMLElement, placement: "above" | "beside") => {
    const rect = button.getBoundingClientRect();
    setAnchor(
      placement === "above"
        ? { top: rect.top, right: rect.right, flipBottom: rect.top }
        : { top: rect.top, left: rect.right + 8, flipBottom: rect.bottom },
    );
  }, []);
  const close = useCallback(() => setAnchor(null), []);
  return { anchor, open, close };
}

/** The bottom bar of phones and medium windows. */
export function NavigationBar() {
  const location = useLocation();
  const tabs = useNavTabs();
  const menu = useOverflowMenu();
  const scrolledAway = useBarHidden();
  // A new page starts with the bar showing.
  useEffect(() => revealBar(), [location.pathname]);
  if (navigationHiddenOn(location.pathname)) return null;

  const selected = selectedTabOf(tabs, location.pathname);
  const { shown, overflow } = splitTabsForOverflow(tabs, MAX_BAR_TABS);

  return (
    <nav
      aria-label={getString("sidebar_menu")}
      data-flow-nav="bar"
      aria-hidden={scrolledAway || undefined}
      className={`flex shrink-0 items-stretch overflow-hidden bg-background transition-[height] duration-200 ease-out ${
        scrolledAway ? "pointer-events-none h-0" : "h-16 border-t border-chrome-neutral-800/50"
      }`}
    >
      {shown.map((tab) => {
        const active = tab === selected;
        return (
          <Link
            key={tab.id}
            to={tab.to}
            aria-current={active ? "page" : undefined}
            onClick={tab.onReselect}
            className="flex min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 pt-1"
          >
            <span className={`grid h-8 w-16 place-items-center rounded-full transition-colors duration-200 ${active ? PILL_ACTIVE : PILL_IDLE}`}>
              {active ? tab.activeIcon : tab.icon}
            </span>
            <span className={`max-w-full truncate text-xs ${active ? "font-medium text-chrome-neutral-100" : "text-chrome-neutral-300"}`}>
              {tab.label}
            </span>
          </Link>
        );
      })}
      {overflow.length > 0 && (
        <>
          <button
            type="button"
            aria-haspopup="menu"
            aria-expanded={menu.anchor !== null}
            onClick={(event) => menu.open(event.currentTarget, "above")}
            className="flex min-w-0 flex-1 flex-col items-center justify-center gap-1 px-1 pt-1"
          >
            <span className={`grid h-8 w-16 place-items-center rounded-full ${selected && overflow.includes(selected) ? PILL_ACTIVE : PILL_IDLE}`}>
              <MoreHorizontal className={ICON} />
            </span>
            <span className="max-w-full truncate text-xs text-chrome-neutral-300">{getString("sidebar_show_more")}</span>
          </button>
          {menu.anchor && <OverflowMenu anchor={menu.anchor} tabs={overflow} selected={selected} onClose={menu.close} />}
        </>
      )}
    </nav>
  );
}

const RAIL_EXPANDED_KEY = "flow_rail_expanded";
const RAIL_HEADER_PX = 44;
const RAIL_FOOTER_PX = 44;
const RAIL_PADDING_PX = 24;

function readRailExpanded(): boolean {
  try {
    return profileStorage.getItem(RAIL_EXPANDED_KEY) === "true";
  } catch {
    return false;
  }
}

/**
 * The start-edge rail of expanded tablet windows, and of a phone on its side. Collapsed it is a
 * 96-wide column of icons over labels; on large windows its header opens it to labels beside the
 * icons. When the window is too short for every tab the last slot becomes "More".
 */
export function NavigationRail({ onOpenDrawer }: { onOpenDrawer: () => void }) {
  const location = useLocation();
  const tabs = useNavTabs();
  const expandable = useRailExpandable();
  const menu = useOverflowMenu();
  const [openPref, setOpenPref] = useState(readRailExpanded);
  const expanded = expandable && openPref;
  const hostRef = useRef<HTMLDivElement>(null);
  const [capacity, setCapacity] = useState(tabs.length);
  const itemHeight = expanded ? 56 : 64;

  useLayoutEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const measure = () => {
      // Not laid out yet (or hidden): keep what is shown rather than collapsing everything into More.
      if (host.clientHeight === 0) return;
      const header = RAIL_HEADER_PX + RAIL_FOOTER_PX;
      setCapacity(railItemCapacity(host.clientHeight - header - RAIL_PADDING_PX, itemHeight));
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(host);
    return () => observer.disconnect();
  }, [itemHeight]);

  useEffect(() => {
    try {
      profileStorage.setItem(RAIL_EXPANDED_KEY, String(openPref));
    } catch {
      // Not remembered; the rail still works.
    }
  }, [openPref]);

  if (navigationHiddenOn(location.pathname)) return null;

  const selected = selectedTabOf(tabs, location.pathname);
  const { shown, overflow } = splitTabsForOverflow(tabs, capacity);
  const toggleLabel = getString("sidebar_menu");

  return (
    <div ref={hostRef} className={`shrink-0 ${expanded ? "w-56" : "w-24"}`}>
      <nav
        aria-label={getString("sidebar_menu")}
        data-flow-nav="rail"
        data-expanded={expanded}
        className="flex h-full flex-col bg-background px-3 py-3"
      >
        <div className={`flex h-11 items-center ${expanded ? "justify-start" : "justify-center"}`}>
          {expandable && (
            <IconButton
              aria-label={toggleLabel}
              title={toggleLabel}
              aria-expanded={expanded}
              onClick={() => setOpenPref((value) => !value)}
            >
              {expanded ? <PanelLeftClose className="rtl:-scale-x-100" /> : <PanelLeftOpen className="rtl:-scale-x-100" />}
            </IconButton>
          )}
        </div>
        <div className="flex flex-1 flex-col items-stretch justify-center gap-1">
          {shown.map((tab) => {
            const active = tab === selected;
            return (
              <Link
                key={tab.id}
                to={tab.to}
                aria-current={active ? "page" : undefined}
                onClick={tab.onReselect}
                className={
                  expanded
                    ? `flex h-14 items-center gap-3 rounded-full px-4 text-sm ${active ? PILL_ACTIVE : PILL_IDLE}`
                    : "flex h-16 flex-col items-center justify-center gap-1"
                }
              >
                {expanded ? (
                  <>
                    {active ? tab.activeIcon : tab.icon}
                    <span className="truncate">{tab.label}</span>
                  </>
                ) : (
                  <>
                    <span className={`grid h-8 w-14 place-items-center rounded-full transition-colors duration-200 ${active ? PILL_ACTIVE : PILL_IDLE}`}>
                      {active ? tab.activeIcon : tab.icon}
                    </span>
                    <span className={`max-w-full truncate text-xs ${active ? "font-medium text-chrome-neutral-100" : "text-chrome-neutral-300"}`}>
                      {tab.label}
                    </span>
                  </>
                )}
              </Link>
            );
          })}
          {overflow.length > 0 && (
            <>
              <button
                type="button"
                aria-haspopup="menu"
                aria-expanded={menu.anchor !== null}
                onClick={(event) => menu.open(event.currentTarget, "beside")}
                className={expanded ? `flex h-14 items-center gap-3 rounded-full px-4 text-sm ${PILL_IDLE}` : "flex h-16 flex-col items-center justify-center gap-1"}
              >
                {expanded ? (
                  <>
                    <MoreHorizontal className={ICON} />
                    <span className="truncate">{getString("sidebar_show_more")}</span>
                  </>
                ) : (
                  <>
                    <span className={`grid h-8 w-14 place-items-center rounded-full ${selected && overflow.includes(selected) ? PILL_ACTIVE : PILL_IDLE}`}>
                      <MoreHorizontal className={ICON} />
                    </span>
                    <span className="text-xs text-chrome-neutral-300">{getString("sidebar_show_more")}</span>
                  </>
                )}
              </button>
              {menu.anchor && <OverflowMenu anchor={menu.anchor} tabs={overflow} selected={selected} onClose={menu.close} />}
            </>
          )}
        </div>
        {/* Sync, Extensions, Support and the rest of the library live in the drawer. */}
        <div className={`flex h-11 items-center ${expanded ? "justify-start" : "justify-center"}`}>
          <IconButton aria-label={getString("sidebar_menu")} title={getString("sidebar_menu")} onClick={onOpenDrawer}>
            <Menu />
          </IconButton>
        </div>
      </nav>
    </div>
  );
}
