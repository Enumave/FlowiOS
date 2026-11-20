import { MOTION_EASE, motionMs } from "./motion";
import type { FrameBox } from "./theaterGlide";

/*
  The player's vertical swipe, as a sheet that follows the finger. Android's expanded player is one
  box that morphs between the watch page, the floating mini player and fullscreen while it is
  dragged; this does the same to the global player frame. Dragging writes the in-between box
  straight onto the frame, and releasing either carries on to the target or springs back.

  Nothing here knows about React or the player store: the caller says where each direction leads
  and what to do when a drag is committed. That keeps the maths testable on its own.
*/

export type SheetAction = "minimize" | "enter-fullscreen" | "exit-fullscreen";

/** Where one direction of drag leads. `travel` is the finger distance that completes it. */
export interface SheetTarget {
  action: SheetAction;
  box: FrameBox;
  radius: number;
  travel: number;
}

export interface PlayerSheetOptions {
  frame: HTMLElement;
  /** The frame's box and corner radius before the drag. */
  origin: FrameBox;
  originRadius: number;
  /** Dragging down, and dragging up. A direction without a target does not move the frame. */
  down: SheetTarget | null;
  up: SheetTarget | null;
  /**
   * Applies the state change for a committed drag. It runs synchronously, before the settle
   * animation starts, so the frame already holds its final layout and the animation only covers
   * the trip there.
   */
  commit: (action: SheetAction) => void;
}

export interface PlayerSheet {
  /** `dy` is the finger's distance from where it first touched; `timeMs` is the event's timestamp. */
  update: (dy: number, timeMs: number) => void;
  /** The finger lifted: commit or spring back. */
  release: () => void;
  /** The touch was interrupted: spring back. */
  cancel: () => void;
  /** Put everything back at once, for when the gesture's owner goes away mid-drag. */
  abort: () => void;
}

// ---------------------------------------------------------------------------
// Maths
// ---------------------------------------------------------------------------

/** Past this share of its travel a released drag completes, however slowly it was dragged. */
export const COMMIT_PROGRESS = 0.35;
/** A flick faster than this (px per ms) completes a drag, or cancels it if it points back. */
export const FLICK_PX_PER_MS = 0.45;
/** A flick still has to have gone somewhere; a fast twitch at the start is not a swipe. */
const FLICK_MIN_PROGRESS = 0.04;
const MIN_SETTLE_MS = 140;
const MIN_SETTLE_SPEED = 0.6;
const VELOCITY_WINDOW_MS = 100;

export const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
export const clamp01 = (value: number) => clamp(value, 0, 1);
export const lerp = (from: number, to: number, t: number) => from + (to - from) * t;

export function lerpBox(from: FrameBox, to: FrameBox, t: number): FrameBox {
  return {
    top: lerp(from.top, to.top, t),
    left: lerp(from.left, to.left, t),
    width: lerp(from.width, to.width, t),
    height: lerp(from.height, to.height, t),
  };
}

export function dragProgress(distancePx: number, travelPx: number): number {
  return travelPx > 0 ? clamp01(Math.abs(distancePx) / travelPx) : 0;
}

/**
 * Whether a released drag completes. `velocity` is the finger's speed toward the target in px per
 * ms, negative when it is moving back.
 */
export function shouldCommit(progress: number, velocity: number): boolean {
  if (velocity >= FLICK_PX_PER_MS) return progress >= FLICK_MIN_PROGRESS;
  if (velocity <= -FLICK_PX_PER_MS) return false;
  return progress >= COMMIT_PROGRESS;
}

/**
 * How long the rest of the trip takes: the distance left at the speed of the release, but never
 * slower than a gentle settle nor longer than `maxMs` (the app's layout motion token). A `maxMs`
 * of zero means reduced motion, which skips the animation.
 */
export function settleDurationMs(distancePx: number, speedPxPerMs: number, maxMs: number): number {
  if (maxMs <= 0) return 0;
  const speed = Math.max(Math.abs(speedPxPerMs), MIN_SETTLE_SPEED);
  return clamp(distancePx / speed, Math.min(MIN_SETTLE_MS, maxMs), maxMs);
}

/** The finger's recent speed in px per ms, signed like the drag (positive is down). */
export function createVelocityTracker(windowMs = VELOCITY_WINDOW_MS) {
  const samples: { t: number; y: number }[] = [];
  return {
    push(t: number, y: number) {
      samples.push({ t, y });
      while (samples.length > 2 && t - samples[0]!.t > windowMs) samples.shift();
    },
    velocity(): number {
      const first = samples[0];
      const last = samples[samples.length - 1];
      if (!first || !last || last.t <= first.t) return 0;
      return (last.y - first.y) / (last.t - first.t);
    },
  };
}

// ---------------------------------------------------------------------------
// Frame
// ---------------------------------------------------------------------------

