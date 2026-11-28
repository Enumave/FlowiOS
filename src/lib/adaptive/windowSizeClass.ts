/**
 * Window size classes and the layout rules built on them, ported from Flow for Android
 * (`ui/utils/WindowSizeClass.kt`, `FlowNavigationChrome.kt`, `PlayerLayoutMode.kt`,
 * `FeedGridLayout.kt`). One CSS pixel is one dp, so the Material breakpoints carry over as they are.
 *
 * Everything here is pure: the React side lives in `useWindowSizeClass.ts`.
 */

/** Material 3 window size class breakpoints (dp / CSS px), the V2 set Flow for Android uses. */
export const WIDTH_BREAKPOINT = { medium: 600, expanded: 840, large: 1200, extraLarge: 1600 } as const;
/**
 * Narrowest window whose rail may open to show labels beside its icons. Android opens its rail from
 * 1200 dp. An iPad mini on its side is 1133 wide and still has the room (a 224 px rail leaves 909 for
 * the page), so the toggle starts at 1100.
 */
export const RAIL_EXPANDABLE_MIN_WIDTH = 1100;
export const HEIGHT_BREAKPOINT = { medium: 480, expanded: 900 } as const;

export type WidthClass = "compact" | "medium" | "expanded" | "large" | "extraLarge";
export type HeightClass = "compact" | "medium" | "expanded";

export interface WindowSizeClass {
  width: WidthClass;
  height: HeightClass;
  /** Whether the window is wider than tall. A size class alone cannot say: see Android's LocalWindowIsLandscape. */
  isLandscape: boolean;
  widthPx: number;
  heightPx: number;
}

const WIDTH_ORDER: WidthClass[] = ["compact", "medium", "expanded", "large", "extraLarge"];
const HEIGHT_ORDER: HeightClass[] = ["compact", "medium", "expanded"];

export function widthClassOf(widthPx: number): WidthClass {
  if (widthPx >= WIDTH_BREAKPOINT.extraLarge) return "extraLarge";
  if (widthPx >= WIDTH_BREAKPOINT.large) return "large";
  if (widthPx >= WIDTH_BREAKPOINT.expanded) return "expanded";
  if (widthPx >= WIDTH_BREAKPOINT.medium) return "medium";
  return "compact";
}

export function heightClassOf(heightPx: number): HeightClass {
  if (heightPx >= HEIGHT_BREAKPOINT.expanded) return "expanded";
  if (heightPx >= HEIGHT_BREAKPOINT.medium) return "medium";
  return "compact";
}

export function windowSizeClassOf(widthPx: number, heightPx: number): WindowSizeClass {
  return {
    width: widthClassOf(widthPx),
    height: heightClassOf(heightPx),
    isLandscape: widthPx > heightPx,
    widthPx,
    heightPx,
  };
}

const atLeastWidth = (sc: WindowSizeClass, floor: WidthClass) => WIDTH_ORDER.indexOf(sc.width) >= WIDTH_ORDER.indexOf(floor);
const atLeastHeight = (sc: WindowSizeClass, floor: HeightClass) => HEIGHT_ORDER.indexOf(sc.height) >= HEIGHT_ORDER.indexOf(floor);

export const isMediumWidth = (sc: WindowSizeClass) => atLeastWidth(sc, "medium");
export const isExpandedWidth = (sc: WindowSizeClass) => atLeastWidth(sc, "expanded");
export const isLargeWidth = (sc: WindowSizeClass) => atLeastWidth(sc, "large");
export const isMediumHeight = (sc: WindowSizeClass) => atLeastHeight(sc, "medium");

// ---------------------------------------------------------------------------
// Navigation
// ---------------------------------------------------------------------------

/** The most tabs a bottom bar shows; a sixth moves it, and the rest, behind "More". */
export const MAX_BAR_TABS = 5;

/**
 * Whether this window navigates from the start edge instead of the bottom. An expanded window tall
 * enough for the rail's items gets it, as on tablets. A landscape window too short for that, a
 * phone on its side, gets it too: a bottom bar would take a sixth of its height. The decision
 * belongs to the window, so a phone-width Split View keeps the bar on an iPad.
 */
export function usesNavigationRail(sc: WindowSizeClass): boolean {
  return (isExpandedWidth(sc) && isMediumHeight(sc)) || (sc.isLandscape && !isMediumHeight(sc));
}

