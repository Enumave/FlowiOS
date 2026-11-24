/*
  How Flow for Android's floating mini player moves, ported from DraggablePlayerDragMath.kt,
  DraggablePlayerGeometry.kt and DraggablePlayerMotionSpecs.kt.

  It does not rest wherever it is let go. It follows the finger (stretching a third as far past the
  screen's edge), and on release it settles into one of the four corners: a flick picks the corner
  outright, a slow drag has to cross 15% of the travel, and the position is projected 300 ms along the
  finger's speed first. Pulled well below its lowest resting place, or flicked down from a bottom
  corner, it closes. It rests above the bottom bar and below the top bar, 8 px from the edges.

  Everything here is pure except the two DOM reads and the settle animation at the bottom.
*/

export type MiniCorner = "topLeft" | "topRight" | "bottomLeft" | "bottomRight";

export interface MiniBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

// --- Android's constants (physical px per second for speeds) -----------------------------------
export const CORNER_FLING_VELOCITY = 400;
export const CORNER_FLING_AXIS_DOMINANCE = 0.8;
export const CORNER_SWITCH_TRAVEL_FRACTION = 0.15;
export const CORNER_VELOCITY_PROJECTION_S = 0.3;
/** Share of the finger's travel past a bound that the mini player still follows. */
export const RUBBER_BAND_FOLLOW = 0.35;
/** How far below its lowest resting place, in mini player heights, a release closes it. */
export const CLOSE_BELOW_HEIGHTS = 0.4;
export const CLOSE_FLING_VELOCITY = 1200;
export const CLOSE_AXIS_DOMINANCE = 2;
/** MiniPlayerMargin in DraggablePlayerLayout.kt. */
export const MINI_MARGIN = 8;

export const isLeft = (corner: MiniCorner) => corner === "topLeft" || corner === "bottomLeft";
export const isTop = (corner: MiniCorner) => corner === "topLeft" || corner === "topRight";

export function cornerFor(left: boolean, top: boolean): MiniCorner {
  if (left && top) return "topLeft";
  if (left) return "bottomLeft";
  if (top) return "topRight";
  return "bottomRight";
}

export const cornerTargetX = (corner: MiniCorner, minX: number, maxX: number) => (isLeft(corner) ? minX : maxX);
export const cornerTargetY = (corner: MiniCorner, minY: number, maxY: number) => (isTop(corner) ? minY : maxY);

/** Where the mini player sits for a finger at `raw`: on it inside the bounds, 35% of the way past them. */
export function rubberBand(raw: number, min: number, max: number): number {
  if (raw < min) return min - (min - raw) * RUBBER_BAND_FOLLOW;
  if (raw > max) return max + (raw - max) * RUBBER_BAND_FOLLOW;
  return raw;
}

/**
 * Picks the corner a released mini player settles into: a dominant fling wins outright, otherwise
 * the position projected 300 ms along the velocity has to cross 15% of the travel to switch.
 */
export function resolveMiniCorner(
  current: MiniCorner,
  currentX: number,
  currentY: number,
  bounds: MiniBounds,
  velocityX: number,
  velocityY: number,
): MiniCorner {
  const originX = cornerTargetX(current, bounds.minX, bounds.maxX);
  const originY = cornerTargetY(current, bounds.minY, bounds.maxY);
  const switchX = Math.max(bounds.maxX - bounds.minX, 1) * CORNER_SWITCH_TRAVEL_FRACTION;
  const switchY = Math.max(bounds.maxY - bounds.minY, 1) * CORNER_SWITCH_TRAVEL_FRACTION;
  const projectedX = currentX - originX + velocityX * CORNER_VELOCITY_PROJECTION_S;
  const projectedY = currentY - originY + velocityY * CORNER_VELOCITY_PROJECTION_S;
  const wasLeft = isLeft(current);
  const wasTop = isTop(current);

  let goLeft = wasLeft;
  if (Math.abs(velocityX) > CORNER_FLING_VELOCITY && Math.abs(velocityX) > Math.abs(velocityY) * CORNER_FLING_AXIS_DOMINANCE) {
    goLeft = velocityX < 0;
  } else if (wasLeft && projectedX > switchX) {
    goLeft = false;
  } else if (!wasLeft && projectedX < -switchX) {
    goLeft = true;
  }

  let goTop = wasTop;
  if (Math.abs(velocityY) > CORNER_FLING_VELOCITY && Math.abs(velocityY) > Math.abs(velocityX) * CORNER_FLING_AXIS_DOMINANCE) {
    goTop = velocityY < 0;
  } else if (wasTop && projectedY > switchY) {
    goTop = false;
  } else if (!wasTop && projectedY < -switchY) {
    goTop = true;
  }
  return cornerFor(goLeft, goTop);
}