/** Above the top bar, the bottom bar and the drawer, for as long as the frame is in motion. */
const SHEET_Z_INDEX = "300";
export const SHEET_ATTR = "data-flow-sheet";
/** Asks the global player to collapse into the mini player and leave the watch page. */
export const MINIMIZE_REQUEST_EVENT = "flow-video-minimize-request";
/** Set on <body> while the frame settles, so the watch page's "playing in mini player" cover stays out of sight. */
export const SHEET_SETTLING_ATTR = "data-flow-sheet-settling";

const BOX_PROPS = ["transform", "width", "height", "borderRadius"] as const;
const HELD_PROPS = ["zIndex", "overflow"] as const;

const boxStyle = (box: FrameBox, radius: number) => ({
  transform: `translate3d(${box.left}px, ${box.top}px, 0)`,
  width: `${box.width}px`,
  height: `${box.height}px`,
  borderRadius: `${radius}px`,
});

export function startPlayerSheet(options: PlayerSheetOptions): PlayerSheet {
  const { frame, origin, originRadius, down, up, commit } = options;

  const saved = Object.fromEntries([...BOX_PROPS, ...HELD_PROPS].map((prop) => [prop, frame.style[prop]])) as Record<
    (typeof BOX_PROPS)[number] | (typeof HELD_PROPS)[number],
    string
  >;
  const restoreBox = () => BOX_PROPS.forEach((prop) => (frame.style[prop] = saved[prop]));
  const restoreHeld = () => HELD_PROPS.forEach((prop) => (frame.style[prop] = saved[prop]));

  frame.getAnimations?.().forEach((animation) => animation.cancel());
  frame.setAttribute(SHEET_ATTR, "drag");
  // The corners round while the frame shrinks, and the video must not spill over them.
  frame.style.overflow = "hidden";
  frame.style.zIndex = SHEET_Z_INDEX;

  const tracker = createVelocityTracker();
  let anchor: number | null = null;
  let target: SheetTarget | null = null;
  let progress = 0;
  let box = origin;
  let radius = originRadius;
  // A settle outlives the drag that started it, so only a drag still in progress can be taken back.
  let phase: "drag" | "settle" | "done" = "drag";

  const write = () => {
    const style = boxStyle(box, radius);
    BOX_PROPS.forEach((prop) => (frame.style[prop] = style[prop]));
  };

  const finish = () => {
    if (phase === "done") return;
    phase = "done";
    frame.removeAttribute(SHEET_ATTR);
    document.body.removeAttribute(SHEET_SETTLING_ATTR);
    restoreHeld();
  };

  /** Plays the rest of the trip. The frame must already hold the layout it ends in. */
  const settle = (from: { box: FrameBox; radius: number }, to: { box: FrameBox; radius: number }, ms: number) => {
    if (ms <= 0 || typeof frame.animate !== "function") {
      finish();
      return;
    }
    phase = "settle";
    frame.setAttribute(SHEET_ATTR, "settle");
    document.body.setAttribute(SHEET_SETTLING_ATTR, "");
    const animation = frame.animate([boxStyle(from.box, from.radius), boxStyle(to.box, to.radius)], {
      duration: ms,
      easing: MOTION_EASE,
    });
    animation.onfinish = finish;
    animation.oncancel = finish;
  };

  const releaseVelocity = () => {
    const speed = tracker.velocity();
    return target === down ? speed : -speed;
  };

  const springBack = () => {
    const speed = Math.abs(tracker.velocity());
    const travel = target?.travel ?? 0;
    const ms = settleDurationMs(progress * travel, speed, motionMs("--motion-layout"));
    const from = { box, radius };
    restoreBox();
    if (progress <= 0) {
      finish();
      return;
    }
    settle(from, { box: origin, radius: originRadius }, ms);
  };

  return {
    update(dyRaw, timeMs) {
      if (phase !== "drag") return;
      // The drag only starts counting once it is recognised, so the frame does not jump by the slop.
      anchor ??= dyRaw;
      const dy = dyRaw - anchor;
      tracker.push(timeMs, dy);
      target = dy > 0 ? down : dy < 0 ? up : null;
      if (target) {
        progress = dragProgress(dy, target.travel);
        box = lerpBox(origin, target.box, progress);
        radius = lerp(originRadius, target.radius, progress);
      } else {
        progress = 0;
        box = origin;
        radius = originRadius;
      }
      write();
    },

    release() {
      if (phase !== "drag") return;
      if (!target || !shouldCommit(progress, releaseVelocity())) {
        springBack();
        return;
      }
      const done = target;
      const speed = Math.abs(tracker.velocity());
      const ms = settleDurationMs((1 - progress) * done.travel, speed, motionMs("--motion-layout"));
      const from = { box, radius };
      restoreBox();
      commit(done.action);
      settle(from, { box: done.box, radius: done.radius }, ms);
    },

    cancel() {
      if (phase !== "drag") return;
      springBack();
    },

    abort() {
      // Once committed, the state has changed and the animation is the only thing left to play.
      if (phase !== "drag") return;
      restoreBox();
      finish();
    },
  };
}
