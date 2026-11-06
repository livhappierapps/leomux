# LeoMux — Android scaffold

Voice-first EdenMux-style terminal + floating Leo conversation pane, backed by
Commander's Python/NDJSON/risk/tmux brain in **Termux on the same Android phone**.
Target: Samsung A17. Android ID: `com.livhappierapps.leomux`.

**Status:** source scaffold, not a tested APK or a production security boundary.
No EAS build, store upload, remote tunnel, paid API request, or device change was
performed while preparing this repository. See [validation](docs/VALIDATION.md).

## What came from where

- EdenMux zip: Expo Router `app/`, `components/`, `lib/`, `assets/` layout;
  actual terminal output renderer/session tab component, Red Delicious palette,
  bundled artwork/fonts, and top-right portrait/chat-pane design. It was **not**
  treated as text-only: microphone is the default, text requires “Type instead”.
- Commander `4ac394b`: persistent `Shell` tmux runner, NDJSON framing, risk/alert
  rules, socket/approval queue architecture, CLI shape, and protocol/risk tests.
  Server approval/UI dispatch was adapted for signed native swipes rather than
  retaining the unsafe “socket token can approve anything” implementation.
- Removed: share activities/hooks, clipboard bridge, notification auto-approval
  routes, Replit, Node remote shell/database/auth/email, RevenueCat/paywalls/OTA.
  No old Android app, installer, generated bootstrap, credentials or handoff zip.

## Architecture

```text
Android LeoMux (Expo SDK 54 / React Native)
  terminal output + display tabs + TOP-RIGHT floating Leo pane
  voice by default → voice.listen; typing fallback → chat
  native review + swipe/hold/release → Keystore HMAC signature
         │ direct react-native-tcp-socket (NOT WebSocket)
         │ hello(token) first, then NDJSON; no LAN address setting
         ▼
  127.0.0.1:8765  leo_server.py (Termux, Python stdlib)
    risk.py → critical = REFUSED, never offered for approval
    nonce + command-hash + session signature → one-command queue
         ▼
  persistent tmux session `leo` → source approved script → output/exit

  voice.listen → termux-speech-to-text → optional Grok adapter → proposed command
  replies → termux-tts-speak
```

Transport is genuine native TCP. A browser's `WebSocket` cannot talk to this
NDJSON server; no WebSocket gateway was added. Expo native autolinking resolves
`react-native-tcp-socket` and the local `modules/leo-approval` module. **Expo Go is
not supported.** JS framing is tested against split UTF-8/merged byte streams,
and Python loopback tests exercise the server. **RN↔Termux TCP on the Samsung has
not yet been device-tested.**

The terminal view mirrors command output, not an interactive VT emulator. Use
`tmux attach -t leo` in Termux for interactive programs. Extra EdenMux-style tabs
are currently **display/notes tabs**, not extra tmux shells; all commands use
`leo`. The floating pane is **inside LeoMux**, not a system-wide overlay.

## Termux setup (on the phone, not iPhone)

Install Termux **and the separate Termux:API Android app from the same trusted
source** (e.g. F-Droid/GitHub-compatible builds). Grant Termux:API microphone
access when needed. Do not root, enable RUN_COMMAND for outside apps, change
`/system`, or manually edit `/data`. Work only from Termux's private `$HOME`.

```sh
pkg install tmux python termux-api git
cd "$HOME"
git clone https://github.com/livhappierapps/leomux.git
cd leomux
python termux/leo_server.py
```

In a second Termux session:

```sh
cd "$HOME/leomux"
python termux/leo.py pair
```

This **explicit local pairing command** displays two different private values:
1. socket token → LeoMux ⚙ → Socket token (saved with Expo SecureStore);
2. approval key → Approval key (imported into non-exportable Android Keystore).

Enter them only in your own LeoMux app; never send to Leo, chat, an issue, a
screenshot or this public repository. The app clears input fields after pairing.
Do not use the clipboard as a command/control bridge. The server's private home
is `~/.leomux` (0700); token/key and command scripts are 0600. Normal server logs
never print pairing values. Reinstalling LeoMux requires pairing again.

Tap **Save privately & connect**. Both processes must be on the same Android
phone: `127.0.0.1` is that phone, not a box, laptop, iPhone or remote API.

### First safe test (no paid API required)

1. In LeoMux's bottom manual input, propose `pwd` (not the chat text fallback).
2. Review the full command in the native protected approval area.
3. Start on the left 20%, swipe right past 85%, hold 600 ms, then release.
4. Confirm output/exit in the terminal. Nothing runs on a tap or spoken “yes”.
5. Try `cd "$HOME"` then `pwd` to verify persistent cwd. Exports persist too.
6. Deny a proposal: pending/queued work is discarded and the session pauses.
   Use Resume explicitly; no failed or cancelled command is retried.
