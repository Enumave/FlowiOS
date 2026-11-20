 **A privacy-respecting YouTube and YouTube Music client with a native, fully local recommendation engine.**

  FlowiOS is the my personal project forked from [Flow for Desktop](https://github.com/Flow-Tube/Flow-Desktop), built with Rust, Tauri, React, and TypeScript. Also a lot of Claude Coding.

  <p>
<picture><source media="(prefers-color-scheme: dark)" srcset="https://assets.flow-tube.org/v1/badges/split/tauri-dark.svg"><img alt="Built with Rust · Tauri 2" src="https://assets.flow-tube.org/v1/badges/split/tauri-light.svg" height="32"></picture>
  <a href="LICENSE"><picture><source media="(prefers-color-scheme: dark)" srcset="https://assets.flow-tube.org/v1/badges/split/license-dark.svg"><img alt="License: GPL-3.0" src="https://assets.flow-tube.org/v1/badges/split/license-light.svg" height="32"></picture></a>
  </p>

  [**Flow Desktop**](https://github.com/Flow-Tube/Flow-Desktop/releases) · [**Android app**](https://github.com/Flow-Tube/Flow) · [**Community**](https://www.reddit.com/r/Flow_Official/) · [**Support development**](#support--donations)
</div>

> FlowiOS is under active development and is not related to the main developer and the main project **THIS IS A COMMUNITY FORK**. Features and storage formats may change frequently. Do approach this fork with your own risk as this is again, **a personal test project** fully vibecoded by Claude AI and a random guy on the internet using his own free account.

**I do not receive any donations or funds doing this, i am just a single person that wanted to use this app on my device, please do donate to the [Main Developer](https://github.com/Flow-Tube#support-the-development)**

---

## Features

- Native video playback with quality and codec selection, SABR/DASH/HLS support, chapters, subtitles, playback speed, queues, mini-player, and Picture-in-Picture.
- YouTube Music home, search, artists, albums, playlists, queue management, synchronized lyrics, repeat, shuffle, and equalizer controls.
- A dedicated Shorts feed with comments, descriptions, saved Shorts, looping, auto-next, and timed scrolling modes.
- Local subscriptions, playlists, Watch Later, likes, albums, video and music history, Continue Watching, and regional Explore feeds.
- Channel pages with videos, Shorts, playlists, community posts, comments, and live chat support.
- SponsorBlock, DeArrow, Return YouTube Dislike, and Discord Rich Presence integrations.
- Imports from Flow backups, Google Takeout, NewPipe, LibreTube, FreeTube, and OPML.

### FlowNeuro

FlowNeuro is Flow's native local recommendation engine. It learns from watches, skips, likes, dislikes, searches, topic preferences, and creator affinity, and ranks content on your device without sending a recommendation profile to a Flow server.

The Control Center lets you inspect topic weights, time-based patterns, channel memory, learning activity, and blocked content. You can export, import, reset, or temporarily pause learning with Deep Flow mode.

---

## Privacy and security

- No Google account is required, and Flow contains no advertising or analytics SDK.
- History, settings, library data, and recommendation state are stored locally in SQLite.
- Tauri permissions are restricted to the main window and the OS, dialog, and external-link capabilities the app uses.
- A strict Content Security Policy blocks arbitrary scripts, frames, objects, and remote application code.
- Rust validates search terms, video IDs, channel IDs, browse IDs, and continuation tokens before network requests.
- Media is relayed through a tokenized loopback-only proxy instead of exposing a public local server.
- BotGuard and PO-token handling run through a native hidden WebView, with a packaged Node script retained only as a compatibility fallback.

Flow still contacts YouTube and optional services such as SponsorBlock, DeArrow, Return YouTube Dislike, and configured lyrics providers when their features are used.

---

## Releases and Downloads

- For obvious reasons there will be no .ipa provided.
- You could fork this and build it on yourself


<a id="support--donations"></a>
## Support & donations to the Main Dev

Flow is free and open-source software maintained by an independent developer. Patreon supports card, PayPal, Apple Pay, recurring support, and one-time tips.

<a href="https://opencollective.com/flow-tube"><picture><source media="(prefers-color-scheme: dark)" srcset="https://assets.flow-tube.org/v1/badges/pill/support-opencollective-dark.svg"><img alt="Support Flow on Open Collective" src="https://assets.flow-tube.org/v1/badges/pill/support-opencollective-light.svg" height="60"></picture></a>
<a href="https://patreon.com/A_EDev"><picture><source media="(prefers-color-scheme: dark)" srcset="https://assets.flow-tube.org/v1/badges/pill/support-patreon-tonal-dark.svg"><img alt="Support Flow on Patreon" src="https://assets.flow-tube.org/v1/badges/pill/support-patreon-tonal-light.svg" height="60"></picture></a>

You can also donate directly with crypto. Scan a QR code using a compatible wallet, or click it where custom wallet links are supported. The address and network are printed below every code — always verify both before sending.

<table>
  <tr>
    <td align="center">
      <strong>USDT · TRC20</strong><br><br>
      <a href="tron:TRz7VDrTWwCLCfQmYBEJakqcZgbFNWfUMP"><img src="Assets/donations/usdt-trc20.png" alt="USDT TRC20 donation QR code" width="170"></a><br><br>
      <code>TRz7VDrTWwCLCfQmYBEJakqcZgbFNWfUMP</code>
    </td>
    <td align="center">
      <strong>Bitcoin · BTC</strong><br><br>
      <a href="bitcoin:bc1qgmkkxxvzvsymtpfazqfl93jw6k4jgy0xmrtnv8?label=Flow%20Development"><img src="Assets/donations/bitcoin.png" alt="Bitcoin donation QR code" width="170"></a><br><br>
      <code>bc1qgmkkxxvzvsymtpfazqfl93jw6k4jgy0xmrtnv8</code>
    </td>
    <td align="center">
      <strong>Ethereum · ERC-20</strong><br><br>
      <a href="ethereum:0xfbac6f464fec7fe458e318971a42ba45b305b70e"><img src="Assets/donations/ethereum.png" alt="Ethereum donation QR code" width="170"></a><br><br>
      <code>0xfbac6f464fec7fe458e318971a42ba45b305b70e</code>
    </td>
  </tr>
  <tr>
    <td align="center" colspan="2">
      <strong>Solana · SOL</strong><br><br>
      <a href="solana:7b3SLgiVPb8qQUvERSPGRWoFoiGEDvkFuY98M1GEngug?label=Flow%20Development"><img src="Assets/donations/solana.png" alt="Solana donation QR code" width="170"></a><br><br>
      <code>7b3SLgiVPb8qQUvERSPGRWoFoiGEDvkFuY98M1GEngug</code>
    </td>
    <td align="center">
      <strong>Monero · XMR</strong><br><br>
      <a href="monero:8AgaxZnpEvT8VXJpczpL7BQejwSEw97saJmKYqq4zKErbe9bkYSwUhJ813msPPbdYhF11oz4N7tfEj4Zi6k27fKD83ca1if"><img src="Assets/donations/monero.png" alt="Monero donation QR code" width="170"></a><br><br>
      <code>8AgaxZnpEvT8VXJpczpL7BQejwSEw97saJmKYqq4zKErbe9bkYSwUhJ813msPPbdYhF11oz4N7tfEj4Zi6k27fKD83ca1if</code>
    </td>
  </tr>
</table>

Wallet URI support varies between wallet applications. Bitcoin, Ethereum, Solana, and Monero QR codes use their standard payment URI formats; the TRC20 code uses a Tron URI and may fall back to displaying the address in wallets that do not register the scheme.

---

## License

Flow Desktop is free software licensed under the [GNU General Public License v3.0](LICENSE).

This license requires that any project using Flow's source code, including the FlowNeuro engine, must also be released as open source under GPLv3. It may not be used in a proprietary or closed-source application.

Copyright © 2025–2026 A-EDev

---

## Star History

<a href="https://github.com/Flow-Tube/Flow-Desktop/stargazers">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://assets.flow-tube.org/v1/stars/stars-flow-desktop-dark.svg">
    <img alt="Star history of Flow Desktop" src="https://assets.flow-tube.org/v1/stars/stars-flow-desktop-light.svg" width="100%">
  </picture>
</a>

---

<div align="center">
  <a href="https://github.com/Flow-Tube"><picture><source media="(prefers-color-scheme: dark)" srcset="https://assets.flow-tube.org/v1/badges/pill/part-of-flow-dark.svg"><img alt="Part of the Flow ecosystem" src="https://assets.flow-tube.org/v1/badges/pill/part-of-flow-light.svg" height="60"></picture></a>
</div>