/** Whether the rail may open to show labels beside the icons: only windows wide enough have room. */
export function railIsExpandable(sc: WindowSizeClass): boolean {
  return sc.widthPx >= RAIL_EXPANDABLE_MIN_WIDTH;
}

/** The tabs that fit, and the ones that go behind "More". The last visible slot becomes "More". */
export function splitTabsForOverflow<T>(tabs: readonly T[], capacity: number): { shown: T[]; overflow: T[] } {
  if (tabs.length <= capacity) return { shown: [...tabs], overflow: [] };
  const shown = tabs.slice(0, Math.max(capacity - 1, 0));
  return { shown, overflow: tabs.slice(shown.length) };
}

/** How many rail items of `itemHeightPx` fit one above the other in `availableHeightPx`. */
export function railItemCapacity(availableHeightPx: number, itemHeightPx: number): number {
  return itemHeightPx <= 0 ? 0 : Math.max(Math.floor(availableHeightPx / itemHeightPx), 0);
}

// ---------------------------------------------------------------------------
// Player detail layout
// ---------------------------------------------------------------------------

export type PlayerLayoutMode = "compact" | "medium" | "wide";

/**
 * The detail layout the window can host. The video keeps the top of the window whatever the width,
 * so a window below the medium height has no room for a detail pane and stays single-column.
 *
 * Width alone does not earn the side pane: an upright tablet is expanded-width, but splitting it
 * leaves a narrow video above a half-width page. Upright it wants the full width and a grid
 * (`medium`). The pane is for windows that are actually wider than they are tall.
 */
export function playerLayoutModeFor(sc: WindowSizeClass, opts: { isFullscreen?: boolean; isPip?: boolean } = {}): PlayerLayoutMode {
  if (opts.isFullscreen || opts.isPip) return "compact";
  if (!isMediumHeight(sc)) return "compact";
  if (isExpandedWidth(sc) && sc.isLandscape) return "wide";
  if (isMediumWidth(sc)) return "medium";
  return "compact";
}

// ---------------------------------------------------------------------------
// Feed grids
// ---------------------------------------------------------------------------

/** Narrowest a grid cell may be before the grid drops a column. */
export const FEED_CARD_MIN_WIDTH = 272;
/** Widest a capped cell may grow before a very wide window adds a column anyway. */
export const FEED_CARD_MAX_WIDTH = 460;
/** Past three cards a row of 16:9 thumbnails reads as a strip of stamps. */
export const FEED_MAX_AUTO_COLUMNS = 3;
/** A card's side inset, and the dense variant's. */
export const VIDEO_CARD_INSET = 12;
export const VIDEO_CARD_DENSE_INSET = 4;
/** Widest a single column of rows grows, so it stays readable on a tablet. */
export const FLOW_MAX_CONTENT_WIDTH = 720;

const ITEM_SPACING = 12;
const DENSE_MIN_COLUMNS = 3;

interface GridSpacing {
  margin: number;
  rowSpacing: number;
}
const COMPACT_SPACING: GridSpacing = { margin: 0, rowSpacing: ITEM_SPACING };
const WIDE_SPACING: GridSpacing = { margin: 16, rowSpacing: ITEM_SPACING };
const LARGE_SPACING: GridSpacing = { margin: 24, rowSpacing: 16 };
const DENSE_SPACING: GridSpacing = { margin: 8, rowSpacing: 8 };

export interface FeedGridLayout {
  columns: number;
  /** Horizontal padding of the grid itself; each card's inset brings thumbnails to the margin. */
  contentPadding: number;
  /** Vertical space between rows of cards. */
  cardSpacing: number;
  isCompact: boolean;
  /** How wide one cell is, inset included. */
  cardWidth: number;
  dense: boolean;
  cardInset: number;
  /** Whether stacked cards run edge to edge: only a single compact column does. */
  cardsBleed: boolean;
}

function cappedColumns(availableWidth: number, autoColumns: number, maxAutoColumns: number): number {
  let columns = Math.min(autoColumns, Math.max(maxAutoColumns, 1));
  while (columns < autoColumns && availableWidth / columns > FEED_CARD_MAX_WIDTH) columns++;
  return columns;
}

