import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, PanelLeftClose, PanelLeftOpen, Search, Settings } from "lucide-react";
import { usePlayerStore } from "../../store/usePlayerStore";
import { useUiStore } from "../../store/useUiStore";
import { useAppSettingsStore } from "../../store/useAppSettingsStore";
import Logo from "../common/Logo";
import { IconButton } from "../ui/IconButton";
import { TopbarSearch } from "./TopbarSearch";
import { SIDEBAR_MENU_BUTTON_ID } from "./Topbar";
import { navigationHiddenOn } from "./AdaptiveNavigation";
import { NotificationsBell } from "../notifications/NotificationsBell";
import { ProfileMenuButton } from "../profiles/ProfileMenuButton";
import { SETTINGS } from "../../lib/settings/schema";
import { getString } from "../../lib/i18n/index";
import { FOCUS_SEARCH_EVENT } from "../../lib/windowEvents";
import { useUsesNavigationRail } from "../../lib/adaptive/useWindowSizeClass";

/*
  The top bar of Flow for Android, the same beside a bottom bar and beside a rail: wordmark on the
  left, then search, notifications, settings and the profile on the right. Search is an icon that
  turns the bar into a search field; there is no inline field, even on a tablet.
*/
export function AdaptiveTopbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const usesRail = useUsesNavigationRail();
  const toggleDrawer = useUiStore((s) => s.toggleWatchSidebar);
  const drawerOpen = useUiStore((s) => s.isWatchSidebarOpen);
  const isWatchPage = location.pathname.startsWith("/watch/");
  const seeThrough = usePlayerStore((s) => s.isAmbientSpreadShown && s.isPlayerBelowTopbar) && isWatchPage;
  const showAppLogo = useAppSettingsStore((s) => s.values[SETTINGS.SHOW_APP_LOGO_ICON] !== "false");
  const [searching, setSearching] = useState(false);

  // Running a search, or any other navigation, puts the bar back.
  useEffect(() => setSearching(false), [location.pathname, location.search]);
  useEffect(() => {
    if (!searching) return;
    const frame = requestAnimationFrame(() => window.dispatchEvent(new Event(FOCUS_SEARCH_EVENT)));
    return () => cancelAnimationFrame(frame);
  }, [searching]);

  const shell = `sticky top-0 z-40 flex h-14 items-center border-b border-transparent px-3 ${
    seeThrough ? "bg-transparent transition-colors duration-200 ease-out" : "bg-background"
  }`;

  if (searching) {
    return (
      <header className={`${shell} gap-1`}>
        <IconButton aria-label={getString("topbar_back")} onClick={() => setSearching(false)}>
          <ArrowLeft className="rtl:-scale-x-100" />
        </IconButton>
        <div className="flex min-w-0 flex-1 items-center">
          <TopbarSearch />
        </div>
      </header>
    );
  }

  const actions = (
    <div className="flex shrink-0 items-center gap-1">
      <IconButton data-flow-search-toggle aria-label={getString("search")} title={getString("search")} onClick={() => setSearching(true)}>
        <Search />
      </IconButton>
      <NotificationsBell />
      <IconButton onClick={() => navigate("/settings")} title={getString("settings_title")} aria-label={getString("settings_title")}>
        <Settings />
      </IconButton>
      <ProfileMenuButton />
    </div>
  );

  return (
    <header className={`${shell} justify-between gap-2`}>
      <div className="flex min-w-0 items-center gap-1">
        {(!usesRail || navigationHiddenOn(location.pathname)) && (
          <IconButton id={SIDEBAR_MENU_BUTTON_ID} aria-label={getString("sidebar_menu")} aria-expanded={drawerOpen} onClick={toggleDrawer}>
            {drawerOpen ? <PanelLeftClose className="rtl:-scale-x-100" /> : <PanelLeftOpen className="rtl:-scale-x-100" />}
          </IconButton>
        )}
        {showAppLogo && (
          <div className="cursor-pointer" onClick={() => navigate("/")}>
            <Logo size={36} showText={true} />
          </div>
        )}
      </div>
      {actions}
    </header>
  );
}
