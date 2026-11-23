import { useEffect, useRef, type RefObject } from "react";
import { usePlayerStore } from "../../../store/usePlayerStore";
import { MINIMIZE_REQUEST_EVENT, SHEET_ATTR, startPlayerSheet, type PlayerSheet, type SheetAction } from "../../../lib/playerSheet";
import { planPlayerSheet } from "../../../lib/playerSheetTargets";
import { beginScreenLevels, endScreenLevels, setScreenBrightness, setSystemVolume } from "../../../lib/screenLevels";

/** One full-width sideways drag moves the video this far, as on Android. */
const SCRUB_SPAN_SECONDS = 90;
/** A touch must move this far before it stops being a tap. */
const SLOP_PX = 12;
/**
 * A vertical drag this long enters or leaves fullscreen when there is no player frame to animate.
 * Otherwise the drag moves the frame itself (see lib/playerSheet.ts) and releasing decides.
 */
const FULLSCREEN_DRAG_PX = 80;
const ZOOM_MIN = 1;
const ZOOM_MAX = 6;
const ZOOM_OVERSHOOT_MIN = 0.7;
const ZOOM_OVERSHOOT_MAX = 8;
/** Releasing below this scale settles all the way back to unzoomed. */
const ZOOM_RESET_THRESHOLD = 1.02;

/**
 * In fullscreen a vertical drag on the left half moves the screen brightness and one on the right
 * half the system volume, as on Android; the middle third still pulls the player out of fullscreen.
 * A full-height drag moves the level by this much (Android's VERTICAL_DRAG_SENSITIVITY).
 */
const LEVEL_SENSITIVITY = 1.5;
/** Drags that start this close to the top or bottom edge belong to the system. */
const EDGE_TOP_BOTTOM_PX = 40;
/** Drags that start this close to a side edge belong to the system's back swipe. */
const EDGE_SIDE_PX = 24;
/** The middle zone, as a share of the width (Android: 33% to 67%). */
const CENTER_ZONE_START = 0.33;
const CENTER_ZONE_END = 0.67;
/** How long the level read-out stays after the finger lifts. */
const LEVEL_LINGER_MS = 700;

export type ScrubPreview = { target: number; delta: number } | null;
export type LevelKind = "brightness" | "volume";
export type LevelPreview = { kind: LevelKind; value: number } | null;

type Options = {
  enabled: boolean;
  layerRef: RefObject<HTMLDivElement | null>;
  videoRef: RefObject<HTMLVideoElement | null>;
  seekBy: (delta: number) => void;
  toggleFullscreen: () => void;
  /** Collapses the watch page into the mini player. Without it a request goes to the global player. */
  minimize?: () => void;
  /** Called when a touch turns into a gesture, so a pending hold-to-speed-up is dropped. */
  onGestureStart: () => void;
  onScrub: (preview: ScrubPreview) => void;
  /** The brightness or volume read-out while a side swipe is under way; null when it should go. */
  onLevel?: (level: LevelPreview) => void;
  /** Changing this (a new video) puts the zoom back. */
  resetKey?: string | null;
};

type Point = { x: number; y: number };
type Mode = "idle" | "pending" | "scrub" | "vertical" | "level" | "pan" | "pinch" | "done";

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

/**
 * Touch gestures for the video, matching Flow for Android:
 * a sideways drag scrubs, a vertical drag moves the player between the watch page, the mini
 * player and fullscreen with the frame following the finger (in fullscreen the left and right
 * halves change brightness and volume instead, and only the middle leaves fullscreen), and two
 * fingers pinch to zoom and pan.
 * Taps, double taps and hold-to-speed-up stay with the overlay.
 */
