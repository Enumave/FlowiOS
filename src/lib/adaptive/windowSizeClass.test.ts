import { describe, expect, it } from "vitest";
import {
  feedGridLayoutFor,
  feedShelfPreviewCount,
  gridColumnsFor,
  heroArtworkSizeFor,
  laneItemWidthFor,
  partialRowIndices,
  playerLayoutModeFor,
  railItemCapacity,
  splitTabsForOverflow,
  usesNavigationRail,
  windowSizeClassOf,
} from "./windowSizeClass";

const sc = windowSizeClassOf;

describe("size classes", () => {
  it("buckets by the Material breakpoints", () => {
    expect(sc(599, 800).width).toBe("compact");
    expect(sc(600, 800).width).toBe("medium");
    expect(sc(839, 800).width).toBe("medium");
    expect(sc(840, 800).width).toBe("expanded");
    expect(sc(1200, 800).width).toBe("large");
    expect(sc(1600, 800).width).toBe("extraLarge");
    expect(sc(900, 479).height).toBe("compact");
    expect(sc(900, 480).height).toBe("medium");
    expect(sc(900, 900).height).toBe("expanded");
  });

  it("tells landscape from the real proportion, not the bucket", () => {
    expect(sc(900, 1100).isLandscape).toBe(false);
    expect(sc(1100, 900).isLandscape).toBe(true);
    // Both are expanded wide: the bucket cannot say which way the window is held.
    expect(sc(900, 1100).width).toBe(sc(1100, 900).width);
  });
});

describe("navigation rail", () => {
  it("keeps the bottom bar on phones and medium windows", () => {
    expect(usesNavigationRail(sc(390, 844))).toBe(false); // iPhone portrait
    expect(usesNavigationRail(sc(820, 1180))).toBe(false); // iPad Air portrait is medium
    expect(usesNavigationRail(sc(700, 900))).toBe(false); // Split View
  });

  it("uses the rail on expanded tablet windows, either orientation", () => {
    expect(usesNavigationRail(sc(1024, 1366))).toBe(true); // iPad Pro 12.9 portrait
    expect(usesNavigationRail(sc(1180, 820))).toBe(true); // iPad Air landscape
    expect(usesNavigationRail(sc(1366, 1024))).toBe(true);
  });

  it("uses the rail on a phone on its side, where a bar would eat the height", () => {
    expect(usesNavigationRail(sc(844, 390))).toBe(true);
    expect(usesNavigationRail(sc(667, 375))).toBe(true);
  });

  it("keeps a phone-width Split View on the bar even on a big display", () => {
    expect(usesNavigationRail(sc(375, 1024))).toBe(false);
  });

  it("moves what does not fit behind More", () => {
    expect(splitTabsForOverflow([1, 2, 3], 5)).toEqual({ shown: [1, 2, 3], overflow: [] });
    expect(splitTabsForOverflow([1, 2, 3, 4, 5, 6, 7], 5)).toEqual({ shown: [1, 2, 3, 4], overflow: [5, 6, 7] });
    expect(splitTabsForOverflow([1, 2], 0)).toEqual({ shown: [], overflow: [1, 2] });
    expect(railItemCapacity(300, 64)).toBe(4);
    expect(railItemCapacity(300, 0)).toBe(0);
  });
});

describe("player layout", () => {
  it("is single column on a phone and when fullscreen or PiP takes the window", () => {
    expect(playerLayoutModeFor(sc(390, 844))).toBe("compact");
    expect(playerLayoutModeFor(sc(1366, 1024), { isFullscreen: true })).toBe("compact");
    expect(playerLayoutModeFor(sc(1366, 1024), { isPip: true })).toBe("compact");
  });

  it("is single column with a grid on a medium or upright tablet window", () => {
    expect(playerLayoutModeFor(sc(820, 1180))).toBe("medium");
    expect(playerLayoutModeFor(sc(1024, 1366))).toBe("medium");
  });

  it("splits only a landscape expanded window", () => {
    expect(playerLayoutModeFor(sc(1180, 820))).toBe("wide");
    expect(playerLayoutModeFor(sc(1366, 1024))).toBe("wide");
  });

  it("stays single column when too short for a detail pane, however wide", () => {
    expect(playerLayoutModeFor(sc(1000, 400))).toBe("compact");
  });
});

describe("feed grid", () => {
  it("is one edge-to-edge column on a phone", () => {
    const grid = feedGridLayoutFor(390);
    expect(grid.columns).toBe(1);
    expect(grid.isCompact).toBe(true);
    expect(grid.cardsBleed).toBe(true);
    expect(grid.contentPadding).toBe(0);
  });

  it("goes to two columns on a medium window and caps at three", () => {
    expect(feedGridLayoutFor(700).columns).toBe(2);
    expect(feedGridLayoutFor(820).columns).toBe(2);
    expect(feedGridLayoutFor(1024).columns).toBe(3);
    expect(feedGridLayoutFor(1366).columns).toBe(3);
    expect(feedGridLayoutFor(2000).columns).toBeGreaterThanOrEqual(3);
  });

  it("pins the user's choice and goes dense at three on a phone", () => {
    const pinned = feedGridLayoutFor(390, { fixedColumns: 3 });
    expect(pinned.columns).toBe(3);
    expect(pinned.dense).toBe(true);
    expect(pinned.cardInset).toBe(4);
    expect(pinned.cardsBleed).toBe(false);
    expect(feedGridLayoutFor(390, { fixedColumns: 2 }).dense).toBe(false);
  });

  it("only grids more than one card", () => {
    expect(feedShelfPreviewCount(3, 1)).toBe(4);
    expect(feedShelfPreviewCount(3, 9)).toBe(6);
    expect(feedShelfPreviewCount(1, 9)).toBe(4);
  });

  it("gives short last rows a full-width row each", () => {
    expect([...partialRowIndices([false, false, false, false, false], 3)]).toEqual([3, 4]);
    expect([...partialRowIndices([false, false, true, false, false, false, false], 3)]).toEqual([0, 1, 6]);
    expect([...partialRowIndices([false, false, false, false], 3, false)]).toEqual([]);
    expect(partialRowIndices([false, false], 1).size).toBe(0);
  });
});

describe("sizes", () => {
  it("sizes lane cards and hero artwork from the window", () => {
    expect(laneItemWidthFor(390, 360)).toBe(326);
    expect(laneItemWidthFor(1200, 360)).toBe(360);
    expect(laneItemWidthFor(200, 360)).toBe(240);
    expect(heroArtworkSizeFor(390)).toBeCloseTo(214.5);
    expect(heroArtworkSizeFor(1200)).toBe(240);
    expect(heroArtworkSizeFor(200)).toBe(180);
  });

  it("picks a count per size class", () => {
    const counts = { compact: 1, medium: 2, expanded: 3 };
    expect(gridColumnsFor(sc(390, 800), counts)).toBe(1);
    expect(gridColumnsFor(sc(700, 800), counts)).toBe(2);
    expect(gridColumnsFor(sc(1000, 800), counts)).toBe(3);
  });
});
