# PocketVault

Self-hosted Android photo/video backup for Raspberry Pi, with optional Tailscale access.

> **v5.0.0-rc2 — Release candidate, not production-security-certified.** The Android APK has passed functional testing, but the Python server still needs security hardening. Do not expose sensitive backups through public Funnel until this is complete.

## Components

- **Android**: signed APK distributed through GitHub Releases; **Android source code is not included in this repository**.
- **Server**: Python 3.11, SQLite, SHA-256 integrity checks, chunked uploads, deduplication, device pairing and token revocation.
- **Remote access**: Tailscale Funnel (public HTTPS) or Tailscale Serve (private tailnet).

## Installation

1. Install **64-bit Raspberry Pi OS** and `python3`, `python3-pil`, `ffmpeg`.
2. Clone this repository when the full source import is completed.
3. Prepare `~/PocketVault/application` and `~/PocketVault/data`; put the RC2 `server.py` into `application/`.
4. From `~/PocketVault`, run `python3 application/server.py init` and `python3 application/server.py serve --port 8092`.
5. Use `python3 application/server.py pair` from a second terminal to obtain a five-minute pairing code.
6. Optionally configure Tailscale and a `/pocketvault` Funnel path. Enter the HTTPS URL in Android.
7. Install the **signed** `PocketVault-v5.0.0-rc2.apk` when it is attached to GitHub Releases.

**Important:** Raspberry Pi server source and the production installer are still being prepared for this repository. Android source will not be uploaded. Do not assume the commands above form a hardened unattended deployment. Existing server data is under `data/` and the compatibility database is called `pibackup.db`; never rename or delete it without a backup.

## APK checksum

SHA-256: `50124279ced4c95b7fcf120b025fcf7e477fac4161e21d4168c802f5d6b9dc4a`

Certificate SHA-256: `7e0124e1497ea60f5c19ee85c0c3a2fc764acf96fe62eddf751f42e99077edf9`

## Current limitations

Production security hardening, validated one-command installer/systemd, fresh-install regression and exact resume-offset observation are outstanding. Android gallery and recycle UI are deferred.

See [SECURITY.md](SECURITY.md), [CHANGELOG.md](CHANGELOG.md) and the full source archive prepared for this release. Never commit keystores, database, phone media, tokens or personal configuration.

MIT License — © 2026 Pocket Solutions.
