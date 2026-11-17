import { useEffect } from "react";
import { useTabsStore } from "../store/useTabsStore";
import { IS_MOBILE_RUNTIME } from "./platform";
import { PLAYER_VIDEO_LAYER_ATTR } from "./playerMenuDismiss";

/** Holding a finger this long opens the same menu a right click would. */
const LONG_PRESS_MS = 550;
/** A finger that moves farther than this is scrolling, not holding. */
const MOVE_SLOP_PX = 10;
/** A swipe that starts this close to the edge goes back. */
const EDGE_PX = 24;
const BACK_SWIPE_PX = 80;
/** Pulling a page down this far at the top refreshes it. */
const PULL_TRIGGER_PX = 100;
const PULL_MAX_PX = 150;

const pullHandlers = new Set<() => void>();

/** A page that can refresh calls this; a pull down at the top of the page then runs `handler`. */
export function registerPullRefresh(handler: () => void): () => void {
  pullHandlers.add(handler);
  return () => {
    pullHandlers.delete(handler);
  };
}

const NATIVE_PRESS_TARGETS = `input, textarea, select, [contenteditable="true"], [${PLAYER_VIDEO_LAYER_ATTR}]`;

function scrollerFor(start: Element | null): HTMLElement | null {
  let fallback: HTMLElement | null = null;
  for (let node = start; node; node = node.parentElement) {
    if (!(node instanceof HTMLElement)) continue;
    const overflowY = getComputedStyle(node).overflowY;
    if (overflowY !== "auto" && overflowY !== "scroll") continue;
    if (node.scrollHeight > node.clientHeight + 1) return node;
    fallback ??= node;
  }
  return fallback;
}

function createIndicator() {
  const element = document.createElement("div");
  element.setAttribute("aria-hidden", "true");
  element.style.cssText = [
    "position:fixed",
    "left:50%",
    "top:env(safe-area-inset-top, 0px)",
    "z-index:9999",
    "width:36px",
    "height:36px",
    "margin-left:-18px",
    "border-radius:9999px",
    "display:none",
    "align-items:center",
    "justify-content:center",
    "pointer-events:none",
    "background:var(--color-surface-container-highest, #333)",
    "color:var(--color-primary, #fff)",
    "box-shadow:0 2px 8px rgba(0,0,0,0.35)",
  ].join(";");
  element.innerHTML =
    '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" ' +
    'stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7"/><path d="M21 3v6h-6"/></svg>';
  document.body.appendChild(element);
  return element;
}

/**
 * Touch gestures for the whole app, matching Flow for Android: hold to open a menu, swipe in
 * from the left edge to go back, and pull a page down at the top to refresh it.
 */
