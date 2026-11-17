#!/usr/bin/env python3
"""Make Flow Desktop's interface behave like an iPad app.

Run from the repository root, before `pnpm build` / `tauri ios build`. It hides the custom
desktop title bar (minimize / maximize / close), skips the desktop window-control calls, and
keeps the page clear of the iPad status bar and home indicator.
"""
import sys


def replace(rel, old, new):
    with open(rel, encoding="utf-8") as f:
        text = f.read()
    found = text.count(old)
    if found != 1:
        sys.exit(f"ios-ui: {rel}: expected 1 match, found {found} for:\n{old}")
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.replace(old, new))
    print(f"patched {rel}")


# 1. One flag that says "this is a phone or tablet".
replace(
    "src/lib/platform.ts",
    "// Native macOS chrome sits outside the webview's content area.\n"
    "export const APP_TITLEBAR_HEIGHT = IS_MACOS_RUNTIME ? 0 : 32;",
    "export const IS_MOBILE_RUNTIME = (() => {\n"
    "  try {\n"
    "    const os = platform();\n"
    "    return os === \"ios\" || os === \"android\";\n"
    "  } catch {\n"
    "    return false;\n"
    "  }\n"
    "})();\n"
    "\n"
    "// Native macOS chrome sits outside the webview's content area, and phones have no title bar.\n"
    "export const APP_TITLEBAR_HEIGHT = IS_MACOS_RUNTIME || IS_MOBILE_RUNTIME ? 0 : 32;",
)

# 2. No custom title bar with window buttons.
replace(
    "src/components/layout/TitleBar.tsx",
    'import { IS_MACOS_RUNTIME } from "../../lib/platform";',
    'import { IS_MACOS_RUNTIME, IS_MOBILE_RUNTIME } from "../../lib/platform";',
)
replace(
    "src/components/layout/TitleBar.tsx",
    "  if (IS_MACOS_RUNTIME) return null;",
    "  if (IS_MACOS_RUNTIME || IS_MOBILE_RUNTIME) return null;",
)

# 3. Do not watch desktop window state (maximized / resized) on iOS.
replace(
    "src/lib/useWindowControls.ts",
    'import { IS_MACOS_RUNTIME } from "./platform";',
    'import { IS_MACOS_RUNTIME, IS_MOBILE_RUNTIME } from "./platform";',
)
replace(
    "src/lib/useWindowControls.ts",
    "    if (IS_MACOS_RUNTIME) return;",
    "    if (IS_MACOS_RUNTIME || IS_MOBILE_RUNTIME) return;",
)

# 4. Keep content out from under the status bar and home indicator.
replace(
    "src/App.tsx",
    'import { APP_TITLEBAR_HEIGHT } from "./lib/platform";',
    'import { APP_TITLEBAR_HEIGHT, IS_MOBILE_RUNTIME } from "./lib/platform";',
)
replace(
    "src/App.tsx",
    'const windowLayoutStyle = { "--app-titlebar-height": `${APP_TITLEBAR_HEIGHT}px` } as CSSProperties;',
    "const windowLayoutStyle = {\n"
    '  "--app-titlebar-height": `${APP_TITLEBAR_HEIGHT}px`,\n'
    "  ...(IS_MOBILE_RUNTIME\n"
    "    ? {\n"
    '        paddingTop: "env(safe-area-inset-top, 0px)",\n'
    '        paddingBottom: "env(safe-area-inset-bottom, 0px)",\n'
    "      }\n"
    "    : {}),\n"
    "} as CSSProperties;",
)
replace(
    "index.html",
    '<meta name="viewport" content="width=device-width, initial-scale=1.0" />',
    '<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />',
)
# 7. App-wide touch behaviour, as on Android: hold for the menu a right click opens, swipe in from
#    the left edge to go back, pull a page down to refresh it (Home and Subscriptions), and keep
#    hover-only buttons visible. The logic lives in src/lib/touchNavigation.ts.
replace(
    "src/App.tsx",
    'import { useTabHistoryShortcuts } from "./lib/tabs/useTabHistoryShortcuts";\n',
    'import { useTabHistoryShortcuts } from "./lib/tabs/useTabHistoryShortcuts";\n'
    'import { useTouchNavigation } from "./lib/touchNavigation";\n',
)
replace(
    "src/App.tsx",
    "  useTabHistoryShortcuts();\n",
    "  useTabHistoryShortcuts();\n  useTouchNavigation();\n",
)
replace(
    "src/pages/Home.tsx",
    'import { RefreshCw } from "lucide-react";\n',
    'import { RefreshCw } from "lucide-react";\n'
    'import { registerPullRefresh } from "../lib/touchNavigation";\n',
)
replace(
    "src/pages/Home.tsx",
    "    return () => window.removeEventListener(HOME_RESELECTED_EVENT, handleReselected);\n"
    "  }, [scrollContainer, refreshOnReselect, chipFeed, reloadChip, handleRefresh]);\n",
    "    return () => window.removeEventListener(HOME_RESELECTED_EVENT, handleReselected);\n"
    "  }, [scrollContainer, refreshOnReselect, chipFeed, reloadChip, handleRefresh]);\n"
    "\n"
    "  useEffect(\n"
    "    () =>\n"
    "      registerPullRefresh(() => {\n"
    "        if (chipFeed) reloadChip();\n"
    "        else handleRefresh();\n"
    "      }),\n"
    "    [chipFeed, reloadChip, handleRefresh],\n"
    "  );\n",
)
replace(
    "src/pages/Subscriptions.tsx",
    'import { ChevronDown, ChevronUp, ListChecks, Loader2, Pencil, Plus, RefreshCw, Trash2, Upload, User } from "lucide-react";\n',
    'import { ChevronDown, ChevronUp, ListChecks, Loader2, Pencil, Plus, RefreshCw, Trash2, Upload, User } from "lucide-react";\n'
    'import { registerPullRefresh } from "../lib/touchNavigation";\n',
)
replace(
    "src/pages/Subscriptions.tsx",
    "  const channelDetails = useSubscriptionChannelDetails(subscriptions);\n",
    "  useEffect(() => registerPullRefresh(() => void refreshFeed()), [refreshFeed]);\n"
    "  const channelDetails = useSubscriptionChannelDetails(subscriptions);\n",
)
with open("src/App.css", "a", encoding="utf-8", newline="\n") as css:
    css.write(
        "\n/* Touch screens have no hover, so controls that only appear on hover stay visible. */\n"
        "@media (hover: none) {\n"
        '  [class*="group-hover:opacity-100"] {\n'
        "    opacity: 1 !important;\n"
        "  }\n"
        "  body {\n"
        "    -webkit-touch-callout: none;\n"
        "  }\n"
        "}\n"
    )
print("patched src/App.css")
print("ios-ui: done")
