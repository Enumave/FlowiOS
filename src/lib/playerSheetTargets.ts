import { useAppSettingsStore } from "../store/useAppSettingsStore";
import { usePlayerStore } from "../store/usePlayerStore";
import { SETTINGS } from "./settings/schema";
import { miniPlayerWidthPx } from "./miniPlayerSize";
import { computeMiniPlayerBounds, parseSavedPosition, positionFromRatios } from "./useMiniPlayerDrag";
import { clamp, type PlayerSheetOptions, type SheetTarget } from "./playerSheet";
import type { FrameBox } from "./theaterGlide";

/** The mini player's corners, as `rounded-xl` draws them. */
const MINI_RADIUS_PX = 12;
/** Fraction of the window height a swipe has to cover to reach fullscreen, and to leave it. */
const ENTER_TRAVEL = 0.3;
const EXIT_TRAVEL = 0.35;

const SLOT_SELECTOR = "[data-flow-watch-player-slot='true']";

const boxOf = (rect: DOMRect): FrameBox => ({ top: rect.top, left: rect.left, width: rect.width, height: rect.height });

export const viewportBox = (): FrameBox => ({ top: 0, left: 0, width: window.innerWidth, height: window.innerHeight });

/**
 * Where the mini player will rest: the same size, bounds and saved corner `useMiniPlayerDrag` puts
 * it at, so the frame lands exactly where the layout will hold it.
 */
export function miniPlayerBox(): FrameBox {
  const values = useAppSettingsStore.getState().values;
  const width = Math.min(miniPlayerWidthPx(values[SETTINGS.MINI_PLAYER_SIZE]), window.innerWidth - 32);
  const height = (width * 9) / 16;
  const bounds = computeMiniPlayerBounds(window.innerWidth, window.innerHeight, width, height);
  const position = positionFromRatios(parseSavedPosition(values[SETTINGS.MINI_PLAYER_POSITION]), bounds);
  return { left: position.x, top: position.y, width, height };
}

/** The watch page's player slot, when it is on screen to land in. */
export function watchSlotTarget(): { box: FrameBox; radius: number } | null {
  const slot = document.querySelector<HTMLElement>(SLOT_SELECTOR);
  if (!slot) return null;
  const rect = slot.getBoundingClientRect();
  if (rect.width <= 0 || rect.height <= 0) return null;
  // A slot scrolled off the top or bottom is nothing to land on: a card in the middle is.
  if (rect.bottom <= 0 || rect.top >= window.innerHeight) return null;
  return { box: boxOf(rect), radius: Number.parseFloat(getComputedStyle(slot).borderTopLeftRadius) || 0 };
}

/** Where leaving fullscreen goes when there is no slot to go to: a card in the middle of the window. */
function fallbackCard(): FrameBox {
  const width = window.innerWidth * 0.8;
  const height = (width * 9) / 16;
  return {
    left: (window.innerWidth - width) / 2,
    top: (window.innerHeight - height) / 2,
    width,
    height,
  };
}

/**
 * What each direction of a vertical swipe on the player does right now, or null when the frame
 * is not somewhere a swipe moves it (the mini player has its own drag).
 *
 *   watch page   down: shrink into the mini player        up: grow to fullscreen
 *   fullscreen   down: shrink back to where it came from
 */
export function planPlayerSheet(
  frame: HTMLElement,
): Pick<PlayerSheetOptions, "origin" | "originRadius" | "down" | "up"> | null {
  const player = usePlayerStore.getState();
  const origin = boxOf(frame.getBoundingClientRect());
  if (origin.width <= 0 || origin.height <= 0) return null;
  const originRadius = Number.parseFloat(getComputedStyle(frame).borderTopLeftRadius) || 0;
  const height = window.innerHeight;

  if (player.isVideoFullscreen) {
    const landing =
      player.videoPlayerMode === "pip"
        ? { box: miniPlayerBox(), radius: MINI_RADIUS_PX }
        : (watchSlotTarget() ?? { box: fallbackCard(), radius: MINI_RADIUS_PX });
    const down: SheetTarget = {
      action: "exit-fullscreen",
      ...landing,
      travel: clamp(height * EXIT_TRAVEL, 200, 320),
    };
    return { origin, originRadius, down, up: null };
  }

  if (player.videoPlayerMode !== "watch") return null;

  const mini = miniPlayerBox();
  const minimize: SheetTarget = {
    action: "minimize",
    box: mini,
    radius: MINI_RADIUS_PX,
    // The frame's top edge follows the finger one to one on its way to the mini player's.
    travel: clamp(mini.top - origin.top, 120, height),
  };
  const enterFullscreen: SheetTarget = {
    action: "enter-fullscreen",
    box: viewportBox(),
    radius: 0,
    travel: clamp(height * ENTER_TRAVEL, 180, 260),
  };
  return { origin, originRadius, down: minimize, up: enterFullscreen };
}
