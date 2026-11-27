# Android application and APK verification

- Package: `com.pocketvault.app`
- Minimum supported Android: API 29 / Android 10
- Version: `5.0.0-rc2` (`versionCode` 6)
- Signed APK filename: `PocketVault-v5.0.0-rc2.apk`
- SHA-256: `50124279ced4c95b7fcf120b025fcf7e477fac4161e21d4168c802f5d6b9dc4a`
- Signing certificate SHA-256: `7e0124e1497ea60f5c19ee85c0c3a2fc764acf96fe62eddf751f42e99077edf9`

Download the signed APK from GitHub Releases **when the release asset has been attached**. Verify its checksum using `shasum -a 256` on macOS or `sha256sum` on Linux. Android verifies the app signature upon installation. Existing debug-signed builds with the same package name must be uninstalled before installing a release-signed build; this clears local app data and pairing, but does not remove server-side backups.

In Android: enter the HTTPS server URL, request a pairing code on the Pi (`python3 application/server.py pair`), select permitted folders, and enable scheduled/automatic backup preferences. Original photos are preserved. Changing folders stops future selection but does not automatically delete server media.

## Build from source

Open repository root in a recent Android Studio with Android SDK 36 available; run Gradle sync. Build the debug variant for development. For distributable release APKs create **your own** permanent signing key. Never commit or share `.jks`, passwords or private keys. Other developers cannot produce an update signature matching the maintainer's public APK.

RC2 does not include the Android gallery/recycle UI; the server's endpoints are separate. Long running background uploads and full error recovery require additional testing.
