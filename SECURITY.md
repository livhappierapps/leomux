# Security and safety boundaries (scaffold, not audited)

## Enforced in code

- Socket hard-bound to 127.0.0.1, hello-first secret auth or disconnect. Localhost
  is **not private to an Android process**; all installed apps can try connecting.
- Two independent per-install secrets. Possessing the socket token alone cannot
  approve a command. Explicit local pairing required, never wire enrollment.
- Fresh per-command nonce, exact command SHA256, consumed pending state, deadline
  and fresh server-session ID; HMAC checked under the decision lock.
- Native Android approval view rejects full/partial obscured touch flags,
  multi-touch, cancelled gestures, focus loss and snapshot changes. It displays
  the command it hashes. No tap, accessibility click, voice message or JS-facing
  signing API can directly generate a signature. Swipe ≥85%, hold ≥600 ms, release.
- App window uses FLAG_SECURE and requests hiding app overlays on Android 12+.
  Android permissions are INTERNET + HIDE_OVERLAY_WINDOWS, not SYSTEM_ALERT_WINDOW,
  storage access, root, shell privileges or Termux RUN_COMMAND.
- Approval HMAC key imported into AndroidKeyStore and not exportable afterward;
  socket token in SecureStore. Pairing values necessarily pass briefly through
  the app's input/JS memory during manual enrollment, then fields are cleared.
- Critical risk commands are refused at proposal and again before execution,
  including root tools, rm recursive+force variants, disk wipes and explicit
  `/system`, `/data` paths. Shared-storage and protected Leo state references are
  also critical. Normal Termux code uses `$HOME`/`$PREFIX`, not hard-coded `/data`.
- No critical-risk override; no notification/CLI approve fallback; no automatic
  retries. Deny/expiry/pause clear pending and queued work. STOP kills only `leo`,
  invalidates even dequeued work with an epoch/gate, and requires manual resume.
- Commands source into one persistent bash session. PTY stdout is untrusted data.
  It is not sent back into chat as instructions or uploaded automatically.
- Server metadata audit contains event/ID/rating, no command/output/token/key.
  `pty.log` and command scripts **do contain local command/output data**; keep
  `~/.leomux` private. No telemetry, email, database, payments or cloud credentials.
- Grok adapter secrets stay in Termux's environment, not the Expo bundle; runner
  subprocesses remove XAI_API_KEY/LEO_GROK_MODEL from their inherited environment.
  Do not reuse an unrelated tmux server already holding secret environment values.

## What this DOES NOT prove

**HMAC proves possession of a separate paired secret, not remote process
attestation.** On an uncompromised Android device, app UID/Keystore isolation plus
native-only gesture signing make casual socket-token theft or another overlay
insufficient. A rooted/compromised OS, injected app code, a compromised JS bundle,
malicious accessibility service/input injection, stolen pairing key, or code
running as the Termux UID is outside this scaffold's guarantee. We cannot promise
“impossible to spoof” or “fat-finger-proof”. Real-device adversarial gesture tests
and an independent review are required before relying on it.

Termux's Android UID sandbox provides the OS boundary. **Regex risk tagging is
not a secure shell sandbox**: arbitrary approved scripts/interpreters, symlinks,
variables, aliases, shell functions, downloads/package scripts and encoded code
can evade static scans. The server cannot mathematically enforce path confinement
for general-purpose bash. Do not approve a command you cannot fully inspect;
never use this scaffold for critical operations. No root is requested or enabled.
A stricter allowlist/parser or isolated execution broker is required for a strong
“private Termux files only” guarantee. Access to shared storage is not enabled by
this repo; if a user enabled it elsewhere, the OS may already allow it.

STOP ends the known tmux session; it does not guarantee termination of malicious
children that detach into other sessions or of outside programs. Persistent
cwd/env is lost on STOP/runtime-limit fallback. Manual typing directly in tmux
bypasses the proposal system and must remain Liv's trusted activity.

## Operational limits / deployment gates

1. Native Android module and TCP connection still need compile/device validation
   on A17, including obscured/partial overlay, focus loss, keyboard, rotation,
   rapid proposal replacement, accidental swipes, expiry and background process
   death. Current checks validate TS/Python, not a shipped native APK.
2. Swipe has no accessibility-click substitute (fail closed). Design a separately
   authenticated accessible approval path before claiming accessibility support.
3. The pane is an in-app view, not “draw over all apps”. No foreground service
   keeps Expo alive. Voice recognizer may foreground another app; reconnect to
   approve afterward. Recognizer privacy/offline behavior depends on Android.
4. Rotate pairing secrets offline if exposed: stop the server, privately replace
   both values with fresh 32-byte random hex, then re-pair and restart. Do not
   overwrite a running server's key files and assume its in-memory key changed.
5. Public repository: never commit ~/.leomux, tokens, .env, XAI credentials, app
   signing material or private transcripts. Any APK should disable backup, debug
   access and unsigned OTA execution; backup is disabled here and OTA omitted.
6. Grok voice-call→headless connection and consented/redacted tool-result feedback
   are not implemented. Do not expose the local socket or grant auto-approval as
   a shortcut. iPhone cannot run Termux.
