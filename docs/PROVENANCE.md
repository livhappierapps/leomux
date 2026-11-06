# Source handoff

- EdenMux: supplied `EdenMuxOP-Android-Leo` archive, inspected from the local
  handoff. Existing Expo structure, artwork, terminal renderer, tabs, palette,
  pane composition and voice-first intent retained. RevenueCat, Replit and
  remote server pieces deliberately not copied.
- Commander: supplied local `leo-commander`, source commit `4ac394b`
  (`Leo the Termux Commander: initial import`). Persistent tmux runner ported
  to `termux/runner.py`; protocol/risk scanners and tests adapted. Server's
  Python socket/approval/queue design retained; legacy share/clipboard/dialog/
  notification approval plumbing removed, HMAC v2 added.
- Commander was identified as private while LeoMux is public; the owner expressly
  requested this port to that public target. No .git metadata, local secret
  files, built APK/IPA or Commander zip is included.
- Artwork remains Eden-branded as a visual foundation; not represented as final
  Leo branding or newly licensed art. Ownership/license of all supplied assets
  remains with the original owner. No invented open-source license is applied.
