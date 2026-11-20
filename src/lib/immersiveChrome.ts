import { useEffect } from "react";
import { invoke } from "@tauri-apps/api/core";
import { platform } from "@tauri-apps/plugin-os";

const ON_IOS = (() => {
  try {
    return platform() === "ios";
  } catch {
    return false;
  }
})();

const setImmersive = (on: boolean) => {
  if (!ON_IOS) return;
  invoke("set_immersive", { on }).catch(() => {
    // Only iOS builds carry this command, and the bar simply stays visible without it.
  });
};

/**
 * Asks iPadOS to fade out the home indicator (the white bar at the bottom edge) while `on`, as
 * Android's immersive mode hides its navigation bar. It returns by itself after a few idle
 * seconds, and a swipe up from the edge still goes home. A no-op everywhere but iOS.
 */
export function useImmersiveChrome(on: boolean) {
  useEffect(() => {
    setImmersive(on);
  }, [on]);

  // Leaving the player for good must not leave the bar hidden.
  useEffect(() => () => setImmersive(false), []);
}
