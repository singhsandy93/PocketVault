# Changelog

## [5.0.0-rc2] — 2026-11-27

- PocketVault Android application package `com.pocketvault.app`; modern dark appearance by default.
- Pairing, selected-folder photo/video backups, Wi-Fi scheduling, automatic backups, resumable uploads, deduplication and per-file status.
- Authenticated logout: server revokes device token, Android clears local pairing while preserving preferences.
- Verified signed APK on a physical Motorola device, media integrity and re-pairing; signed APK attachment to GitHub Releases is a separate publication step.
- **Limitations:** not fully hardened; exact resume-offset reuse not proven; long-running Android background worker has no foreground promotion; gallery UI deferred; database compatibility name `pibackup.db` retained; manual server setup only.
