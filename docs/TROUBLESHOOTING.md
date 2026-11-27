# Troubleshooting

- **No connection**: On Pi, check `ss -ltnp | grep :8092` and `curl -i http://127.0.0.1:8092/api/health`. Review `sudo tailscale funnel status`; preserve the `/pocketvault` path.
- **Pairing fails**: Generate a fresh code (`python3 application/server.py pair`), use it within five minutes, and ensure the Android server URL is correct. Generating a new code invalidates the previous code.
- **Logout reports HTTP 404**: The Android RC2 release requires the RC2 server's authenticated `POST /api/device/revoke` endpoint. Update only after backing up server source/data.
- **Backup unavailable**: Check Pi free space, folder permissions, Wi-Fi and battery settings; media files max 20 GB and upload chunk size 4 MiB. Use non-sensitive test files for debugging public Funnel.
- **APK signing mismatch**: `INSTALL_FAILED_UPDATE_INCOMPATIBLE` means installed package has a different signer; preserve data, remove only the matching debug app and reinstall signed APK.
- **Logs**: Redact device tokens, pairing codes, personal hostnames and media contents before publishing.

The RC2 server is not security hardened. Background upload worker interruption and exact offset resumption remain areas for improvement.
