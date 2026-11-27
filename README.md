# PocketVault

Self-hosted Android photo and video backup for Raspberry Pi, with optional HTTPS access using Tailscale Funnel.

> **v5.0.0-rc2 — public release candidate. Not production-security-certified.** Do not expose sensitive backups through a public Funnel until server hardening and independent security testing are complete. The tested companion server supports device pairing, resumable chunk uploads, SHA-256 content verification, deduplication, media metadata, recycle-bin APIs and authenticated device logout.

## Components

- `app/` — Android Kotlin / Jetpack Compose project (`com.pocketvault.app`, Android 10+).
- `server/application/server.py` — Python / SQLite server, currently tested with Python 3.11 on Raspberry Pi OS Bookworm.
- `docs/` — Raspberry Pi, manual server, Tailscale, Funnel, Android, security and troubleshooting guides.
- `scripts/` — initial development setup scripts; production one-command installer is **not yet available**.

## Quick start (development / non-sensitive data)

1. Install Raspberry Pi OS 64-bit and Python 3.11; follow [Pi setup](docs/RASPBERRY_PI_SETUP.md).
2. Follow [manual server setup](docs/SERVER_SETUP.md). Do **not** run an unreviewed legacy `setup.sh`.
3. For remote access follow [Tailscale and Funnel](docs/TAILSCALE_FUNNEL.md), recognizing that Funnel is public.
4. Install the signed Android APK from a GitHub pre-release once its asset is attached. Confirm its SHA-256 using [release verification](docs/ANDROID_SETUP.md).
5. On the Pi use `python3 server.py pair`, then configure the server's HTTPS URL and enter the pairing code in Android.

## Security and limitations

- **Funnel exposes the app to the public internet.** A trusted private tailnet, firewall, or VPN-only arrangement is safer for sensitive media until server hardening is complete.
- Media are ordinary files beneath the server's `data/originals/` directory and metadata are in SQLite. Back these up separately.
- RC2 uses a metadata database named `pibackup.db` for compatibility with existing installations. Do not rename it manually.
- The current server lacks full limits for unauthenticated connections, crash/disk-full testing and other production hardening. Gallery/recycle API endpoints exist, but Android gallery UI remains future work.
- Do not commit Android signing keystores, passwords, pairing codes, token files, personal media, databases or host-specific configuration.
- A systemd installer, secure automated migration, full validation and production-readiness review remain on the roadmap.

## Development

Open the repository root in Android Studio and use Gradle to build. Use **your own** persistent signing keystore for release APKs. Never publish signing credentials. See [Android guide](docs/ANDROID_SETUP.md).

## Legal

MIT License; see [LICENSE](LICENSE). Third-party dependencies retain their own licences.
