import { useEffect, useImperativeHandle, useRef, type Ref } from "react";
import type { StoryboardLevel } from "../../types/video";

/**
 * The scrub preview of Flow for Android (SeekPreviewStrip): while the seek bar is held, a filmstrip
 * sits above it with the read-out (time, and the chapter) over it.
 *
 * The strip is a magnified timeline rather than the whole video: one frame per storyboard interval,
 * laid out at a fixed width per frame, with the frame being seeked to under the playhead and its
 * neighbours either side. It slides under the thumb much faster than the thumb crosses the bar,
 * which is what makes it worth showing instead of one frame. Frames before the start or past the
 * end are left out, so an empty stretch says there is nothing further to scrub to.
 *
 * It is driven imperatively and drawn on a canvas, like the level read-out: a drag updates it on
 * every pointer move, and going through React state would re-render the controls each time. The
 * storyboard sheets (dozens of frames each) are fetched only when a frame on them is drawn.
 */
const STRIP_HEIGHT = 64;
/** The frame width a storyboard level is picked against; the level's own aspect sets the real one. */
export const FILMSTRIP_NOMINAL_FRAME_WIDTH = 112;
const FRAME_GAP = 2;
const PLAYHEAD_WIDTH = 2;
const FADE_MS = 120;
const MAX_CACHED_SHEETS = 16;

export type FilmstripUpdate = {
  /** The time being seeked to. */
  seconds: number;
  duration: number;
  /** The width the strip is drawn across: the seek bar's. */
  trackWidth: number;
  /** Null when the video has no storyboard: the read-out still shows, without a strip. */
  level: StoryboardLevel | null;
  imageUrl: (url: string) => string;
  timeText: string;
  chapter?: string;
};

export type SeekFilmstripHandle = {
  update: (state: FilmstripUpdate) => void;
  hide: () => void;
};

type Frame = { index: number; left: number };

/** Android's seekStripFrames: the frames visible in the strip, each with where its left edge falls. */
function stripFrames(
  positionMs: number,
  intervalMs: number,
  frameCount: number,
  thumbX: number,
  frameWidth: number,
  stripWidth: number,
): Frame[] {
  if (intervalMs <= 0 || frameCount <= 0 || frameWidth < 1 || stripWidth <= 0) return [];
  const pxPerMs = frameWidth / intervalMs;
  const firstMs = positionMs - (thumbX + frameWidth) / pxPerMs;
  const lastMs = positionMs + (stripWidth - thumbX) / pxPerMs;
  const first = Math.max(0, Math.floor(firstMs / intervalMs));
  const last = Math.min(frameCount - 1, Math.ceil(lastMs / intervalMs));
  const frames: Frame[] = [];
  for (let index = first; index <= last; index++) {
    const left = thumbX + (index * intervalMs - positionMs) * pxPerMs;
    if (left < stripWidth && left + frameWidth > 0) frames.push({ index, left });
  }
  return frames;
}

