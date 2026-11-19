import { platform } from "@tauri-apps/plugin-os";

/**
 * Whether the phone and tablet layouts ported from Flow for Android are in use: on iOS and
 * Android, or in a plain browser opened with `?adaptive=1`, to try them at any window size.
 * Desktop keeps its own layout.
 */
export const IS_ADAPTIVE_LAYOUT = (() => {
  try {
    const os = platform();
    if (os === "ios" || os === "android") return true;
  } catch {
    // Not inside Tauri.
  }
  try {
    return typeof location !== "undefined" && new URLSearchParams(location.search).get("adaptive") === "1";
  } catch {
    return false;
  }
})();
