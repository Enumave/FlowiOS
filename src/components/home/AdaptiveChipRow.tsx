import { useRef } from "react";
import { useScrollContainer } from "../../lib/useScrollContainer";
import { useEnterAlways } from "../../lib/adaptive/useEnterAlways";
import type { HomeChipOption } from "./HomeChipRow";

const ROW_HEIGHT = 48;

/**
 * The chips above Home's feed as Flow for Android draws them: a 48-high row with 12 of side
 * padding and 8 between chips, which slides away as the feed scrolls down and returns on the first
 * scroll up. A selected chip is filled and an unselected one outlined, and none carries a check, so
 * a chip keeps its width when it is picked.
 */
export function AdaptiveChipRow({
  chips,
  selected,
  onSelect,
}: {
  chips: HomeChipOption[];
  selected: string;
  onSelect: (key: string) => void;
}) {
  const scroller = useScrollContainer();
  const rowRef = useRef<HTMLDivElement>(null);
  useEnterAlways(scroller, rowRef, ROW_HEIGHT);

  return (
    <div ref={rowRef} className="sticky top-0 z-20 -mb-px bg-background will-change-transform">
      <div
        role="tablist"
        className="flex h-12 items-center gap-2 overflow-x-auto px-3 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
      >
        {chips.map((chip) => {
          const active = chip.key === selected;
          return (
            <button
              key={chip.key}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onSelect(chip.key)}
              className={`inline-flex h-8 shrink-0 items-center whitespace-nowrap rounded-lg px-4 text-sm font-medium transition-colors duration-200 ${
                active
                  ? "bg-surface-container-highest text-chrome-neutral-100"
                  : "border border-chrome-neutral-700 text-chrome-neutral-200 active:bg-chrome-neutral-800"
              }`}
            >
              {chip.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
