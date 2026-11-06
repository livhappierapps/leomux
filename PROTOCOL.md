# LeoMux NDJSON protocol v2

IPv4 TCP **127.0.0.1:8765 only**. UTF-8 JSON object per newline. Split/merged reads
and multibyte characters are buffered as bytes. Max frame including LF: 1 MiB.
Command length: 16,000 characters. IDs: `[A-Za-z0-9_-]{1,32}`, never reused during
one server run. Max 16 pending, bounded execution queue; duplicate IDs rejected.

The first message within five seconds **must** be:

```json
{"type":"hello","token":"<local socket token>","client":"leomux"}
```

Any wrong token or non-hello-first connection receives an error and is closed.
Success: `hello` with `ok:true`, `version:2`, `session:"leo"`, and random
`session_id`. A `client` label is descriptive only, **not** authentication of a
process. Heartbeat ping every three seconds; idle connections close after ten seconds (active voice/chat is exempt while Android
recognition temporarily owns the foreground).
Tokens/approval keys are never echoed or returned by the socket server.

## Client → server

| type | fields / behavior |
|---|---|
| `propose` | `cmd`, optional `id`, `reason`, `timeout` (1..300 seconds, default 60); risk tag, critical refusal, otherwise broadcast `proposed` |
| `decision` | `id`, `decision:"approve"`, `nonce`, `session_id`, `signature` (see below) |
| `decision` | `id`, `decision:"deny"`; deny is safe without a signature; pauses + cancels pending/queued work |
| `pause` | discard pending/queued work; don't kill current command |
| `resume` | explicit resume; never replays discarded commands |
| `stop` | emergency pause/cancel and kill known tmux `leo` session; no broad process kill |
| `status` | current status plus pending proposal snapshots for reconnecting approver |
| `ping` | `pong` |
| `chat` | `text`, optional configured Grok adapter; one in-flight voice/chat per client |
| `voice.listen` | fixed `termux-speech-to-text` call → transcript → same chat adapter |

There is no clipboard/share-sheet, arbitrary `speak` executable, unsigned approve,
notification-button approve, network-key-fetch, shell auto-approve or remote bind.

## Server → client

| type | fields |
|---|---|
| `hello` | `ok`, `version`, `session`, `session_id` |
| `proposed` | `id`, `cmd`, `reason`, `risk:{level,tags}`, `timeout`, `deadline` (Unix seconds), `nonce`, `cmd_hash`, `session_id` |
| `decision` | `id`, `decision`: approve/deny/timeout/cancelled/stopped/failed |
| `status` | `state`, `paused`, `running` (ID or null), `pending` (IDs), `session`, `session_id`, `version` |
| `output` | `id`, `stream:"pty"`, `data`; local terminal output only |
| `exit` | `id`, `code`, `summary`; failure pauses and discards queued work, never retries |
| `alert` | `level`, `msg`, optional `id` |
| `error` | `msg`, optional risk metadata; critical proposals never become pending |
| `voice` | `state`: listening/idle |
| `transcript` | `text`; conversational input, **never a command/approval** |
| `chat` | `role:"leo"`, `text` |
| `pong` | heartbeat response |

## Approval signature

The approval key is a **different** 32-byte secret from the socket token. It is
paired once locally and imported into LeoMux Android Keystore. JS exposes key
import/pairing state only, **not a sign or approve function**. The native view
shows the exact command, computes SHA256 of its UTF-8 bytes, checks it matches
`cmd_hash`, and signs only after a focused, unobscured one-finger swipe/hold/release.

Exact UTF-8 payload, LF between fields, **no trailing LF**:

```text
leomux.approve.v1
<random server session_id>
<command ID>
<per-command nonce>
<lowercase SHA256 hex of exact command>
approve
```

`signature = lowercase_hex(HMAC_SHA256(bytes.fromhex(approval_key), payload))`.
The server recomputes from its own stored proposal, constant-time compares,
checks nonce/session and unexpired pending state under a lock, then consumes it
exactly once. Nonce replay, changed command/ID, wrong key, old session and unsigned
approval fail. A signature is **not an Android remote attestation certificate**;
see SECURITY.md for the narrower guarantee.

No CLI command generates valid real approvals. Tests use ephemeral fixture keys
to exercise the verifier. The production CLI can propose, deny, stop and inspect,
not self-approve with the socket token.
