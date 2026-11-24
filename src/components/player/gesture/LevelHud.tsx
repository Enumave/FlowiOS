import { useEffect, useImperativeHandle, useRef, type Ref } from "react";
import { Sun, Volume1, Volume2, VolumeX } from "lucide-react";
import type { LevelPreview } from "./touchGestures";

/**
 * The brightness / volume read-out of Flow for Android's circular style (CircularLevelHud): a ring
 * that fills clockwise from the top around a dark disc with the icon, and the percentage under it,
 * in the middle of the picture. Sizes are Android's dp read as CSS pixels.
 *
 * It is driven imperatively (`ref.current.set(level)`) rather than through React state. A swipe
 * moves it on every pointer move, and going through state would re-render the whole gesture overlay
 * each time; writing three attributes straight into the DOM keeps the read-out as quick as the
 * finger. Nothing here is animated per frame (no transition on the ring), so it never lags behind.
 */
const RING = 104;
const STROKE = 8;
const DISC = 56;
const ICON = 28;
const RADIUS = (RING - STROKE) / 2;
const CIRCUMFERENCE = 2 * Math.PI * RADIUS;
const FADE_MS = 150;

type IconKey = "sun" | "high" | "low" | "mute";

export type LevelHudHandle = {
  /** Shows or updates the read-out with the level; null fades it out. */
  set: (level: LevelPreview) => void;
};

function iconKeyFor(level: NonNullable<LevelPreview>): IconKey {
  if (level.kind === "brightness") return "sun";
  if (level.value > 0.6) return "high";
  if (level.value > 0.1) return "low";
  return "mute";
}

export function LevelHud({ ref }: { ref?: Ref<LevelHudHandle> }) {
  const root = useRef<HTMLDivElement>(null);
  const arc = useRef<SVGCircleElement>(null);
  const label = useRef<HTMLSpanElement>(null);
  const icons = useRef<Record<IconKey, HTMLSpanElement | null>>({ sun: null, high: null, low: null, mute: null });
  const state = useRef<{ icon: IconKey | null; shown: boolean; hideTimer: number | undefined }>({
    icon: null,
    shown: false,
    hideTimer: undefined,
  });

  useImperativeHandle(
    ref,
    () => ({
      set(level) {
        const element = root.current;
        if (!element) return;
        const current = state.current;
        window.clearTimeout(current.hideTimer);

        if (!level) {
          current.shown = false;
          element.style.opacity = "0";
          current.hideTimer = window.setTimeout(() => {
            if (!current.shown) element.style.visibility = "hidden";
          }, FADE_MS);
          return;
        }

        if (!current.shown) {
          current.shown = true;
          element.style.visibility = "visible";
          element.style.opacity = "1";
        }
        const progress = Math.min(1, Math.max(0, level.value));
        const ring = arc.current;
        if (ring) {
          ring.setAttribute("stroke-dashoffset", String(CIRCUMFERENCE * (1 - progress)));
          // A round cap would draw a dot at zero.
          ring.style.opacity = progress > 0 ? "1" : "0";
        }
        if (label.current) label.current.textContent = `${Math.round(progress * 100)}%`;
        const key = iconKeyFor(level);
        if (key !== current.icon) {
          current.icon = key;
          for (const [name, holder] of Object.entries(icons.current)) {
            if (holder) holder.style.display = name === key ? "grid" : "none";
          }
        }
      },
    }),
    [],
  );

  useEffect(() => () => window.clearTimeout(state.current.hideTimer), []);

  const holder = (key: IconKey) => (node: HTMLSpanElement | null) => {
    icons.current[key] = node;
  };

  return (
    <div className="pointer-events-none absolute inset-0 z-30 flex items-center justify-center">
      <div
        ref={root}
        className="invisible flex w-[148px] flex-col items-center px-[18px] py-4 opacity-0 transition-opacity duration-150"
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
              ref={arc}
              cx={RING / 2}
              cy={RING / 2}
              r={RADIUS}
              fill="none"
              strokeWidth={STROKE}
              strokeLinecap="round"
              strokeDasharray={CIRCUMFERENCE}
              strokeDashoffset={CIRCUMFERENCE}
              style={{ stroke: "var(--color-primary)", opacity: 0 }}
            />
          </svg>
          <div
            className="grid place-items-center rounded-full"
            style={{ width: DISC, height: DISC, background: "rgba(0, 0, 0, 0.54)" }}
          >
            <span ref={holder("sun")} className="hidden text-chrome-white">
              <Sun size={ICON} />
            </span>
            <span ref={holder("high")} className="hidden text-chrome-white">
              <Volume2 size={ICON} />
            </span>
            <span ref={holder("low")} className="hidden text-chrome-white">
              <Volume1 size={ICON} />
            </span>
            <span ref={holder("mute")} className="hidden text-chrome-white">
              <VolumeX size={ICON} />
            </span>
          </div>
        </div>
        <span
          ref={label}
          className="mt-2.5 text-sm font-bold tabular-nums text-chrome-white [text-shadow:0_1px_3px_rgba(0,0,0,0.55)]"
        />
      </div>
    </div>
  );
}