7. Test STOP with a harmless long-running command: it kills **only tmux `leo`**,
   clears pending/queued work, and pauses. It sacrifices that shell's cwd/env.
   STOP is intentionally immediate (tap), unlike approval. Do not make an
   emergency stop harder to reach. The ↕ button moves the pane down for a thumb.

Critical command strings such as recursive forced deletion, disk wipes,
`su`/`sudo`/`tsu`/`doas`, explicit `/system` or `/data`, shared storage and protected
Leo files are refused **before** an approval can be created. The risk scanner is
heuristic, not a shell parser or a filesystem isolation system. Read
[SECURITY.md](SECURITY.md) before enabling real workflows.

### Voice + optional Grok conversation

- Primary implemented STT: `termux-speech-to-text` (Termux:API invokes Android's
  recognizer). Depending on the installed recognition engine it **may use the
  network**; this is not a guarantee of offline STT.
- TTS: `termux-tts-speak` via fixed subprocess arguments/stdin (never shell eval).
- `whisper.cpp` is **not implemented** in this scaffold. A local model, capture
  path and measured A17 latency would need to be added for guaranteed offline STT.
- Termux must be configured privately with **both** `XAI_API_KEY` and
  `LEO_GROK_MODEL` environment variables to use the opt-in API adapter. Choose an
  available model from your account; no guessed model is silently selected.
  Never put credentials in app config or an `EXPO_PUBLIC_*` variable. API use may
  cost money; the scaffold does not make any live request during tests/setup.
- Talk sends recognized text to Grok; text fallback sends typed conversation.
  Grok tool calls only create proposals; they never approve or directly execute.
  TTS reads replies. There are no automatic API retries.
- Shell output is displayed locally and **not automatically uploaded to Grok**.
  The continuous tool-result/conversation loop is intentionally not implemented;
  adding it needs a clear consent/redaction design. This is not a fully
  autonomous agent. API history is memory-only and per socket connection.

### Headless mode (honest limitations)

```sh
python termux/leo_server.py --headless
# Same server and socket as UI mode; no Android UI is required to listen.
python termux/leo.py status
python termux/leo.py watch
python termux/leo.py propose 'pwd' --reason 'local headless test'
```

LeoMux's **Headless** button disconnects/hides the UI client; close the app and
leave the Termux process running. It does not launch a hidden Expo service, keep
JS alive, auto-start Termux, or grant automatic approvals. Without an active
paired approval view, proposals time out and pause. Already-approved work may
finish when the app backgrounds; use STOP first if you want it stopped.

**A Grok Android voice call cannot access this localhost socket by itself.** A
future dedicated on-device tool/voice bridge or user-authorized outbound relay
would need to implement the authenticated protocol while preserving a separate
human approval channel. No such relay/tunnel/voice-call bridge exists here. Do
not expose port 8765 on the LAN or internet to work around this. No zero-approval
headless execution mode is included.

For Android background reliability, optionally use `termux-wake-lock` and the
phone's per-app battery settings. This repo does not change those settings or
include an Android foreground service. Android may still kill Termux; test on the
A17. Mic capture may bring Android recognition UI forward; approval only works
when LeoMux has focus. The connection stays open during an initiated voice request while the recognizer
has focus; otherwise backgrounding disconnects the UI. Reconnect explicitly if
Android kills it. This behavior needs a real-device check.

## Development (pnpm)

```sh
pnpm install --frozen-lockfile
pnpm typecheck
pnpm test:transport
python3 -m unittest discover -s termux/tests -v
# Native Android development build later, when authorized:
# pnpm android
```

`pnpm android` would compile/install a development build and needs Android build
tools/device; it was **not run** for this handoff. A fresh `eas.json` contains development/preview APK profiles only. No EAS
project ID, account link, build automation or submission config is carried over
from EdenMux; a future build still needs explicit approval and project setup.

iOS bundle identity is reserved as `com.livhappierapps.leomux`, but iPhone 13
cannot host Termux and this Android-only approval module is unavailable there.
The iOS UI is a non-executing preview, not a functional iOS promise. A remote
companion architecture would be a separate, explicitly secured project.

## Layout / protocol

```text
app/                       Expo Router layout + terminal screen
components/                inherited output/tabs, LeoPanel, pairing, input
lib/                       TCP client, bounded NDJSON, controller, palette
modules/leo-approval/       native Android guarded swipe + Keystore HMAC
assets/                    EdenMux artwork (not final Leo branding)
termux/                    server/protocol/risk/runner/voice/Grok/CLI + tests
docs/                      validation, provenance, device checklist
PROTOCOL.md                message types + canonical approval bytes
SECURITY.md                threat model and explicit non-guarantees
```

[Protocol v2](PROTOCOL.md) deliberately rejects Commander's old unsigned approve
messages. Nothing else should be listening on 8765; stop an old Commander server
manually before running LeoMux. Do not run two approval servers against `leo`.
