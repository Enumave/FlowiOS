import { IS_ADAPTIVE_LAYOUT } from "./runtime";
import { useWindowSize } from "./useWindowSizeClass";
import { laneItemWidthFor, WIDTH_BREAKPOINT } from "./windowSizeClass";
import type { CSSProperties } from "react";

export interface AdaptiveCard {
  /** Whether cards are drawn the way Flow for Android draws them. */
  active: boolean;
  /** A single compact column runs the thumbnail edge to edge; wider windows inset it. */
  bleed: boolean;
}

const OFF: AdaptiveCard = { active: false, bleed: false };

/** Card styling for the shared video card. Off (and free) outside the adaptive layouts. */
export function useAdaptiveCard(): AdaptiveCard {
  const { width } = useWindowSize();
  if (!IS_ADAPTIVE_LAYOUT) return OFF;
  return { active: true, bleed: width < WIDTH_BREAKPOINT.medium };
}

const LANE_MAX_WIDTH = 350;

/** One card of a sideways shelf: a phone shows a peek of the next, a tablet stops at 350. */
export function useAdaptiveLaneStyle(): CSSProperties | undefined {
  const { width } = useWindowSize();
  if (!IS_ADAPTIVE_LAYOUT) return undefined;
  const cardWidth = laneItemWidthFor(width, LANE_MAX_WIDTH);
  return { width: cardWidth };
}
