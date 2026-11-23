import { useCallback, useEffect, useRef, useState } from "react";
import { Sun, Volume1, Volume2, VolumeX } from "lucide-react";
import type { LevelPreview } from "./touchGestures";

/**
 * The brightness / volume read-out of Flow for Android's circular style (CircularLevelHud): a ring
 * that fills clockwise from the top around a dark disc with the icon, and the percentage under it,
 * in the middle of the picture. Sizes are Android's dp read as CSS pixels. It fades and scales in
 * from 0.86 and back out, and keeps the last level on screen while it does.
 */
const RING = 104;
const STROKE = 8;
const DISC = 56;
const ICON = 28;
const RADIUS = (RING - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const FADE_MS = 200;

type Level = NonNullable<LevelPreview>;

function iconFor(level: Level) {
  if (level.kind === "brightness") return Sun;
  if (level.value > 0.6) return Volume2;
  if (level.value > 0.1) return Volume1;
  return VolumeX;
}

export function LevelHud({ preview }: { preview: LevelPreview }) {
  const active = preview !== null;
  const lastLevel = useRef<Level | null>(null);
  if (preview) lastLevel.current = preview;

  // Stays mounted for the fade-out after the preview goes.
  const [mounted, setMounted] = useState(false);
  useEffect(() => {
    if (active) {
      setMounted(true);
      return;
    }
    const timer = window.setTimeout(() => setMounted(false), FADE_MS);
    return () => window.clearTimeout(timer);
  }, [active]);

  // A stable ref callback, so the entrance plays once when the HUD appears and not on every move.
  const playEntrance = useCallback((element: HTMLDivElement | null) => {
    element?.animate?.(
      [
        { opacity: 0, transform: "scale(0.86)" },
        { opacity: 1, transform: "scale(1)" },
      ],
      { duration: 160, easing: "ease-out" },
    );
  }, []);

  const level = preview ?? lastLevel.current;
  if ((!mounted && !active) || !level) return null;

  const Icon = iconFor(level);
  const progress = Math.min(1, Math.max(0, level.value));
  const percent = Math.round(progress * 100);

  return (
    <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center">
      <div
        ref={playEntrance}
        className="flex w-[148px] flex-col items-center px-[18px] py-4"
        style={{
          opacity: active ? 1 : 0,
          transform: active ? "scale(1)" : "scale(0.92)",
          transition: `opacity ${FADE_MS}ms ease, transform ${FADE_MS}ms ease`,
        }}
      >
        <div className="relative grid place-items-center" style={{ width: RING, height: RING }}>
          <svg
            width={RING}
            height={RING}
            viewBox={`0 0 ${RING} ${RING}`}
            className="absolute inset-0 -rotate-90"
            aria-hidden="true"
          >
            <circle
              cx={RING / 2}
              cy={RING / 2}
              r={RADIUS}
              fill="none"
              strokeWidth={STROKE}
              style={{ stroke: "rgba(0, 0, 0, 0.4)" }}
            />
            <circle
              cx={RING / 2}
              cy={RING / 2}
              r={RADIUS}
              fill="none"
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={CIRCUMFERENCE * (1 - progress)}
              style={{
                stroke: "var(--color-primary)",
                // A round cap would draw a dot at zero.
                opacity: progress > 0 ? 1 : 0,
                transition: "stroke-dashoffset 90ms linear",
              }}
            />
          </svg>
          <div
            className="grid place-items-center rounded-full"
            style={{ width: DISC, height: DISC, background: "rgba(0, 0, 0, 0.54)" }}
          >
            <Icon size={ICON} className="text-chrome-white" />
          </div>
        </div>
        <span className="mt-2.5 text-sm font-bold tabular-nums text-chrome-white [text-shadow:0_1px_3px_rgba(0,0,0,0.55)]">
          {percent}%
        </span>
      </div>
    </div>
  );
}