/**
 * The single layout decision behind every vertical video grid. A compact window is one column of
 * edge-to-edge cards. Wider windows fill with as many cells of at least `minCellWidth` as fit,
 * capped by `maxAutoColumns`. `fixedColumns` pins the count the user chose in settings.
 */
export function feedGridLayoutFor(
  maxWidth: number,
  { fixedColumns = null, maxAutoColumns = FEED_MAX_AUTO_COLUMNS, minCellWidth = FEED_CARD_MIN_WIDTH }: {
    fixedColumns?: number | null;
    maxAutoColumns?: number;
    minCellWidth?: number;
  } = {},
): FeedGridLayout {
  const isCompact = maxWidth < WIDTH_BREAKPOINT.medium;
  const spacing = maxWidth >= WIDTH_BREAKPOINT.large ? LARGE_SPACING : isCompact ? COMPACT_SPACING : WIDE_SPACING;
  const regularPadding = Math.max(spacing.margin - VIDEO_CARD_INSET, 0);
  const dense = isCompact && (fixedColumns ?? 1) >= DENSE_MIN_COLUMNS;
  const cardInset = dense ? VIDEO_CARD_DENSE_INSET : VIDEO_CARD_INSET;
  const contentPadding = dense ? DENSE_SPACING.margin - cardInset : regularPadding;
  const availableWidth = Math.max(maxWidth - contentPadding * 2, 0);
  const autoColumns = isCompact ? 1 : Math.max(Math.floor(availableWidth / minCellWidth), 1);
  const automatic = cappedColumns(availableWidth, autoColumns, maxAutoColumns);
  const columns = fixedColumns ?? automatic;
  return {
    columns,
    contentPadding,
    cardSpacing: dense ? DENSE_SPACING.rowSpacing : spacing.rowSpacing,
    isCompact,
    cardWidth: availableWidth / columns,
    dense,
    cardInset,
    cardsBleed: isCompact && columns === 1,
  };
}

/** One lone grid card on a wide window is a thumbnail blown up to a third of the screen. */
export const feedCardsFormGrid = (columns: number, itemCount: number) => columns > 1 && itemCount > 1;

/**
 * The items whose grid row cannot be filled. A row only holds items from one contiguous run between
 * the full-width rows a hero card or a strip occupies, so a run whose length is not a multiple of
 * `columns` leaves its last row short; those trailing items take a full-width row each instead.
 * `includeLastRun` is false while more pages may still arrive, so the tail does not reflow per page.
 */
export function partialRowIndices(spansOwnRow: readonly boolean[], columns: number, includeLastRun = true): Set<number> {
  const partial = new Set<number>();
  if (columns <= 1) return partial;
  let runStart = -1;
  const closeRun = (endExclusive: number) => {
    if (runStart < 0) return;
    const remainder = (endExclusive - runStart) % columns;
    for (let i = endExclusive - remainder; i < endExclusive; i++) partial.add(i);
    runStart = -1;
  };
  spansOwnRow.forEach((spansRow, index) => {
    if (spansRow) closeRun(index);
    else if (runStart < 0) runStart = index;
  });
  if (includeLastRun) closeRun(spansOwnRow.length);
  return partial;
}

/** A phone shelf previews four rows; a grid previews two full rows so the expander sits on a seam. */
export function feedShelfPreviewCount(columns: number, itemCount: number): number {
  return feedCardsFormGrid(columns, itemCount) ? columns * 2 : 4;
}

/** Width of one card in a horizontally scrolling lane: a phone shows a peek of the next card. */
export function laneItemWidthFor(windowWidth: number, maxWidth: number, peek = 40): number {
  return Math.min(Math.max(windowWidth - 12 * 2 - peek, 240), maxWidth);
}

/** Artwork size for a collection or artist header: over half a phone, capped on wider windows. */
export function heroArtworkSizeFor(windowWidth: number): number {
  return Math.min(Math.max(windowWidth * 0.55, 180), 240);
}

/** Columns for a grid that only has a value per size class (Android's flowGridColumns). */
export function gridColumnsFor(sc: WindowSizeClass, counts: { compact: number; medium: number; expanded: number }): number {
  if (isExpandedWidth(sc)) return counts.expanded;
  if (isMediumWidth(sc)) return counts.medium;
  return counts.compact;
}