export function useTouchNavigation() {
  useEffect(() => {
    if (!IS_MOBILE_RUNTIME) return;

    const indicator = createIndicator();
    const rtl = () => document.documentElement.dir === "rtl";

    let pressTimer: number | undefined;
    let pressStartX = 0;
    let pressStartY = 0;
    let pressTarget: Element | null = null;
    let pressFired = false;

    let edgeStartX = -1;
    let edgeStartY = 0;
    let edgeDx = 0;
    let edgeDy = 0;

    let pullScroller: HTMLElement | null = null;
    let pullStartY = 0;
    let pullStartX = 0;
    let pullDistance = 0;
    let pullCancelled = true;

    const cancelPress = () => {
      if (pressTimer !== undefined) window.clearTimeout(pressTimer);
      pressTimer = undefined;
    };

    const showPull = (distance: number) => {
      const shown = Math.min(PULL_MAX_PX, distance * 0.5);
      indicator.style.display = "flex";
      indicator.style.transition = "none";
      indicator.style.opacity = String(Math.min(1, distance / PULL_TRIGGER_PX));
      indicator.style.transform = `translateY(${shown - 20}px) rotate(${distance * 2.4}deg)`;
    };

    const hidePull = () => {
      indicator.style.transition = "transform 160ms ease, opacity 160ms ease";
      indicator.style.opacity = "0";
      indicator.style.transform = "translateY(-20px)";
      window.setTimeout(() => {
        if (indicator.style.opacity === "0") indicator.style.display = "none";
      }, 180);
    };

    const spinThenHide = () => {
      indicator.style.transition = "none";
      indicator.style.opacity = "1";
      indicator.animate(
        [
          { transform: `translateY(${PULL_TRIGGER_PX * 0.5 - 20}px) rotate(0deg)` },
          { transform: `translateY(${PULL_TRIGGER_PX * 0.5 - 20}px) rotate(360deg)` },
        ],
        { duration: 700, iterations: 1 },
      );
      window.setTimeout(hidePull, 700);
    };

    const onTouchStart = (event: TouchEvent) => {
      pressFired = false;
      cancelPress();
      edgeStartX = -1;
      pullCancelled = true;
      indicator.style.display = "none";

      if (event.touches.length !== 1) return;
      const touch = event.touches[0];
      const target = event.target instanceof Element ? event.target : null;

      // Hold to open the menu a right click would.
      if (target && !target.closest(NATIVE_PRESS_TARGETS)) {
        pressStartX = touch.clientX;
        pressStartY = touch.clientY;
        pressTarget = target;
        pressTimer = window.setTimeout(() => {
          pressTimer = undefined;
          if (!pressTarget || !pressTarget.isConnected) return;
          const menu = new MouseEvent("contextmenu", {
            bubbles: true,
            cancelable: true,
            composed: true,
            clientX: pressStartX,
            clientY: pressStartY,
            button: 2,
            view: window,
          });
          // A handler that opens a menu calls preventDefault, which is how we know it took it.
          if (!pressTarget.dispatchEvent(menu)) {
            pressFired = true;
            window.getSelection()?.removeAllRanges();
          }
        }, LONG_PRESS_MS);
      }

      // Swipe in from the left edge (right edge in right-to-left languages) to go back.
      const fromEdge = rtl() ? window.innerWidth - touch.clientX <= EDGE_PX : touch.clientX <= EDGE_PX;
      if (fromEdge) {
        edgeStartX = touch.clientX;
        edgeStartY = touch.clientY;
        edgeDx = 0;
        edgeDy = 0;
        return;
      }

      // Pull a page down at the top to refresh it.
      if (pullHandlers.size > 0 && target && !target.closest(`[${PLAYER_VIDEO_LAYER_ATTR}]`)) {
        const scroller = scrollerFor(target);
        if (scroller && scroller.scrollTop <= 0) {
          pullScroller = scroller;
          pullStartX = touch.clientX;
          pullStartY = touch.clientY;
          pullDistance = 0;
          pullCancelled = false;
        }
      }
    };

    const onTouchMove = (event: TouchEvent) => {
      if (event.touches.length !== 1) {
        cancelPress();
        pullCancelled = true;
        edgeStartX = -1;
        return;
      }
      const touch = event.touches[0];

      if (
        pressTimer !== undefined &&
        Math.hypot(touch.clientX - pressStartX, touch.clientY - pressStartY) > MOVE_SLOP_PX
      ) {
        cancelPress();
      }

      if (edgeStartX >= 0) {
        edgeDx = touch.clientX - edgeStartX;
        edgeDy = touch.clientY - edgeStartY;
      }

      if (!pullCancelled && pullScroller) {
        const dy = touch.clientY - pullStartY;
        const dx = touch.clientX - pullStartX;
        if (dy < 0 || pullScroller.scrollTop > 0 || Math.abs(dx) > Math.abs(dy)) {
          pullCancelled = true;
          hidePull();
        } else if (dy > MOVE_SLOP_PX) {
          pullDistance = dy;
          showPull(dy);
        }
      }
    };

    const onTouchEnd = (event: TouchEvent) => {
      cancelPress();

      // The finger that opened a menu must not also tap whatever is under it.
      if (pressFired) {
        pressFired = false;
        event.preventDefault();
      }

      if (edgeStartX >= 0) {
        const forward = rtl() ? -edgeDx : edgeDx;
        if (forward > BACK_SWIPE_PX && Math.abs(edgeDy) < forward * 0.6) {
          useTabsStore.getState().go(-1);
        }
        edgeStartX = -1;
      }

      if (!pullCancelled) {
        pullCancelled = true;
        if (pullDistance >= PULL_TRIGGER_PX) {
          spinThenHide();
          for (const handler of Array.from(pullHandlers)) handler();
        } else {
          hidePull();
        }
      }
    };

    const onTouchCancel = () => {
      cancelPress();
      pressFired = false;
      edgeStartX = -1;
      if (!pullCancelled) hidePull();
      pullCancelled = true;
    };

    document.addEventListener("touchstart", onTouchStart, { passive: true });
    document.addEventListener("touchmove", onTouchMove, { passive: true });
    document.addEventListener("touchend", onTouchEnd, { passive: false });
    document.addEventListener("touchcancel", onTouchCancel, { passive: true });

    return () => {
      document.removeEventListener("touchstart", onTouchStart);
      document.removeEventListener("touchmove", onTouchMove);
      document.removeEventListener("touchend", onTouchEnd);
      document.removeEventListener("touchcancel", onTouchCancel);
      cancelPress();
      indicator.remove();
    };
  }, []);
}
