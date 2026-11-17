#!/usr/bin/env python3
"""Make Flow Desktop's Rust code compile for iOS.

Run from the repository root, before `tauri ios build`. Every edit is an exact-text
replacement and the script stops with an error if a snippet is not found, so a changed
upstream file shows up as a clear failure instead of a silent miss.
"""
import os
import sys

SRC = "src-tauri/src"


def path(rel):
    return os.path.join(SRC, rel)


def read(rel):
    with open(path(rel), encoding="utf-8") as f:
        return f.read()


def write(rel, text):
    with open(path(rel), "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def replace(rel, old, new, count=1):
    text = read(rel)
    found = text.count(old)
    if found != count:
        sys.exit(f"ios-port: {rel}: expected {count} match(es), found {found} for:\n{old}")
    write(rel, text.replace(old, new))
    print(f"patched {rel}")


# ---------------------------------------------------------------------------
# New file: stand-ins for window calls that only exist on desktop.
# ---------------------------------------------------------------------------
write(
    "mobile_compat.rs",
    r'''//! iOS stand-ins for window calls that Tauri only provides on desktop. They do nothing, which
//! is right for an iPad: there is no taskbar, minimizing or always-on-top. Inherent methods win
//! over trait methods, so desktop builds never use these.
#![allow(dead_code, unused_imports)]

use tauri::{Manager, Runtime, WebviewWindow, WebviewWindowBuilder};

#[derive(Debug, Clone, Copy)]
pub enum ProgressBarStatus {
    None,
    Normal,
    Indeterminate,
    Paused,
    Error,
}

#[derive(Debug, Clone, Default)]
pub struct ProgressBarState {
    pub status: Option<ProgressBarStatus>,
    pub progress: Option<u64>,
}

pub trait WindowCompat {
    fn unminimize(&self) -> tauri::Result<()>;
    fn set_always_on_top(&self, on_top: bool) -> tauri::Result<()>;
}

impl<R: Runtime> WindowCompat for WebviewWindow<R> {
    fn unminimize(&self) -> tauri::Result<()> {
        Ok(())
    }

    fn set_always_on_top(&self, _on_top: bool) -> tauri::Result<()> {
        Ok(())
    }
}

pub trait BuilderCompat: Sized {
    fn skip_taskbar(self, _v: bool) -> Self { self }
    fn maximizable(self, _v: bool) -> Self { self }
    fn minimizable(self, _v: bool) -> Self { self }
    fn closable(self, _v: bool) -> Self { self }
    fn focused(self, _v: bool) -> Self { self }
    fn decorations(self, _v: bool) -> Self { self }
    fn always_on_top(self, _v: bool) -> Self { self }
    fn always_on_bottom(self, _v: bool) -> Self { self }
    fn shadow(self, _v: bool) -> Self { self }
    fn content_protected(self, _v: bool) -> Self { self }
    fn general_autofill_enabled(self, _v: bool) -> Self { self }
    fn maximized(self, _v: bool) -> Self { self }
    fn fullscreen(self, _v: bool) -> Self { self }
}

impl<'a, R: Runtime, M: Manager<R>> BuilderCompat for WebviewWindowBuilder<'a, R, M> {}
''',
)

# ---------------------------------------------------------------------------
# New file: the tray does not exist on iOS.
# ---------------------------------------------------------------------------
write(
    "services/music_tray_mobile.rs",
    r'''//! iOS has no system tray, so this keeps the same names and does nothing.
#![allow(dead_code)]

use tauri::AppHandle;

#[derive(Debug, Clone, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TrayLabels {
    pub play: String,
    pub pause: String,
    pub previous: String,
    pub next: String,
    pub show: String,
    pub continue_watching: String,
}

#[derive(Debug, Clone, serde::Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TrayUpdate {
    pub now_playing: String,
    pub has_track: bool,
    pub playing: bool,
    pub continue_watching: Option<String>,
    pub labels: TrayLabels,
}

#[derive(Default)]
pub struct MusicTray;

impl MusicTray {
    pub fn supported() -> bool {
        false
    }

    pub fn update(&self, _app: &AppHandle, _window: &str, _update: TrayUpdate) -> tauri::Result<()> {
        Ok(())
    }

    pub fn show_latest(&self, _app: &AppHandle) -> tauri::Result<()> {
        Ok(())
    }

    pub fn hide(&self, _app: &AppHandle) -> tauri::Result<()> {
        Ok(())
    }
}
''',
)

# ---------------------------------------------------------------------------
# services/mod.rs: pick the tray implementation per platform.
# ---------------------------------------------------------------------------
replace(
    "services/mod.rs",
    "pub mod music_tray;\n",
    '#[cfg(desktop)]\npub mod music_tray;\n'
    '#[cfg(mobile)]\n#[path = "music_tray_mobile.rs"]\npub mod music_tray;\n',
)

# ---------------------------------------------------------------------------
# lib.rs: register the compat module and bring it into scope.
# ---------------------------------------------------------------------------
replace(
    "lib.rs",
    "pub mod models;\n",
    "#[cfg(mobile)]\nmod mobile_compat;\npub mod models;\n",
)
replace(
    "lib.rs",
    "use std::sync::Arc;\nuse tauri::Manager;\n",
    "use std::sync::Arc;\n#[cfg(mobile)]\n#[allow(unused_imports)]\nuse mobile_compat::{BuilderCompat, WindowCompat};\nuse tauri::Manager;\n",
)

# ---------------------------------------------------------------------------
# Files that call unminimize / always-on-top / skip_taskbar / maximizable.
# ---------------------------------------------------------------------------
COMPAT_USE = (
    "#[cfg(mobile)]\n#[allow(unused_imports)]\n"
    "use crate::mobile_compat::{BuilderCompat, WindowCompat};\n"
)

replace("commands/pip.rs", "use crate::errors::{AppError, ErrorResponse};\n",
        COMPAT_USE + "use crate::errors::{AppError, ErrorResponse};\n")
replace("bridge/mod.rs", "use crate::security::validation::{validate_playlist_id, validate_video_id};\n",
        COMPAT_USE + "use crate::security::validation::{validate_playlist_id, validate_video_id};\n")
replace("services/shell_pages.rs", "use crate::security::validation::is_openable_link;\n",
        COMPAT_USE + "use crate::security::validation::is_openable_link;\n")
replace("api/innertube/core/hidden_webview.rs", "use tracing::{debug, warn};\n",
        "use tracing::{debug, warn};\n\n" + COMPAT_USE)

# ---------------------------------------------------------------------------
# commands/tray.rs: no taskbar progress or badge on iOS.
# ---------------------------------------------------------------------------
replace(
    "commands/tray.rs",
    "use tauri::window::{ProgressBarState, ProgressBarStatus};\n",
    "#[cfg(desktop)]\nuse tauri::window::{ProgressBarState, ProgressBarStatus};\n",
)
replace(
    "commands/tray.rs",
    "/// Show download progress on the taskbar or Dock icon.",
    '''#[cfg(mobile)]
#[tauri::command]
pub async fn set_download_progress(
    _app: AppHandle,
    _percent: Option<u64>,
    _count: u32,
    _paused: bool,
) -> Result<(), ErrorResponse> {
    Ok(())
}

/// Show download progress on the taskbar or Dock icon.''',
)
replace(
    "commands/tray.rs",
    "#[tauri::command]\npub async fn set_download_progress(\n    app: AppHandle,",
    "#[cfg(desktop)]\n#[tauri::command]\npub async fn set_download_progress(\n    app: AppHandle,",
)

# ---------------------------------------------------------------------------
# services/media_keys.rs: the global shortcut plugin is desktop only.
# ---------------------------------------------------------------------------
replace(
    "services/media_keys.rs",
    "use tauri::{AppHandle, Emitter, Listener, Manager, Wry};\n"
    "use tauri_plugin_global_shortcut::{\n"
    "    Builder, Code, GlobalShortcut, GlobalShortcutExt, Shortcut, ShortcutState,\n"
    "};\n",
    "use tauri::{AppHandle, Emitter, Listener, Manager};\n"
    "#[cfg(desktop)]\nuse tauri::Wry;\n"
    "#[cfg(desktop)]\nuse tauri_plugin_global_shortcut::{\n"
    "    Builder, Code, GlobalShortcut, GlobalShortcutExt, Shortcut, ShortcutState,\n"
    "};\n",
)
replace(
    "services/media_keys.rs",
    "// The X11 backend has no key for the combined play/pause media code; XF86AudioPlay is that key.\n"
    "#[cfg(target_os = \"linux\")]\nconst PLAY_PAUSE: Code = Code::MediaPlay;\n"
    "#[cfg(not(target_os = \"linux\"))]\nconst PLAY_PAUSE: Code = Code::MediaPlayPause;\n",
    "// The X11 backend has no key for the combined play/pause media code; XF86AudioPlay is that key.\n"
    "#[cfg(target_os = \"linux\")]\nconst PLAY_PAUSE: Code = Code::MediaPlay;\n"
    "#[cfg(all(desktop, not(target_os = \"linux\")))]\nconst PLAY_PAUSE: Code = Code::MediaPlayPause;\n",
)
replace(
    "services/media_keys.rs",
    "fn command_for(key: Code) -> Option<&'static str> {",
    "#[cfg(desktop)]\nfn command_for(key: Code) -> Option<&'static str> {",
)
replace(
    "services/media_keys.rs",
    "    #[cfg(not(target_os = \"linux\"))]\n    {\n        true\n    }\n}",
    "    #[cfg(all(desktop, not(target_os = \"linux\")))]\n    {\n        true\n    }\n    #[cfg(mobile)]\n    {\n        false\n    }\n}",
)
replace(
    "services/media_keys.rs",
    "/// Takes or releases the keys. Runs on the main thread, as macOS needs for registering them.\n"
    "pub fn set_keys_enabled(",
    "/// Global media keys do not exist on iOS.\n"
    "#[cfg(mobile)]\n"
    "pub fn set_keys_enabled(_app: &AppHandle, _enabled: bool) -> Result<(), String> {\n"
    "    Err(\"global media keys are not available on iOS\".to_string())\n"
    "}\n\n"
    "/// Takes or releases the keys. Runs on the main thread, as macOS needs for registering them.\n"
    "#[cfg(desktop)]\n"
    "pub fn set_keys_enabled(",
)

# ---------------------------------------------------------------------------
# commands/local_media.rs: no folder picker or recycle bin on iOS.
# ---------------------------------------------------------------------------
replace(
    "commands/local_media.rs",
    "/// Asks the person for a folder and adds it. `None` when they cancel the dialog.\n"
    "#[tauri::command]\npub async fn local_media_add_folder(",
    "/// Folder picking is not available on iOS, so this reads as the person cancelling.\n"
    "#[cfg(mobile)]\n#[tauri::command]\n"
    "pub async fn local_media_add_folder(\n"
    "    _title: String,\n    _exclude: bool,\n) -> Result<Option<String>, ErrorResponse> {\n"
    "    Ok(None)\n}\n\n"
    "/// Asks the person for a folder and adds it. `None` when they cancel the dialog.\n"
    "#[cfg(desktop)]\n#[tauri::command]\npub async fn local_media_add_folder(",
)
replace(
    "commands/local_media.rs",
    "fn move_to_trash(path: &Path) -> Result<(), trash::Error> {",
    "#[cfg(mobile)]\n"
    "fn move_to_trash(_path: &Path) -> Result<(), std::io::Error> {\n"
    "    Err(std::io::Error::new(\n"
    "        std::io::ErrorKind::Unsupported,\n"
    "        \"there is no trash on iOS\",\n"
    "    ))\n}\n\n"
    "#[cfg(desktop)]\n"
    "fn move_to_trash(path: &Path) -> Result<(), trash::Error> {",
)

print("ios-port: done")
