import { invoke } from "@tauri-apps/api/core";
import { platform } from "@tauri-apps/plugin-os";

const ON_IOS = (() => {
  try {
    return platform() === "ios";
  } catch {
    return false;
  }
})();

export type ScreenLevels = {
  /** The screen brightness, 0 to 1. */
  brightness: number;
  /** The system volume, 0 to 1, or null while iOS has not produced the volume slider yet. */
  volume: number | null;
};

/**
 * Starts a brightness or volume swipe and returns where both stand (`withVolume` is for a volume
 * swipe, which is the only one that needs the volume slider). A web view cannot move either,
 * and iOS ignores `video.volume`, so these go through native code (src-tauri/src/ios_chrome.rs).
 * Null on anything but iOS, or if the native side did not answer.
 */
export async function beginScreenLevels(withVolume: boolean): Promise<ScreenLevels | null> {
  if (!ON_IOS) return null;
  try {
    const [brightness, volume] = await invoke<[number, number]>("begin_screen_levels", { withVolume });
    if (!(brightness >= 0)) return null;
    return { brightness, volume: volume >= 0 ? volume : null };
  } catch {
    return null;
  }
}

/** Ends the swipe, which lets the system volume pop-up work again. */
export function endScreenLevels() {
  if (!ON_IOS) return;
  invoke("end_screen_levels").catch(() => {
    // Only iOS builds carry this command.
  });
}

export function setScreenBrightness(value: number) {
  if (!ON_IOS) return;
  invoke("set_screen_brightness", { value }).catch(() => {});
}

export function setSystemVolume(value: number) {
  if (!ON_IOS) return;
  invoke("set_system_volume", { value }).catch(() => {});
}
