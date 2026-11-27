# PocketVault

Self-hosted Android photo and video backup server for Raspberry Pi, with optional HTTPS access through Tailscale.

**Current server: 5.0.0-rc7.** This is a release candidate, not a production-security-certified service. The compatible Android APK and Android source are not distributed in this repository at present.

## Start here

Follow these guides in order:

1. [Prepare Raspberry Pi](docs/RASPBERRY_PI_SETUP.md)
2. [Install and test the Python server](docs/SERVER_SETUP.md)
3. [Enable automatic startup and restart on failure](docs/AUTO_START.md)
4. [Install Tailscale and configure private Serve or public Funnel](docs/TAILSCALE_FUNNEL.md)
5. [Connect the Android application](docs/ANDROID_SETUP.md)
6. [Using PocketVault](docs/USER_GUIDE.md)

Already installed? Read [upgrade instructions](docs/UPGRADE.md) and [troubleshooting](docs/TROUBLESHOOTING.md).

## Server features

- Single-use six-digit pairing and token authentication.
- Resumable chunk uploads with SHA-256 verification and deduplication.
- Original source folder organization for new uploads.
- Gallery filtering, thumbnails, downloads and video streaming APIs.
- Recycle bin with 30-day retention, restore and permanent purge.
- Storage reporting and a 3 GB upload free-space reserve.

## Project layout

```text
server/application/server.py
systemd/pocketvault.service
docs/
tests/
```

The documented deployment uses ~/tailscale/PocketVault, Python 3.11, Pillow, FFmpeg and SQLite. HTTP listens on 127.0.0.1:8092. The systemd template uses the installing user's own account and home directory. See the individual guides for commands.

## Security and backup

Prefer private Tailscale Serve for sensitive media. Funnel exposes the HTTPS listener publicly; use non-sensitive test data until independently hardened. All active paired devices share gallery and trash access, so pair only trusted devices. Media are ordinary files, not an application-encrypted vault. Keep independent backups of the complete data directory, including pibackup.db. Never commit personal data, device tokens, pairing codes, signing keys or credentials.

The current server has not been independently security audited or fully regression tested with every Android build. Historical tests in this repository are not an RC7 validation report.

See [security policy](SECURITY.md), [changelog](CHANGELOG.md) and [MIT license](LICENSE).
