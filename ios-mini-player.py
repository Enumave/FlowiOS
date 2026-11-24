#!/usr/bin/env python3
"""Make the floating mini player move the way Flow for Android's does.

Run from the repository root after `ios-adaptive.py`. The rules live in
src/lib/adaptive/miniPlayerCorner.ts; this only wires them into src/lib/useMiniPlayerDrag.ts, and
only where the adaptive layouts run (desktop is untouched).

If `useMiniPlayerDrag.ts` has changed so that an edit no longer matches, the whole group is skipped
with a warning and the build carries on.
"""

REL = "src/lib/useMiniPlayerDrag.ts"

EDITS = [
    # imports
    (
        'import { miniPlayerWidthPx } from "./miniPlayerSize";\n',
        'import { miniPlayerWidthPx } from "./miniPlayerSize";\n'
        'import { usePlayerStore } from "../store/usePlayerStore";\n'
        'import { IS_ADAPTIVE_LAYOUT } from "./adaptive/runtime";\n'
        "import {\n"
        "  adaptiveMiniBounds,\n"
        "  cornerOfRatios,\n"
        "  createMiniDragTracker,\n"
        "  decideMiniRelease,\n"
        "  ratiosOfCorner,\n"
        "  rubberBand,\n"
        "  settleMiniPlayer,\n"
        "  snapToCorner,\n"
        '} from "./adaptive/miniPlayerCorner";\n',
    ),
    # where it may rest
    (
        "  topGutter = TOP_TITLEBAR_GUTTER,\n): MiniPlayerBounds {\n",
        "  topGutter = TOP_TITLEBAR_GUTTER,\n): MiniPlayerBounds {\n"
        "  // Android's mini player rests 8 px from the sides, above the bottom bar and below the top bar.\n"
        "  if (IS_ADAPTIVE_LAYOUT) return adaptiveMiniBounds(viewportWidth, viewportHeight, playerWidth, playerHeight);\n",
    ),
    # a position saved by the free-drag player becomes the corner nearest it
    (
        "export function parseSavedPosition(raw: string | null | undefined): MiniPlayerRatios {\n",
        "export function parseSavedPosition(raw: string | null | undefined): MiniPlayerRatios {\n"
        "  const ratios = parseSavedRatios(raw);\n"
        "  return IS_ADAPTIVE_LAYOUT ? snapToCorner(ratios) : ratios;\n"
        "}\n"
        "\n"
        "function parseSavedRatios(raw: string | null | undefined): MiniPlayerRatios {\n",
    ),
    # finger tracking
    (
        "  const isDraggingActiveRef = useRef(false);\n",
        "  const isDraggingActiveRef = useRef(false);\n  const miniDragRef = useRef(createMiniDragTracker());\n",
    ),
    (
        "      if (target?.closest(\"[data-drag-ignore='true']\")) return;\n",
        "      if (target?.closest(\"[data-drag-ignore='true']\")) return;\n"
        "      // Grabbing it mid-settle takes it where it is going, and the drag starts from there.\n"
        "      if (IS_ADAPTIVE_LAYOUT) frameRef.current?.getAnimations?.().forEach((animation) => animation.cancel());\n",
    ),
    (
        "      pressRef.current = { id: event.pointerId, x: event.clientX, y: event.clientY };\n"
        "      startPosRef.current = currentPos;\n",
        "      pressRef.current = { id: event.pointerId, x: event.clientX, y: event.clientY };\n"
        "      startPosRef.current = currentPos;\n"
        "      miniDragRef.current.reset();\n"
        "      miniDragRef.current.push(event.timeStamp, currentPos.x, currentPos.y);\n",
    ),
    # dragging: follow the finger, stretching past the edge
    (
        "      const nextX = Math.max(bounds.minX, Math.min(bounds.maxX, startPosRef.current.x + dx));\n"
        "      const nextY = Math.max(bounds.minY, Math.min(bounds.maxY, startPosRef.current.y + dy));\n"
        "\n"
        "      syncPositionToDom(nextX, nextY);\n",
        "      const rawX = startPosRef.current.x + dx;\n"
        "      const rawY = startPosRef.current.y + dy;\n"
        "      if (IS_ADAPTIVE_LAYOUT) {\n"
        "        // Follows the finger, stretching a third as far past the edge; the release settles it.\n"
        "        miniDragRef.current.push(event.timeStamp, rawX, rawY);\n"
        "        syncPositionToDom(rubberBand(rawX, bounds.minX, bounds.maxX), rubberBand(rawY, bounds.minY, bounds.maxY));\n"
        "        return;\n"
        "      }\n"
        "      const nextX = Math.max(bounds.minX, Math.min(bounds.maxX, rawX));\n"
        "      const nextY = Math.max(bounds.minY, Math.min(bounds.maxY, rawY));\n"
        "\n"
        "      syncPositionToDom(nextX, nextY);\n",
    ),
    # release: settle into a corner, or close
    (
        "    const currentPos = currentPosRef.current || positionFromRatios(ratiosRef.current, bounds);\n"
        "    const newRatios = ratiosFromPosition(currentPos.x, currentPos.y, bounds);\n",
        "    const currentPos = currentPosRef.current || positionFromRatios(ratiosRef.current, bounds);\n"
        "    const settlingFrame = frameRef.current;\n"
        "    if (IS_ADAPTIVE_LAYOUT && settlingFrame) {\n"
        "      // Android's mini player settles into a corner, or closes if it was pulled off the bottom.\n"
        "      const tracker = miniDragRef.current;\n"
        "      const pixelRatio = window.devicePixelRatio || 1;\n"
        "      const cssVelocity = tracker.velocity(event.timeStamp);\n"
        "      const release = decideMiniRelease({\n"
        "        finger: tracker.finger ?? currentPos,\n"
        "        current: currentPos,\n"
        "        startCorner: cornerOfRatios(ratiosRef.current),\n"
        "        bounds,\n"
        "        miniHeight: dims.height,\n"
        "        // Android measures speed in physical pixels.\n"
        "        velocity: { x: cssVelocity.x * pixelRatio, y: cssVelocity.y * pixelRatio },\n"
        "      });\n"
        "      settleMiniPlayer({\n"
        "        frame: settlingFrame,\n"
        "        from: currentPos,\n"
        "        bounds,\n"
        "        miniHeight: dims.height,\n"
        "        viewportHeight: window.innerHeight,\n"
        "        release,\n"
        "        velocity: cssVelocity,\n"
        "        onDone: (done) => {\n"
        '          if (done.kind === "close") {\n'
        "            usePlayerStore.getState().dismissVideoPlayer();\n"
        "            return;\n"
        "          }\n"
        "          syncPositionToDom(done.x, done.y);\n"
        "          const settled = ratiosOfCorner(done.corner);\n"
        "          ratiosRef.current = settled;\n"
        "          void setSettingValue(SETTINGS.MINI_PLAYER_POSITION, JSON.stringify(settled));\n"
        "        },\n"
        "      });\n"
        "      return;\n"
        "    }\n"
        "    const newRatios = ratiosFromPosition(currentPos.x, currentPos.y, bounds);\n",
    ),
]


def main():
    try:
        with open(REL, encoding="utf-8") as f:
            text = f.read()
    except OSError:
        print(f"ios-mini-player: SKIPPED: {REL} not found")
        return
    for old, _ in EDITS:
        if text.count(old) != 1:
            print(f"ios-mini-player: SKIPPED: snippet not found once in {REL}:\n{old[:140]}")
            return
    for old, new in EDITS:
        text = text.replace(old, new)
    with open(REL, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
    print(f"patched {REL}")
    print("ios-mini-player: done")


main()
