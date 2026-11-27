# Changelog

## [5.0.0-rc7]

- Server health identifies RC7; source-folder storage and legacy date-folder relocation on confirmed full paths.
- Deleted-hash suppression for all-reference deletion, cleared on restore; trash media access and gallery filters.
- Documented Raspberry Pi deployment, Tailscale Serve/Funnel, systemd automatic startup, pairing, usage, troubleshooting and upgrades.
- RC7 APK and Android source are not published in this update. No new server behavior was introduced by the documentation changes; full RC7 regression/security validation remains pending.

## [5.0.0-rc2] — 2026-11-27

- PocketVault Android application package `com.pocketvault.app`; modern dark appearance by default.
- Pairing, selected-folder photo/video backups, Wi-Fi scheduling, automatic backups, resumable uploads, deduplication and per-file status.
- Authenticated logout: server revokes device token, Android clears local pairing while preserving preferences.
- Verified signed APK on a physical Motorola device, media integrity and re-pairing; signed APK attachment to GitHub Releases is a separate publication step.
- **Limitations:** not fully hardened; exact resume-offset reuse not proven; long-running Android background worker has no foreground promotion; gallery UI deferred; database compatibility name `pibackup.db` retained; manual server setup only.
