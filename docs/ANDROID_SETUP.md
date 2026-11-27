# Android — signed RC2 APK

- Android package: `com.pocketvault.app`
- Version: `5.0.0-rc2`; version code `6`
- Minimum supported: Android 10 (API 29)
- APK: `PocketVault-v5.0.0-rc2.apk`
- APK SHA-256: `50124279ced4c95b7fcf120b025fcf7e477fac4161e21d4168c802f5d6b9dc4a`
- Signing certificate SHA-256: `7e0124e1497ea60f5c19ee85c0c3a2fc764acf96fe62eddf751f42e99077edf9`

After the APK is added to a GitHub pre-release, download it and verify the SHA-256 checksum (macOS: `shasum -a 256 PocketVault-v5.0.0-rc2.apk`; Linux: `sha256sum ...`).

Install the APK on Android, configure your server's HTTPS URL, generate a pairing code on Raspberry Pi with `python3 application/server.py pair` and enter it in the app. Select photo/video folders and set backup preferences. Original phone media is not deleted.

If an existing `com.pocketvault.app` was debug-signed, the release APK cannot update it in place: back up relevant settings, then uninstall the debug build before installing release; pairing must be repeated. Never uninstall the separate original PiBackup application by mistake.

Build from source with Android Studio and SDK 36; use your own secure signing key. Never publish .jks files or key passwords. Gallery/recycle Android UI is deferred in RC2.
