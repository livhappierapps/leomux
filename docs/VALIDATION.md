# Validation — November 6, 2026 (America/Chicago, CST)

Run locally on the authorized box, not the Samsung/iPhone. No EAS, APK, AAB, IPA,
store upload or live paid API call was run.

| Check | Result |
|---|---|
| `pnpm install --ignore-scripts` | PASS, lockfile generated; pnpm 10.34.6 |
| `pnpm typecheck` | PASS (`tsc --noEmit`, strict TypeScript) |
| `pnpm test:transport` | PASS, 3/3, no skips |
| `python3 -m unittest discover -s termux/tests -v` | PASS, 25/25, no skips; Python 3.13.5 |
| Python bytecode syntax compilation | PASS |
| `CI=1 pnpm exec expo install --check` | PASS, dependencies match Expo SDK 54 |
| `pnpm exec expo config --type public` | PASS, LeoMux ID/settings, no inherited EAS project |
| Expo autolinking resolve (Android) | PASS, `leo-approval` Kotlin module discovered |
| RN autolinking config (Android) | PASS, `react-native-tcp-socket` native dependency discovered |
| `CI=1 pnpm exec expo export --platform android` | PASS, Metro/Hermes JS bundle exported locally (1086 modules); NOT native compilation/APK |
| Git whitespace checks / staged source hygiene | PASS before commit; only source/assets/lockfile/docs tracked |

Python tests use **real TCP loopback and real tmux on a private test socket**;
Termux:API is mocked. They cover hello-first disconnect, wrong token, loopback
bind, signed execution, unsigned/nonce/replay rejection, cwd/environment
persistence, Unicode/multiline/exit codes, deny/timeout/manual resume, critical
refusal, STOP cancellation of already-approved queued work, voice never acting as
approval, and model tool calls becoming pending proposals without execution.
API adapter requests/responses are mocked; missing configuration makes no request.

Ported risk tests include rm-rf/root/wipe tags; extra cases test quoted commands,
explicit `/system`/`/data`, shared storage and protected state. NDJSON tests cover
partial/merged reads, invalid schemas, UTF-8 split bytes and oversized complete
and incomplete frames. HMAC tests bind command hash, ID, nonce and server session.

## Not validated / remaining gates

- Native Kotlin compilation or gesture instrumentation; Android Keystore import,
  obscured-touch rejection, and a native module's UI cannot be proven by TS tests.
- Actual Samsung A17 RN TCP↔Termux connection, microphone/TTS, Android background
  restrictions, one-handed ergonomics and keyboard/layout behavior.
- Live Grok account/model, API call, reply quality, latency/cost; no real key used.
- Grok voice-call headless bridge and autonomous tool-result loop do not exist.
- iOS is a non-executing layout target, not a functioning Termux app.
- Arbitrary-shell confinement/strong process attestation: see SECURITY.md. Do not
  treat regex critical denial or HMAC as a full security sandbox/OS attestation.

Next: authorize a native Android development build, use the device checklist,
then independent security review before real workflows. GitHub CI is configured
for the same Python/TS checks; remote CI status is separate from these local runs.