/**
 * Whether a released mini player closes by leaving through the bottom: the finger took it well past
 * its lowest resting place, or flicked it down from a bottom corner. A flick down from a top corner
 * only moves it to the bottom corner.
 */
export function shouldCloseMiniDownward(
  fingerY: number,
  maxY: number,
  miniHeight: number,
  startedAtBottom: boolean,
  velocityX: number,
  velocityY: number,
): boolean {
  return (
    fingerY - maxY > miniHeight * CLOSE_BELOW_HEIGHTS ||
    (startedAtBottom && velocityY > CLOSE_FLING_VELOCITY && velocityY > Math.abs(velocityX) * CLOSE_AXIS_DOMINANCE)
  );
}

export type MiniRelease = { kind: "close" } | { kind: "corner"; corner: MiniCorner; x: number; y: number };

export function decideMiniRelease(input: {
  finger: { x: number; y: number };
  current: { x: number; y: number };
  startCorner: MiniCorner;
  bounds: MiniBounds;
  miniHeight: number;
  /** Physical px per second, as Android measures it. */
  velocity: { x: number; y: number };
}): MiniRelease {
  const { finger, current, startCorner, bounds, miniHeight, velocity } = input;
  if (shouldCloseMiniDownward(finger.y, bounds.maxY, miniHeight, !isTop(startCorner), velocity.x, velocity.y)) {
    return { kind: "close" };
  }
  const corner = resolveMiniCorner(startCorner, current.x, current.y, bounds, velocity.x, velocity.y);
  return { kind: "corner", corner, x: cornerTargetX(corner, bounds.minX, bounds.maxX), y: cornerTargetY(corner, bounds.minY, bounds.maxY) };
}

// --- Saved position: the port stores ratios, a corner is 0 or 1 on each axis -------------------

export function cornerOfRatios(ratios: { xRatio: number; yRatio: number }): MiniCorner {
  return cornerFor(ratios.xRatio < 0.5, ratios.yRatio < 0.5);
}

export function ratiosOfCorner(corner: MiniCorner): { xRatio: number; yRatio: number } {
  return { xRatio: isLeft(corner) ? 0 : 1, yRatio: isTop(corner) ? 0 : 1 };
}

/** A position saved by the free-drag mini player becomes the corner nearest it. */
export function snapToCorner(ratios: { xRatio: number; yRatio: number }): { xRatio: number; yRatio: number } {
  return ratiosOfCorner(cornerOfRatios(ratios));
}

// --- Where it may rest -------------------------------------------------------------------------

/** The top bar's height, which the mini player never covers. */
export const TOP_BAR_PX = 56;
/** The bottom bar's height, which it rests above. */
export const BOTTOM_BAR_PX = 64;

let probe: HTMLDivElement | null = null;

function safeInset(side: "top" | "bottom"): number {
  if (typeof document === "undefined") return 0;
  if (!probe || !probe.isConnected) {
    probe = document.createElement("div");
    probe.style.cssText =
      "position:fixed;visibility:hidden;pointer-events:none;left:0;top:0;width:0;" +
      "padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)";
    document.body.appendChild(probe);
  }
  const style = getComputedStyle(probe);
  return Number.parseFloat(side === "top" ? style.paddingTop : style.paddingBottom) || 0;
}

/**
 * The corners' bounds for a mini player of `playerWidth` x `playerHeight`: 8 px from the sides, below
 * the status bar and top bar, above the home indicator and, where the layout has one, the bottom bar
 * (whether or not the page it lands on is showing it yet: a video minimized from the Watch page
 * goes to a page that has).
 */
export function adaptiveMiniBounds(viewportWidth: number, viewportHeight: number, playerWidth: number, playerHeight: number): MiniBounds {
  const barBelow = typeof document !== "undefined" && document.documentElement.dataset.navigation === "bar";
  const minX = MINI_MARGIN;
  const maxX = Math.max(minX, viewportWidth - playerWidth - MINI_MARGIN);
  const minY = safeInset("top") + TOP_BAR_PX + MINI_MARGIN;
  const bottomPad = safeInset("bottom") + (barBelow ? BOTTOM_BAR_PX : 0);
  const maxY = Math.max(minY, viewportHeight - playerHeight - bottomPad - MINI_MARGIN);
  return { minX, maxX, minY, maxY };
}

// --- Finger tracking ---------------------------------------------------------------------------

const VELOCITY_WINDOW_MS = 100;

