# Troubleshooting

## Connection or pairing fails

- Check the Pi process: `ss -ltnp | grep :8092` and local health endpoint: `curl -i http://127.0.0.1:8092/api/health`.
- Check `sudo tailscale funnel status`; confirm the **same path** `/pocketvault` and device hostname in Android.
- A new pairing code invalidates the previous code. Codes expire in five minutes. Verify date/time is synchronized.

## HTTP 404 during logout

The RC2 Android app requires authenticated `POST /api/device/revoke`. Deploy the compatible RC2 server from this repository. Do not clear credentials on a failed logout unless you separately revoke the token.

## Upload failures or stuck backup

- Confirm data directory permissions and `df -h`; the server maintains a 3 GB disk free-space reserve.
- The server limits individual files to 20 GB and chunks to 4 MiB.
- Confirm Wi-Fi, battery and folder permissions and check device diagnostics. Use test data when troubleshooting public access.
- Upload interruption should retain incomplete data for retry, but exact reuse of the saved byte offset has not been independently verified on RC2.

## Incompatible installed APK signature

`INSTALL_FAILED_UPDATE_INCOMPATIBLE` means an installed app with the same package name was signed by a different key. Back up relevant settings and safely uninstall the old debug build before installing the signed release. Never remove original phone files.

## Reporting

Include sanitized server logs, application version, OS version, exact error response and reproducible steps. Remove token values, passwords, personal hostnames and media filenames if sensitive.
