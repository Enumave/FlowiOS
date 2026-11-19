import { useMemo } from "react";
import { useAdaptiveContentWidth } from "./useWindowSizeClass";
import { feedGridLayoutFor } from "./windowSizeClass";

/** The CSS variables `.flow-grid` reads, as Flow for Android's feed grid would size them. */
export interface AdaptiveGridVars {
  columns: number;
  cardMin: string;
  gap: string;
}

/** Extra columns for square and portrait cards (shorts, albums, artists), as on desktop. */
const DENSE_COLUMN_OFFSET = 2;

/**
 * `null` where the adaptive layouts are off. `pinned` is the count the user chose in Settings, or
 * 0 for "automatic": one column on a phone, two on a medium window, up to three on a tablet.
 */
export function useAdaptiveGridVars(pinned: number, density: "video" | "dense", gapRem: number): AdaptiveGridVars | null {
  const width = useAdaptiveContentWidth();
  return useMemo(() => {
    if (width === null) return null;
    const layout = feedGridLayoutFor(width, { fixedColumns: pinned > 0 ? pinned : null });
    const columns = pinned > 0 ? layout.columns : density === "dense" ? layout.columns + DENSE_COLUMN_OFFSET : layout.columns;
    // The column count is exact here, so the per-card minimum that sheds columns stays out of the way.
    return { columns, cardMin: "1px", gap: `${gapRem}rem` };
  }, [width, pinned, density, gapRem]);
}
