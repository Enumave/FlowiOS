import { useLayoutEffect, type RefObject } from "react";

/**
 * Android's "enter always" scroll behaviour, for a bar that rides at the top of a scroller: it
 * slides away as the page scrolls down and comes straight back on the first scroll up, however far
 * down the page is. The offset goes onto the element as a transform, so scrolling never re-renders.
 */
export function useEnterAlways(
  scroller: RefObject<HTMLElement | null> | null,
  target: RefObject<HTMLElement | null>,
  height: number,
  enabled = true,
) {
  useLayoutEffect(() => {
    const container = scroller?.current;
    const element = target.current;
    if (!enabled || !container || !element) return;
    let offset = 0;
    let last = container.scrollTop;
    const apply = () => {
      element.style.transform = offset === 0 ? "" : `translateY(${offset}px)`;
    };
    const onScroll = () => {
      const top = container.scrollTop;
      const delta = top - last;
      last = top;
      // Overscroll bounce reports negative tops; the bar stays put there.
      if (top <= 0) offset = 0;
      else offset = Math.min(0, Math.max(-height, offset - delta));
      apply();
    };
    container.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      container.removeEventListener("scroll", onScroll);
      element.style.transform = "";
    };
  }, [scroller, target, height, enabled]);
}
