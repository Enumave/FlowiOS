import { useLayoutEffect, useMemo, useSyncExternalStore } from "react";
import { IS_ADAPTIVE_LAYOUT } from "./runtime";
import {
  feedGridLayoutFor,
  playerLayoutModeFor,
  railIsExpandable,
  usesNavigationRail,
  windowSizeClassOf,
  type FeedGridLayout,
  type PlayerLayoutMode,
  type WindowSizeClass,
} from "./windowSizeClass";

/*
  The size the app is laid out at: the window, not the display, so Split View, Slide Over and
  Stage Manager windows lay out like the narrow devices they behave as (Flow for Android measures
  the same way). The on-screen keyboard is not part of that: opening it shrinks the viewport, and
  reading that as a short window would swap the bottom bar for a rail under the user's fingers.
*/

type Size = { width: number; height: number };

let current: Size = readSize(null);
const listeners = new Set<() => void>();
let attached = false;

function textEntryFocused(): boolean {
  const el = typeof document === "undefined" ? null : document.activeElement;
  if (!(el instanceof HTMLElement)) return false;
  return el.isContentEditable || el instanceof HTMLTextAreaElement || (el instanceof HTMLInputElement && el.type !== "checkbox" && el.type !== "radio" && el.type !== "range" && el.type !== "button");
}

function readSize(previous: Size | null): Size {
  if (typeof window === "undefined") return { width: 1280, height: 800 };
  const width = Math.round(document.documentElement.clientWidth || window.innerWidth);
  let height = Math.round(window.innerHeight);
  // A shorter window while text is being typed is the keyboard, not a resize.
  if (previous && previous.width === width && height < previous.height && textEntryFocused()) height = previous.height;
  return { width, height };
}

function refresh() {
  const next = readSize(current);
  if (next.width === current.width && next.height === current.height) return;
  current = next;
  publishRootAttributes();
  listeners.forEach((listener) => listener());
}

function publishRootAttributes() {
  if (typeof document === "undefined") return;
  const sc = windowSizeClassOf(current.width, current.height);
  const root = document.documentElement;
  root.dataset.widthClass = sc.width;
  root.dataset.heightClass = sc.height;
  root.dataset.orientation = sc.isLandscape ? "landscape" : "portrait";
  root.dataset.navigation = usesNavigationRail(sc) ? "rail" : "bar";
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  if (!attached && typeof window !== "undefined") {
    attached = true;
    window.addEventListener("resize", refresh);
    window.addEventListener("orientationchange", refresh);
    window.addEventListener("focusout", refresh);
    refresh();
    publishRootAttributes();
  }
  return () => {
    listeners.delete(listener);
  };
}

const getSnapshot = () => current;
const getServerSnapshot = (): Size => ({ width: 1280, height: 800 });

/** Test hook: sets the size directly and notifies readers. */
export function __setWindowSizeForTests(width: number, height: number) {
  current = { width, height };
  publishRootAttributes();
  listeners.forEach((listener) => listener());
}

export function useWindowSize(): Size {
  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

export function useWindowSizeClass(): WindowSizeClass {
  const { width, height } = useWindowSize();
  return useMemo(() => windowSizeClassOf(width, height), [width, height]);
}

/** Whether primary navigation runs down the start edge rather than along the bottom. */
export function useUsesNavigationRail(): boolean {
  return usesNavigationRail(useWindowSizeClass());
}

export function useRailExpandable(): boolean {
  return railIsExpandable(useWindowSizeClass());
}

export function usePlayerLayoutMode(opts: { isFullscreen?: boolean; isPip?: boolean } = {}): PlayerLayoutMode {
  const sc = useWindowSizeClass();
  return playerLayoutModeFor(sc, opts);
}

export function useFeedGridLayout(options: { fixedColumns?: number | null; maxAutoColumns?: number } = {}): FeedGridLayout {
  const { width } = useWindowSize();
  const { fixedColumns = null, maxAutoColumns } = options;
  return useMemo(() => feedGridLayoutFor(width, { fixedColumns, maxAutoColumns }), [width, fixedColumns, maxAutoColumns]);
}

// ---------------------------------------------------------------------------
// Content width
// ---------------------------------------------------------------------------

/*
  Android sizes a grid from the pane it sits in, not from the window: beside a rail the feed has
  less room. The routed page's scroll container reports its width here, so grids count columns
  for the space they really have.
*/
let contentWidth = 0;
const contentListeners = new Set<() => void>();

export function reportContentWidth(width: number) {
  const rounded = Math.round(width);
  if (rounded === contentWidth) return;
  contentWidth = rounded;
  contentListeners.forEach((listener) => listener());
}

function subscribeContent(listener: () => void) {
  contentListeners.add(listener);
  return () => {
    contentListeners.delete(listener);
  };
}

/** The width of the page area, falling back to the window until the page has been measured. */
export function useContentWidth(): number {
  const measured = useSyncExternalStore(subscribeContent, () => contentWidth, () => 0);
  const { width } = useWindowSize();
  return measured > 0 ? measured : width;
}

const subscribeNothing = () => () => {};

/**
 * `useContentWidth` for code shared with desktop: where the adaptive layouts are off it never
 * subscribes, so a desktop window resize does not re-render every grid.
 */
export function useAdaptiveContentWidth(): number | null {
  const measured = useSyncExternalStore(IS_ADAPTIVE_LAYOUT ? subscribeContent : subscribeNothing, () => contentWidth, () => 0);
  const windowWidth = useSyncExternalStore(IS_ADAPTIVE_LAYOUT ? subscribe : subscribeNothing, () => current.width, () => 0);
  if (!IS_ADAPTIVE_LAYOUT) return null;
  return measured > 0 ? measured : windowWidth;
}

/** Keeps `reportContentWidth` current for the element the routed pages scroll in. */
export function useReportContentWidth(ref: { current: HTMLElement | null }, enabled = true) {
  useLayoutEffect(() => {
    const element = ref.current;
    if (!enabled || !element) return;
    const measure = () => reportContentWidth(element.clientWidth);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [ref, enabled]);
}