export function useTouchPlayerGestures(options: Options) {
  const latest = useRef(options);
  latest.current = options;
  const { enabled, resetKey } = options;

  useEffect(() => {
    const layer = latest.current.layerRef.current;
    if (!enabled || !layer) return;

    layer.style.touchAction = "none";

    const pointers = new Map<number, Point>();
    let mode: Mode = "idle";
    let start: Point = { x: 0, y: 0 };
    let baseTime = 0;
    let lastPreview: ScrubPreview = null;
    let swallowClick = false;
    let sheet: PlayerSheet | null = null;

    let levelKind: LevelKind | null = null;
    /** Null until the native side has said where the level stands. */
    let levelValue: number | null = null;
    let levelPendingDelta = 0;
    let levelLastY = 0;
    let levelSent = -1;
    let levelFrame = 0;
    let levelHideTimer: number | undefined;
    let levelSession = 0;

    let scale = 1;
    let offsetX = 0;
    let offsetY = 0;
    let pinchStartDistance = 1;
    let pinchStartScale = 1;
    let pinchStartMid: Point = { x: 0, y: 0 };
    let pinchStartOffset: Point = { x: 0, y: 0 };
    let panStart: Point = { x: 0, y: 0 };
    let panStartOffset: Point = { x: 0, y: 0 };

    const video = () => latest.current.videoRef.current;

    const applyTransform = () => {
      const element = video();
      if (!element) return;
      if (scale === 1 && offsetX === 0 && offsetY === 0) {
        element.style.transform = "";
        element.style.transformOrigin = "";
        return;
      }
      element.style.transformOrigin = "center center";
      element.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
    };

    const clampOffsets = () => {
      const rect = layer.getBoundingClientRect();
      const limitX = Math.max(0, ((scale - 1) * rect.width) / 2);
      const limitY = Math.max(0, ((scale - 1) * rect.height) / 2);
      offsetX = clamp(offsetX, -limitX, limitX);
      offsetY = clamp(offsetY, -limitY, limitY);
    };

    const resetZoom = () => {
      scale = 1;
      offsetX = 0;
      offsetY = 0;
      applyTransform();
    };

    const settleZoom = () => {
      if (scale < ZOOM_RESET_THRESHOLD) {
        resetZoom();
        return;
      }
      scale = clamp(scale, ZOOM_MIN, ZOOM_MAX);
      clampOffsets();
      applyTransform();
    };

    const distanceBetween = () => {
      const [a, b] = Array.from(pointers.values());
      return Math.max(1, Math.hypot(a.x - b.x, a.y - b.y));
    };

    const midpoint = (): Point => {
      const [a, b] = Array.from(pointers.values());
      return { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    };

    /** Where a touch landed on the video: a side half, the middle third, or too close to an edge. */
    const zoneAt = (point: Point): "left" | "center" | "right" | "edge" => {
      const rect = layer.getBoundingClientRect();
      const x = point.x - rect.left;
      const y = point.y - rect.top;
      if (
        y < EDGE_TOP_BOTTOM_PX ||
        rect.height - y < EDGE_TOP_BOTTOM_PX ||
        x < EDGE_SIDE_PX ||
        rect.width - x < EDGE_SIDE_PX
      ) {
        return "edge";
      }
      if (x > rect.width * CENTER_ZONE_START && x < rect.width * CENTER_ZONE_END) return "center";
      return x < rect.width / 2 ? "left" : "right";
    };

    const sendLevel = () => {
      if (levelKind === null || levelValue === null) return;
      if (levelSent >= 0 && Math.abs(levelValue - levelSent) < 0.002) return;
      levelSent = levelValue;
      if (levelKind === "brightness") setScreenBrightness(levelValue);
      else setSystemVolume(levelValue);
    };

    const publishLevel = () => {
      if (levelKind === null || levelValue === null) return;
      latest.current.onLevel?.({ kind: levelKind, value: levelValue });
      // Native calls are batched to one per frame; the read-out above follows every move.
      if (!levelFrame) {
        levelFrame = requestAnimationFrame(() => {
          levelFrame = 0;
          sendLevel();
        });
      }
    };

    const moveLevel = (y: number) => {
      const height = Math.max(1, layer.getBoundingClientRect().height);
      const delta = (-(y - levelLastY) / height) * LEVEL_SENSITIVITY;
      levelLastY = y;
      if (levelValue === null) {
        levelPendingDelta += delta;
        return;
      }
      // Accumulated and clamped step by step, so dragging past an end and back responds at once.
      levelValue = clamp(levelValue + delta, 0, 1);
      publishLevel();
    };

    const beginLevel = (kind: LevelKind, y: number) => {
      begin("level");
      window.clearTimeout(levelHideTimer);
      levelKind = kind;
      levelValue = null;
      levelPendingDelta = 0;
      levelLastY = y;
      levelSent = -1;
      const session = ++levelSession;
      void (async () => {
        let levels = await beginScreenLevels(kind === "volume");
        // The first time, iOS can take a moment to produce the volume slider.
        for (let attempt = 0; attempt < 2 && levels && kind === "volume" && levels.volume === null; attempt++) {
          await new Promise((resolve) => window.setTimeout(resolve, 90));
          if (session !== levelSession) return;
          levels = await beginScreenLevels(true);
        }
        if (session !== levelSession || levelKind !== kind) return;
        const base = kind === "brightness" ? levels?.brightness : levels?.volume;
        if (base === null || base === undefined) {
          // Nothing to move (not iOS, or the native side did not answer): drop the gesture quietly.
          levelKind = null;
          mode = "done";
          latest.current.onLevel?.(null);
          endScreenLevels();
          return;
        }
        levelValue = clamp(base + levelPendingDelta, 0, 1);
        publishLevel();
      })();
    };

    const endLevel = () => {
      if (levelKind === null) return;
      sendLevel();
      if (levelFrame) {
        cancelAnimationFrame(levelFrame);
        levelFrame = 0;
      }
      levelKind = null;
      levelValue = null;
      // The read-out lingers a moment, and the volume view stays until it goes.
      window.clearTimeout(levelHideTimer);
      levelHideTimer = window.setTimeout(() => {
        latest.current.onLevel?.(null);
        endScreenLevels();
      }, LEVEL_LINGER_MS);
    };

    const begin = (next: Mode) => {
      mode = next;
      swallowClick = true;
      latest.current.onGestureStart();
    };

    const commitSheet = (action: SheetAction) => {
      if (action === "minimize") {
        const minimize = latest.current.minimize;
        if (minimize) minimize();
        else window.dispatchEvent(new Event(MINIMIZE_REQUEST_EVENT));
      } else {
        latest.current.toggleFullscreen();
      }
    };

    /** The player frame follows the finger; null where there is no frame to move. */
    const startSheet = (frame: HTMLElement | null): PlayerSheet | null => {
      if (!frame) return null;
      const plan = planPlayerSheet(frame);
      return plan ? startPlayerSheet({ frame, ...plan, commit: commitSheet }) : null;
    };

    const onDown = (event: PointerEvent) => {
      if (event.pointerType !== "touch") return;
      if (pointers.size === 0) {
        mode = "idle";
        swallowClick = false;
        lastPreview = null;
      }
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
      try {
        layer.setPointerCapture(event.pointerId);
      } catch {
        // A pointer that already ended cannot be captured; the gesture just does not start.
      }

      if (pointers.size === 1) {
        start = { x: event.clientX, y: event.clientY };
        baseTime = video()?.currentTime ?? 0;
        mode = "pending";
      } else if (pointers.size === 2) {
        sheet?.cancel();
        sheet = null;
        endLevel();
        begin("pinch");
        latest.current.onScrub(null);
        pinchStartDistance = distanceBetween();
        pinchStartScale = scale;
        pinchStartMid = midpoint();
        pinchStartOffset = { x: offsetX, y: offsetY };
      }
    };

    const onMove = (event: PointerEvent) => {
      if (!pointers.has(event.pointerId)) return;
      pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });

      if (mode === "pinch" && pointers.size >= 2) {
        const ratio = distanceBetween() / pinchStartDistance;
        scale = clamp(pinchStartScale * ratio, ZOOM_OVERSHOOT_MIN, ZOOM_OVERSHOOT_MAX);
        const mid = midpoint();
        offsetX = pinchStartOffset.x + (mid.x - pinchStartMid.x);
        offsetY = pinchStartOffset.y + (mid.y - pinchStartMid.y);
        if (scale <= 1) {
          offsetX = 0;
          offsetY = 0;
        } else {
          clampOffsets();
        }
        applyTransform();
        return;
      }

      if (pointers.size !== 1) return;
      const dx = event.clientX - start.x;
      const dy = event.clientY - start.y;

      if (mode === "pending") {
        if (Math.hypot(dx, dy) < SLOP_PX) return;
        if (scale > ZOOM_RESET_THRESHOLD) {
          begin("pan");
          panStart = { x: event.clientX, y: event.clientY };
          panStartOffset = { x: offsetX, y: offsetY };
        } else if (Math.abs(dx) > Math.abs(dy) * 1.3) {
          const element = video();
          if (!element || !Number.isFinite(element.duration) || element.duration <= 0) {
            mode = "done";
            return;
          }
          begin("scrub");
        } else if (Math.abs(dy) > Math.abs(dx) * 1.3) {
          // In fullscreen the zone the touch started in decides what a vertical drag does.
          const zone = usePlayerStore.getState().isVideoFullscreen ? zoneAt(start) : null;
          if (zone === "edge") {
            // Left to the system (back swipe, Control Center, the home indicator).
            begin("done");
            return;
          }
          if (zone === "left" || zone === "right") {
            beginLevel(zone === "left" ? "brightness" : "volume", event.clientY);
          } else {
            const frame = layer.closest<HTMLElement>("[data-flow-player-frame]");
            begin("vertical");
            // The last swipe is still settling: let it finish rather than fight it.
            if (frame?.hasAttribute(SHEET_ATTR)) {
              mode = "done";
              return;
            }
            sheet = startSheet(frame);
          }
        } else {
          return;
        }
      }

      if (mode === "scrub") {
        const element = video();
        if (!element) return;
        const width = Math.max(1, layer.getBoundingClientRect().width);
        const target = clamp(baseTime + (dx / width) * SCRUB_SPAN_SECONDS, 0, element.duration);
        lastPreview = { target, delta: target - baseTime };
        latest.current.onScrub(lastPreview);
      } else if (mode === "vertical") {
        sheet?.update(dy, event.timeStamp);
      } else if (mode === "level") {
        moveLevel(event.clientY);
      } else if (mode === "pan") {
        offsetX = panStartOffset.x + (event.clientX - panStart.x);
        offsetY = panStartOffset.y + (event.clientY - panStart.y);
        clampOffsets();
        applyTransform();
      }
    };

    const finish = (event: PointerEvent, cancelled: boolean) => {
      if (!pointers.has(event.pointerId)) return;
      const end = pointers.get(event.pointerId) ?? start;
      pointers.delete(event.pointerId);

      if (mode === "pinch") {
        if (pointers.size < 2) {
          settleZoom();
          mode = "done";
        }
      } else if (mode === "scrub") {
        latest.current.onScrub(null);
        if (!cancelled && lastPreview) latest.current.seekBy(lastPreview.delta);
        lastPreview = null;
        mode = "done";
      } else if (mode === "vertical") {
        if (sheet) {
          if (cancelled) sheet.cancel();
          else sheet.release();
          sheet = null;
        } else if (!cancelled) {
          const dy = end.y - start.y;
          const inFullscreen = usePlayerStore.getState().isVideoFullscreen;
          if (inFullscreen && dy > FULLSCREEN_DRAG_PX) latest.current.toggleFullscreen();
          else if (!inFullscreen && dy < -FULLSCREEN_DRAG_PX) latest.current.toggleFullscreen();
        }
        mode = "done";
      } else if (mode === "level") {
        endLevel();
        mode = "done";
      } else if (mode === "pan") {
        settleZoom();
        mode = "done";
      }

      if (pointers.size === 0) mode = "idle";
    };

    const onUp = (event: PointerEvent) => finish(event, false);
    const onCancel = (event: PointerEvent) => finish(event, true);

    // A drag must not also toggle play or seek by a double tap once the finger lifts.
    const onClickCapture = (event: Event) => {
      if (!swallowClick) return;
      swallowClick = false;
      event.stopImmediatePropagation();
      event.preventDefault();
    };

    layer.addEventListener("pointerdown", onDown);
    layer.addEventListener("pointermove", onMove);
    layer.addEventListener("pointerup", onUp);
    layer.addEventListener("pointercancel", onCancel);
    layer.addEventListener("click", onClickCapture, true);
    layer.addEventListener("dblclick", onClickCapture, true);

    return () => {
      layer.removeEventListener("pointerdown", onDown);
      layer.removeEventListener("pointermove", onMove);
      layer.removeEventListener("pointerup", onUp);
      layer.removeEventListener("pointercancel", onCancel);
      layer.removeEventListener("click", onClickCapture, true);
      layer.removeEventListener("dblclick", onClickCapture, true);
      layer.style.touchAction = "";
      // A drag cut off by this teardown goes back; a committed one is left to finish its animation.
      sheet?.abort();
      sheet = null;
      endLevel();
      window.clearTimeout(levelHideTimer);
      levelSession++;
      latest.current.onLevel?.(null);
      endScreenLevels();
      latest.current.onScrub(null);
      resetZoom();
    };
  }, [enabled, resetKey]);
}