export function SeekFilmstrip({ ref }: { ref?: Ref<SeekFilmstripHandle> }) {
  const root = useRef<HTMLDivElement>(null);
  const timeLabel = useRef<HTMLSpanElement>(null);
  const chapterLabel = useRef<HTMLSpanElement>(null);
  const stripBox = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);

  const state = useRef({
    shown: false,
    hideTimer: undefined as number | undefined,
    frame: 0,
    latest: null as FilmstripUpdate | null,
    sheets: new Map<string, HTMLImageElement>(),
  });

  const draw = () => {
    const current = state.current;
    current.frame = 0;
    const update = current.latest;
    const element = canvas.current;
    const context = element?.getContext("2d");
    if (!update || !element || !context || !update.level || !(update.duration > 0)) return;

    const { level, trackWidth } = update;
    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.round(trackWidth * dpr);
    const pixelHeight = Math.round(STRIP_HEIGHT * dpr);
    if (element.width !== pixelWidth || element.height !== pixelHeight) {
      element.width = pixelWidth;
      element.height = pixelHeight;
    }
    context.setTransform(dpr, 0, 0, dpr, 0, 0);
    context.clearRect(0, 0, trackWidth, STRIP_HEIGHT);

    const frameWidth = (STRIP_HEIGHT * level.width) / level.height;
    const positionMs = update.seconds * 1000;
    const thumbX = Math.min(1, Math.max(0, update.seconds / update.duration)) * trackWidth;
    const perSheet = level.columns * level.rows;
    const drawnWidth = frameWidth - FRAME_GAP;

    for (const { index, left } of stripFrames(positionMs, level.intervalMs, level.count, thumbX, frameWidth, trackWidth)) {
      const sheetIndex = Math.floor(index / perSheet);
      const within = index % perSheet;
      const url = update.imageUrl(level.urlTemplate.replace("$M", String(sheetIndex)));
      let sheet = current.sheets.get(url);
      if (!sheet) {
        sheet = new Image();
        sheet.decoding = "async";
        sheet.onload = () => {
          if (!current.frame) current.frame = requestAnimationFrame(draw);
        };
        sheet.src = url;
        current.sheets.set(url, sheet);
        if (current.sheets.size > MAX_CACHED_SHEETS) {
          const oldest = current.sheets.keys().next().value;
          if (oldest !== undefined) current.sheets.delete(oldest);
        }
      }
      // Not loaded yet: that frame stays empty and the load redraws.
      if (!sheet.complete || sheet.naturalWidth === 0) continue;
      const sourceX = (within % level.columns) * level.width;
      const sourceY = Math.floor(within / level.columns) * level.height;
      // The gap is cut off the frame's right edge, as Android clips it, rather than squeezing the frame.
      const sourceWidth = (level.width * drawnWidth) / frameWidth;
      context.drawImage(sheet, sourceX, sourceY, sourceWidth, level.height, left, 0, drawnWidth, STRIP_HEIGHT);
    }

    context.fillStyle = "#ffffff";
    context.fillRect(thumbX - PLAYHEAD_WIDTH / 2, 0, PLAYHEAD_WIDTH, STRIP_HEIGHT);
  };

  useImperativeHandle(
    ref,
    () => ({
      update(next) {
        const element = root.current;
        if (!element) return;
        const current = state.current;
        window.clearTimeout(current.hideTimer);
        if (!current.shown) {
          current.shown = true;
          element.style.visibility = "visible";
          element.style.opacity = "1";
        }
        current.latest = next;
        if (timeLabel.current) timeLabel.current.textContent = next.timeText;
        if (chapterLabel.current) {
          chapterLabel.current.textContent = next.chapter ?? "";
          chapterLabel.current.style.display = next.chapter ? "block" : "none";
        }
        if (stripBox.current) stripBox.current.style.display = next.level ? "block" : "none";
        if (next.level && !current.frame) current.frame = requestAnimationFrame(draw);
      },
      hide() {
        const element = root.current;
        if (!element) return;
        const current = state.current;
        if (!current.shown) return;
        current.shown = false;
        element.style.opacity = "0";
        window.clearTimeout(current.hideTimer);
        current.hideTimer = window.setTimeout(() => {
          if (!current.shown) element.style.visibility = "hidden";
        }, FADE_MS);
      },
    }),
    [],
  );

  useEffect(() => {
    const current = state.current;
    return () => {
      window.clearTimeout(current.hideTimer);
      cancelAnimationFrame(current.frame);
    };
  }, []);

  return (
    <div
      ref={root}
      data-seek-filmstrip
      className="pointer-events-none invisible absolute inset-x-0 z-50 flex flex-col gap-2 opacity-0 transition-opacity duration-100"
    >
      <div className="flex min-w-0 items-center gap-2">
        <span
          ref={timeLabel}
          className="shrink-0 whitespace-nowrap rounded-full bg-chrome-black/55 px-3 py-1 text-xs font-semibold tabular-nums text-chrome-white"
        />
        <span
          ref={chapterLabel}
          className="hidden min-w-0 truncate rounded-full bg-chrome-black/55 px-3 py-1 text-xs font-medium text-chrome-white"
        />
      </div>
      <div
        ref={stripBox}
        className="relative hidden overflow-hidden rounded-lg"
        style={{ height: STRIP_HEIGHT, background: "rgba(0, 0, 0, 0.5)" }}
      >
        <canvas ref={canvas} className="absolute inset-0 h-full w-full" />
      </div>
    </div>
  );
}
