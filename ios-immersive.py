#!/usr/bin/env python3
"""Hide the iPad's home indicator (the white bar at the bottom) and status bar during fullscreen video,
and give the fullscreen brightness and volume swipes their native side.

Run from the repository root after ios-port.py, ios-ui.py and ios-adaptive.py. The native part is
src-tauri/src/ios_chrome.rs and the frontend part is src/lib/immersiveChrome.ts; this only wires the
Rust side into the iOS build. The status bar is hidden with the application-level call, which needs
the plist's view-controller-based status bar appearance to stay off (ios-ui.py sets that). Like the
other scripts it stops with an error if a snippet is not found. To drop the feature, remove this
script's step from the workflow: nothing else depends on it.
"""
import sys


def replace(rel, old, new):
    with open(rel, encoding="utf-8") as f:
        text = f.read()
    found = text.count(old)
    if found != 1:
        sys.exit(f"ios-immersive: {rel}: expected 1 match, found {found} for:\n{old}")
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(old, new))
    print(f"patched {rel}")


replace(
    "src-tauri/src/lib.rs",
    "#[cfg(mobile)]\nmod mobile_compat;\n",
    '#[cfg(mobile)]\nmod mobile_compat;\n#[cfg(target_os = "ios")]\nmod ios_chrome;\n',
)
replace(
    "src-tauri/src/lib.rs",
    "        .invoke_handler(tauri::generate_handler![\n",
    "        .invoke_handler(tauri::generate_handler![\n"
    "            ios_chrome::set_immersive,\n"
    "            ios_chrome::begin_screen_levels,\n"
    "            ios_chrome::end_screen_levels,\n"
    "            ios_chrome::set_screen_brightness,\n"
    "            ios_chrome::set_system_volume,\n",
)
replace(
    "src-tauri/Cargo.toml",
    'apple-native-keyring-store = { version = "1", features = ["protected"] }\n',
    'apple-native-keyring-store = { version = "1", features = ["protected"] }\n'
    "# The home indicator preference (src/ios_chrome.rs). Already in the tree through tauri.\n"
    'objc2 = "0.6"\n',
)
