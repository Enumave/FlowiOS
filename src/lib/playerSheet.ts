import { motionMs } from "./motion";
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

// ---------------------------------------------------------------------------
// Spring
// ---------------------------------------------------------------------------

/**
 * A damped spring, which is how a released player settles on Android and in YouTube. `omega` is its
 * stiffness in rad/s and `zeta` its damping: below 1 it overshoots and rocks back, at 1 it just
 * arrives. The motion is measured along the whole trip (0 is where the drag began, 1 its target),
 * so a bounce is as big as the swipe was long, not as big as what was left of it.
 */
export interface Spring {
  omega: number;
  zeta: number;
}

/** Growing to fullscreen: lively, with a small overshoot that the screen's edge crops. */
export const SPRING_EXPAND: Spring = { omega: 20, zeta: 0.62 };
/** Shrinking to the mini player or the page: barely overshoots, it must not run off the screen. */
export const SPRING_COLLAPSE: Spring = { omega: 19, zeta: 0.75 };
/** A swipe that did not go through springs back with a visible wobble. */
export const SPRING_RETURN: Spring = { omega: 21, zeta: 0.55 };

/** Fastest the spring is thrown at, in trips per second, so a wild flick cannot fling the frame. */
const MAX_RATE = 7;
/** The spring is at rest once it is this close to its goal (a fraction of the trip, under a pixel). */
const REST_DISTANCE = 0.0015;
const MAX_SPRING_MS = 900;
const FRAME_MS = 16;

/**
 * How far the spring is from its goal `t` seconds after it was let go, starting `e0` away and moving
 * at `v0` per second. A `zeta` of 1 or more is treated as critically damped.
 */
export function springOffset(t: number, e0: number, v0: number, { omega, zeta }: Spring): number {
  if (zeta >= 1) return (e0 + (v0 + omega * e0) * t) * Math.exp(-omega * t);
  const damped = omega * Math.sqrt(1 - zeta * zeta);
  return (
    Math.exp(-zeta * omega * t) *
    (e0 * Math.cos(damped * t) + ((v0 + zeta * omega * e0) / damped) * Math.sin(damped * t))
  );
}

/**
 * The positions to play, one per frame, from `from` to `goal` (both along the trip) with the
 * release's `rate` in trips per second. Ends exactly on `goal`. Zero duration means nothing to play.
 */
export function springFrames(
  from: number,
  goal: number,
  rate: number,
  spring: Spring,
): { durationMs: number; values: number[] } {
  const e0 = from - goal;
  const v0 = clamp(rate, -MAX_RATE, MAX_RATE);
  let lastMovingMs = -1;
  for (let ms = 0; ms <= MAX_SPRING_MS; ms += 4) {
    if (Math.abs(springOffset(ms / 1000, e0, v0, spring)) > REST_DISTANCE) lastMovingMs = ms;
  }
  if (lastMovingMs < 0) return { durationMs: 0, values: [goal] };
  const durationMs = Math.min(MAX_SPRING_MS, lastMovingMs + FRAME_MS);
  const steps = Math.ceil(durationMs / FRAME_MS);
  const values: number[] = [];
  for (let step = 0; step < steps; step += 1) {
    values.push(goal + springOffset((step * durationMs) / steps / 1000, e0, v0, spring));
  }
  values.push(goal);
  return { durationMs, values };
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

  /**
   * Plays the rest of the trip as a spring toward `goal` (1 is the target, 0 is where the drag
   * began). The frame must already hold the layout it ends in.
   */
  const settle = (to: SheetTarget, goal: 0 | 1, rate: number, spring: Spring) => {
    const { durationMs, values } = springFrames(progress, goal, rate, spring);
    if (motionMs("--motion-layout") <= 0 || durationMs <= 0 || typeof frame.animate !== "function") {
      finish();
      return;
    }
    phase = "settle";
    frame.setAttribute(SHEET_ATTR, "settle");
    document.body.setAttribute(SHEET_SETTLING_ATTR, "");
    const keyframes = values.map((y) => {
      const at = lerpBox(origin, to.box, y);
      // A spring can swing past either end, but a box cannot be smaller than nothing.
      const sized = { ...at, width: Math.max(0, at.width), height: Math.max(0, at.height) };
      return boxStyle(sized, Math.max(0, lerp(originRadius, to.radius, y)));
    });
    const animation = frame.animate(keyframes, { duration: durationMs, easing: "linear" });
    animation.onfinish = finish;
    animation.oncancel = finish;
  };

  /** Finger speed toward the target in px per ms, negative when it is moving back. */
  const releaseVelocity = () => {
    const speed = tracker.velocity();
    return target === down ? speed : -speed;
  };

  /** The same speed as trips per second, which is what the spring is thrown with. */
  const releaseRate = (to: SheetTarget) => (releaseVelocity() * 1000) / to.travel;

  const springBack = () => {
    const to = target;
    restoreBox();
    if (!to || progress <= 0) {
      finish();
      return;
    }
    settle(to, 0, releaseRate(to), SPRING_RETURN);
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
      const rate = releaseRate(done);
      restoreBox();
      commit(done.action);
      settle(done, 1, rate, done.action === "enter-fullscreen" ? SPRING_EXPAND : SPRING_COLLAPSE);
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
