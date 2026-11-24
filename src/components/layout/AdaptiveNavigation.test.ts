import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { NavigationBar, NavigationRail } from "./AdaptiveNavigation";
import { AdaptiveTopbar } from "./AdaptiveTopbar";
import { SETTINGS } from "../../lib/settings/schema";
import { useAppSettingsStore } from "../../store/useAppSettingsStore";
import { __setWindowSizeForTests } from "../../lib/adaptive/useWindowSizeClass";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

let host: HTMLDivElement;
let root: Root;

function show(path: string, element: ReturnType<typeof createElement>) {
  act(() => {
    root.render(createElement(MemoryRouter, { key: path, initialEntries: [path] }, element));
  });
}

const labels = () => [...host.querySelectorAll("nav a, nav button")].map((el) => el.textContent?.trim());

describe("adaptive navigation", () => {
  beforeEach(() => {
    vi.stubGlobal("matchMedia", () => ({ matches: false, addEventListener: () => {}, removeEventListener: () => {} }));
    vi.stubGlobal(
      "ResizeObserver",
      class {
        observe() {}
        disconnect() {}
        unobserve() {}
      },
    );
    host = document.createElement("div");
    document.body.append(host);
    root = createRoot(host);
  });

  afterEach(() => {
    act(() => root.unmount());
    host.remove();
    vi.unstubAllGlobals();
    useAppSettingsStore.setState({ values: {} });
  });

  it("draws Android's five tabs on the bottom bar and marks the current one", () => {
    show("/subscriptions", createElement(NavigationBar));
    const bar = host.querySelector("nav[data-flow-nav='bar']");
    expect(bar).not.toBeNull();
    expect(bar?.querySelectorAll("a, button").length).toBeLessThanOrEqual(5);
    expect(bar?.querySelector("a[aria-current='page']")?.getAttribute("href")).toBe("/subscriptions");
  });

  it("keeps Library selected on the pages it opens", () => {
    show("/history", createElement(NavigationBar));
    expect(host.querySelector("a[aria-current='page']")?.getAttribute("href")).toBe("/library");
  });

  it("moves a sixth tab behind More", () => {
    useAppSettingsStore.setState({ values: { [SETTINGS.CATEGORIES_NAV_TAB_ENABLED]: "true" } });
    show("/", createElement(NavigationBar));
    const items = host.querySelectorAll("nav[data-flow-nav='bar'] > a, nav[data-flow-nav='bar'] > button");
    expect(items.length).toBe(5);
    expect(items[items.length - 1]?.getAttribute("aria-haspopup")).toBe("menu");
    expect(labels()).not.toContain("Explore");
  });

  it("is hidden where the page covers the chrome", () => {
    show("/watch/abc", createElement(NavigationBar));
    expect(host.querySelector("nav")).toBeNull();
    show("/settings", createElement(NavigationBar));
    expect(host.querySelector("nav")).toBeNull();
  });

  it("shows the rail's tabs, and a toggle only where it can open", () => {
    __setWindowSizeForTests(1024, 768);
    show("/subscriptions", createElement(NavigationRail, { onOpenDrawer: () => {} }));
    expect(host.querySelector("nav[data-flow-nav='rail']")).not.toBeNull();
    expect(host.querySelector("a[aria-current='page']")?.getAttribute("href")).toBe("/subscriptions");
    // 1024 wide is expanded, not large: no expand toggle.
    expect(host.querySelector("[aria-expanded]")).toBeNull();
    __setWindowSizeForTests(1366, 1024);
    show("/subscriptions", createElement(NavigationRail, { onOpenDrawer: () => {} }));
    expect(host.querySelector("button[aria-expanded='false']")).not.toBeNull();
  });

  it("labels the tabs as Android does", () => {
    __setWindowSizeForTests(1024, 768);
    show("/", createElement(NavigationRail));
    expect(labels()).toEqual(expect.arrayContaining(["Home", "Subs", "Library"]));
  });

  it("has no button of its own at the foot of the rail", () => {
    __setWindowSizeForTests(1024, 768);
    show("/", createElement(NavigationRail));
    expect(host.querySelectorAll("nav[data-flow-nav='rail'] button").length).toBe(0);
  });

  it("turns the bar into a search field behind an icon, on a phone and on a tablet alike", () => {
    __setWindowSizeForTests(390, 844);
    show("/", createElement(AdaptiveTopbar));
    const searchButton = host.querySelector("button[data-flow-search-toggle]") as HTMLButtonElement | null;
    expect(searchButton).not.toBeNull();
    expect(host.querySelector("input")).toBeNull();
    act(() => searchButton?.click());
    expect(host.querySelector("input")).not.toBeNull();

    __setWindowSizeForTests(1180, 820);
    show("/", createElement(AdaptiveTopbar));
    expect(host.querySelector("button[data-flow-search-toggle]")).not.toBeNull();
    expect(host.querySelector("input")).toBeNull();
  });
});
