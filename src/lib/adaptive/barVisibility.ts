import { useLayoutEffect, useSyncExternalStore, type RefObject } from "react";
import { IS_ADAPTIVE_LAYOUT } from "./runtime";

/*
  Flow for Android's bottom bar hides on scroll by default: it leaves as the page scrolls down and
  returns on the first scroll up, so the feed gets the whole screen. The page's scroller reports its
  direction here and the bar reads it.
*/

const HIDE_AFTER_PX = 24;

let hidden = false;
const listeners = new Set<() => void>();

function setHidden(next: boolean) {
  if (hidden === next) return;
  hidden = next;
  listeners.forEach((listener) => listener());
}

/** Pure rule: given the scroll position and how far it has travelled one way, should the bar hide? */
export function nextBarHidden(
  wasHidden: boolean,
  scrollTop: number,
  delta: number,
  travelled: number,
): { hidden: boolean; travelled: number } {
  if (scrollTop <= 0) return { hidden: false, travelled: 0 };
  const sameDirection = travelled === 0 || Math.sign(travelled) === Math.sign(delta);
  const total = sameDirection ? travelled + delta : delta;
  if (total >= HIDE_AFTER_PX) return { hidden: true, travelled: total };
  if (total <= -HIDE_AFTER_PX / 3) return { hidden: false, travelled: total };
  return { hidden: wasHidden, travelled: total };
}

export function useReportBarVisibility(scroller: RefObject<HTMLElement | null>, enabled: boolean) {
  useLayoutEffect(() => {
    const container = scroller.current;
    if (!enabled || !container) return;
    let last = container.scrollTop;
    let travelled = 0;
    const onScroll = () => {
      const top = container.scrollTop;
      const next = nextBarHidden(hidden, top, top - last, travelled);
      last = top;
      travelled = next.travelled;
      setHidden(next.hidden);
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      container.removeEventListener("scroll", onScroll);
      setHidden(false);
    };
  }, [scroller, enabled]);
}

const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};

/** Whether the bottom bar is slid away by scrolling. */
export function useBarHidden(): boolean {
  return useSyncExternalStore(subscribe, () => hidden, () => false);
}

/** Show the bar again, as when the route changes. */
export function revealBar() {
  setHidden(false);
}

export { IS_ADAPTIVE_LAYOUT as BAR_HIDING_ENABLED };
