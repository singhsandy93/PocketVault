# Android setup

This repository currently provides the RC7 server. The RC7 APK and Android source are not included; obtain a compatible signed APK from the maintainer through a trusted channel. Do not download unverified APKs. The earlier Android package is com.pocketvault.app (Android 10+); RC7 client build metadata and signing checksum have not been verified here.

1. Complete [server setup](SERVER_SETUP.md) and [remote access](TAILSCALE_FUNNEL.md).
2. Install the trusted compatible APK. Allow installation from the selected source only if necessary, then disable that permission.
3. On the Pi run:

```sh
cd ~/tailscale/PocketVault
python3 application/server.py pair
```

4. In the app enter your full HTTPS server base URL including /pocketvault, and the pairing code. Do not include /api/health.
5. Select folders and grant the requested media access. Start a small backup and check that the media is present on the server.
6. Configure backup scheduling or Wi-Fi preferences if available in your client build.

See [user guide](USER_GUIDE.md). Do not uninstall a working client merely to upgrade: Android requires matching signing keys. Uninstalling clears app-local settings and credentials. Verify any published APK checksum before installing. Never share signing keys or device tokens.
