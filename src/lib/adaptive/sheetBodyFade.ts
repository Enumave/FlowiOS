/*
  While Android's player sheet is dragged down into the mini player, the page under the video fades
  out and slides down: it is fully transparent a third of the way through the collapse and has
  moved 80 px by the end (BODY_CONTENT_MAX_EXPAND_FRACTION, BODY_SLIDE_PX in
  DraggablePlayerMotionSpecs.kt). The page and the video are separate layers there too, so the
  video keeps its own box while the page ghosts away.

  Here the global player frame moves on its own (playerSheet.ts), and this does the page's half. It
  works on whatever carries `data-flow-watch-body`, and does nothing where nothing does.
*/

/** The drag progress at which the page is fully transparent. */
export const BODY_FADE_END = 0.3;
/** How far the page slides down over a full collapse, in px. */
export const BODY_SLIDE_PX = 80;

export const BODY_SELECTOR = "[data-flow-watch-body]";

const clamp01 = (value: number) => Math.min(1, Math.max(0, value));

/** The page's opacity and downward shift when the sheet is `fraction` of the way collapsed. */
export function bodyFadeFor(fraction: number): { opacity: number; shift: number } {
  const f = clamp01(fraction);
  return { opacity: clamp01(1 - f / BODY_FADE_END), shift: f * BODY_SLIDE_PX };
}

function body(): HTMLElement | null {
  return typeof document === "undefined" ? null : document.querySelector<HTMLElement>(BODY_SELECTOR);
}

const frameOf = (fraction: number) => {
  const { opacity, shift } = bodyFadeFor(fraction);
  return { opacity: String(opacity), transform: `translate3d(0, ${shift}px, 0)` };
};

/** Follows the finger: the page at `fraction`. */
export function applySheetBodyFade(fraction: number) {
  const element = body();
  if (!element) return;
  const style = frameOf(fraction);
  element.style.opacity = style.opacity;
  element.style.transform = style.transform;
  element.style.willChange = "opacity, transform";
}

/** Plays the page along the same trip the frame's spring takes, one value per frame. */
export function animateSheetBodyFade(fractions: number[], durationMs: number) {
  const element = body();
  if (!element || typeof element.animate !== "function" || fractions.length === 0) return;
  element.animate(fractions.map(frameOf), { duration: durationMs, easing: "linear", fill: "forwards" });
}

/** Puts the page back as it was, at once. */
export function clearSheetBodyFade() {
  const element = body();
  if (!element) return;
  element.getAnimations?.().forEach((animation) => animation.cancel());
  element.style.opacity = "";
  element.style.transform = "";
  element.style.willChange = "";
}
