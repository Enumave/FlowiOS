import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, HatGlasses, PanelLeftClose, PanelLeftOpen, Search, Settings } from "lucide-react";
import { usePlayerStore } from "../../store/usePlayerStore";
import { useUiStore } from "../../store/useUiStore";
import { useAppSettingsStore } from "../../store/useAppSettingsStore";
import Logo from "../common/Logo";
import { IconButton } from "../ui/IconButton";
import { TopbarSearch } from "./TopbarSearch";
import { SIDEBAR_MENU_BUTTON_ID } from "./Topbar";
import { NotificationsBell } from "../notifications/NotificationsBell";
import { ProfileMenuButton } from "../profiles/ProfileMenuButton";
import { SETTINGS } from "../../lib/settings/schema";
import { getString } from "../../lib/i18n/index";
import { toggleDeepFlow } from "../../lib/deepFlow";
import { FOCUS_SEARCH_EVENT } from "../../lib/windowEvents";
import { useUsesNavigationRail, useWindowSize } from "../../lib/adaptive/useWindowSizeClass";
import { WIDTH_BREAKPOINT } from "../../lib/adaptive/windowSizeClass";

/*
  The top bar of Flow for Android's two layouts.

  Beside a bottom bar (phones, medium windows) it is the phone bar: wordmark on the left and the
  actions on the right, with search behind an icon that turns the bar into a search field. Beside
  a rail (tablets) there is room for the search field to stay in the bar, centred, as on desktop.
*/
export function AdaptiveTopbar() {
  const navigate = useNavigate();
  const location = useLocation();
  const usesRail = useUsesNavigationRail();
  const { width } = useWindowSize();
  const roomy = width >= WIDTH_BREAKPOINT.medium;
  const toggleDrawer = useUiStore((s) => s.toggleWatchSidebar);
  const drawerOpen = useUiStore((s) => s.isWatchSidebarOpen);
  const isWatchPage = location.pathname.startsWith("/watch/");
  const seeThrough = usePlayerStore((s) => s.isAmbientSpreadShown && s.isPlayerBelowTopbar) && isWatchPage;
  const showAppLogo = useAppSettingsStore((s) => s.values[SETTINGS.SHOW_APP_LOGO_ICON] !== "false");
  const deepFlowActive = useAppSettingsStore((s) => s.values[SETTINGS.DEEP_FLOW_ACTIVE] === "true");
  const [searching, setSearching] = useState(false);

  // Running a search, or any other navigation, puts the bar back.
  useEffect(() => setSearching(false), [location.pathname, location.search]);
  // The bar grew into a rail layout with the field open: the inline field is already there.
  useEffect(() => {
    if (usesRail) setSearching(false);
  }, [usesRail]);
  useEffect(() => {
    if (!searching) return;
    const frame = requestAnimationFrame(() => window.dispatchEvent(new Event(FOCUS_SEARCH_EVENT)));
    return () => cancelAnimationFrame(frame);
  }, [searching]);

  const shell = `sticky top-0 z-40 flex h-14 items-center border-b border-transparent px-3 ${
    seeThrough ? "bg-transparent transition-colors duration-200 ease-out" : "bg-background"
  }`;

  if (searching && !usesRail) {
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
      {!usesRail && (
        <IconButton data-flow-search-toggle aria-label={getString("search")} title={getString("search")} onClick={() => setSearching(true)}>
          <Search />
        </IconButton>
      )}
      <NotificationsBell />
      {roomy && (
        <IconButton
          onClick={() => {
            void toggleDeepFlow();
          }}
          title={getString(deepFlowActive ? "deep_flow_topbar_disable" : "deep_flow_topbar_enable")}
          aria-pressed={deepFlowActive}
          className={deepFlowActive ? "deep-flow-topbar-active" : undefined}
        >
          <HatGlasses />
        </IconButton>
      )}
      <IconButton onClick={() => navigate("/settings")} title={getString("settings_title")} aria-label={getString("settings_title")}>
        <Settings />
      </IconButton>
      <ProfileMenuButton />
    </div>
  );

  return (
    <header className={`${shell} justify-between gap-2`}>
      <div className="flex min-w-0 items-center gap-1">
        {!usesRail && (
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
      {usesRail && (
        <div className="flex max-w-[720px] flex-1 items-center justify-center px-4 md:px-8">
          <TopbarSearch />
        </div>
      )}
      {actions}
    </header>
  );
}
