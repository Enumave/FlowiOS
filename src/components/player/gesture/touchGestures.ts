import { useEffect, useRef, type RefObject } from "react";
import { usePlayerStore } from "../../../store/usePlayerStore";

/** One full-width sideways drag moves the video this far, as on Android. */
const SCRUB_SPAN_SECONDS = 90;
/** A touch must move this far before it stops being a tap. */
const SLOP_PX = 12;
/** A vertical drag this long enters or leaves fullscreen. */
const FULLSCREEN_DRAG_PX = 80;
const ZOOM_MIN = 1;
const ZOOM_MAX = 6;
const ZOOM_OVERSHOOT_MIN = 0.7;
const ZOOM_OVERSHOOT_MAX = 8;
/** Releasing below this scale settles all the way back to unzoomed. */
const ZOOM_RESET_THRESHOLD = 1.02;

export type ScrubPreview = { target: number; delta: number } | null;

type Options = {
  enabled: boolean;
  layerRef: RefObject<HTMLDivElement | null>;
  videoRef: RefObject<HTMLVideoElement | null>;
  seekBy: (delta: number) => void;
  toggleFullscreen: () => void;
  /** Called when a touch turns into a gesture, so a pending hold-to-speed-up is dropped. */
  onGestureStart: () => void;
  onScrub: (preview: ScrubPreview) => void;
  /** Changing this (a new video) puts the zoom back. */
  resetKey?: string | null;
};

type Point = { x: number; y: number };
type Mode = "idle" | "pending" | "scrub" | "vertical" | "pan" | "pinch" | "done";

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

/**
 * Touch gestures for the video, matching Flow for Android:
 * a sideways drag scrubs, a vertical drag enters or leaves fullscreen, and two fingers
 * pinch to zoom and pan. Taps, double taps and hold-to-speed-up stay with the overlay.
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

    const begin = (next: Mode) => {
      mode = next;
      swallowClick = true;
      latest.current.onGestureStart();
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
          begin("vertical");
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
        if (!cancelled) {
          const dy = end.y - start.y;
          const inFullscreen = usePlayerStore.getState().isVideoFullscreen;
          if (inFullscreen && dy > FULLSCREEN_DRAG_PX) latest.current.toggleFullscreen();
          else if (!inFullscreen && dy < -FULLSCREEN_DRAG_PX) latest.current.toggleFullscreen();
        }
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
      latest.current.onScrub(null);
      resetZoom();
    };
  }, [enabled, resetKey]);
}
