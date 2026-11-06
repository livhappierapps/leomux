# Before calling this ready on Samsung A17

- [ ] Obtain authorization for a native development APK/build (none run yet).
- [ ] Compile native LeoApproval module with Expo SDK54/new architecture; inspect
      merged manifest: no share target, overlay permission, exported shell service,
      backup, unintended storage/microphone permissions.
- [ ] Verify real react-native-tcp-socket→Termux on same phone at 127.0.0.1:8765.
- [ ] Wrong token/non-hello first disconnect; never expose LAN/socket key endpoint.
- [ ] Pair separate key; restart app; ensure SecureStore and Keystore survive.
- [ ] Voice is default, tap talks through Termux:API, text is explicit fallback;
      handle permission denial, missing recognizer, cancel and API/network error.
- [ ] Verify termux-tts-speak replies and no recognizer-derived approval route.
- [ ] Scroll/review long command natively, normal swipe+hold+release succeeds once.
- [ ] Taps, quick flings, short swipes, endpoint misses, multi-touch, focus loss,
      replacement proposal, full/partial overlay and synthetic accessibility click
      do NOT approve. Test Android recognition switching focus away and back.
- [ ] One-handed reach-down control; short screens/keyboard do not hide STOP.
- [ ] Deny/expire pauses and discards queue; resume never replays.
- [ ] Harmless slow command + queued pwd: STOP ends leo and cancels queued command.
- [ ] cd/export survive successful commands, interactive programs require tmux.
- [ ] Background/kill UI, disconnect/reconnect, reboot server, killed Termux,
      battery optimization all fail safely; stale signatures rejected.
- [ ] Independent security review before allowing arbitrary real workflows.