/** Follows the finger so its speed can be read at the moment it lifts. */
export function createMiniDragTracker() {
  let samples: { t: number; x: number; y: number }[] = [];
  return {
    reset() {
      samples = [];
    },
    push(t: number, x: number, y: number) {
      samples.push({ t, x, y });
      while (samples.length > 2 && t - samples[0]!.t > VELOCITY_WINDOW_MS * 2) samples.shift();
    },
    get finger(): { x: number; y: number } | null {
      const last = samples[samples.length - 1];
      return last ? { x: last.x, y: last.y } : null;
    },
    /** CSS px per second over the last 100 ms before `now`; zero if the finger had stopped. */
    velocity(now: number): { x: number; y: number } {
      const recent = samples.filter((sample) => now - sample.t <= VELOCITY_WINDOW_MS);
      const first = recent[0];
      const last = recent[recent.length - 1];
      if (!first || !last || last.t <= first.t) return { x: 0, y: 0 };
      const seconds = (last.t - first.t) / 1000;
      return { x: (last.x - first.x) / seconds, y: (last.y - first.y) / seconds };
    },
  };
}

// --- Settling ----------------------------------------------------------------------------------

export interface Spring {
  omega: number;
  zeta: number;
}
/** miniSnapSpringSpec: damping 0.82, stiffness 500. */
export const SPRING_MINI_SNAP: Spring = { omega: Math.sqrt(500), zeta: 0.82 };
/** miniDismissSpringSpec: damping 0.9, stiffness 340. */
export const SPRING_MINI_DISMISS: Spring = { omega: Math.sqrt(340), zeta: 0.9 };

/** How far a spring is from its goal `t` seconds after it was let go `e0` away at `v0` per second. */
export function springOffset(t: number, e0: number, v0: number, { omega, zeta }: Spring): number {
  if (zeta >= 1) return (e0 + (v0 + omega * e0) * t) * Math.exp(-omega * t);
  const damped = omega * Math.sqrt(1 - zeta * zeta);
  return Math.exp(-zeta * omega * t) * (e0 * Math.cos(damped * t) + ((v0 + zeta * omega * e0) / damped) * Math.sin(damped * t));
}

/** One position per frame along a trip from 0 to 1, thrown at `rate` trips a second. Ends on 1. */
export function springFrames(rate: number, spring: Spring): { durationMs: number; values: number[] } {
  const e0 = -1;
  const v0 = Math.max(-7, Math.min(7, rate));
  let lastMoving = -1;
  for (let ms = 0; ms <= 900; ms += 4) {
    if (Math.abs(springOffset(ms / 1000, e0, v0, spring)) > 0.0015) lastMoving = ms;
  }
  if (lastMoving < 0) return { durationMs: 0, values: [1] };
  const durationMs = Math.min(900, lastMoving + 16);
  const steps = Math.ceil(durationMs / 16);
  const values: number[] = [];
  for (let step = 0; step < steps; step += 1) values.push(1 + springOffset((step * durationMs) / steps / 1000, e0, v0, spring));
  values.push(1);
  return { durationMs, values };
}

export interface MiniSettleInput {
  frame: HTMLElement;
  from: { x: number; y: number };
  bounds: MiniBounds;
  miniHeight: number;
  viewportHeight: number;
  release: MiniRelease;
  /** CSS px per second at release. */
  velocity: { x: number; y: number };
  /** Called with the resting place once the frame has arrived (corner) or left (close). */
  onDone: (release: MiniRelease) => void;
}

/** Plays the settle: a spring into the corner, or a drop off the bottom of the screen. */
export function settleMiniPlayer(input: MiniSettleInput) {
  const { frame, from, release, velocity, onDone, viewportHeight } = input;
  const to =
    release.kind === "close"
      ? { x: from.x, y: viewportHeight + MINI_MARGIN }
      : { x: release.x, y: release.y };
  const spring = release.kind === "close" ? SPRING_MINI_DISMISS : SPRING_MINI_SNAP;
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const distance = Math.hypot(dx, dy);
  const place = (x: number, y: number) => `translate3d(${x}px, ${y}px, 0)`;
  // The speed along the trip, as trips per second.
  const along = distance > 0 ? (velocity.x * dx + velocity.y * dy) / (distance * distance) : 0;
  const { durationMs, values } = springFrames(along, spring);
  const finish = () => {
    frame.style.transform = place(to.x, to.y);
    onDone(release);
  };
  if (distance < 0.5 || durationMs <= 0 || typeof frame.animate !== "function") {
    finish();
    return;
  }
  const animation = frame.animate(
    values.map((t) => ({ transform: place(from.x + dx * t, from.y + dy * t) })),
    { duration: durationMs, easing: "linear" },
  );
  animation.onfinish = finish;
  animation.oncancel = finish;
}
