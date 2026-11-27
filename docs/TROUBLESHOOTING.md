# Troubleshooting RC7

## Server is not reachable

```sh
systemctl status pocketvault --no-pager
sudo journalctl -u pocketvault -n 50 --no-pager
ss -ltnp | grep :8092
curl -i http://127.0.0.1:8092/api/health
```

If local health works, check tailscaled, the selected Serve/Funnel status, HTTPS hostname and /pocketvault prefix. A bare root URL can return 404. A storage request without a token should return 401.

## Pairing fails

Generate a fresh code using the pair command in the installation directory. Codes expire after five minutes, are single use, and are limited to five incorrect attempts. Check the phone URL and Pi clock.

## Upload failures

```sh
df -h ~/tailscale/PocketVault
du -sh ~/tailscale/PocketVault/data
```

Allow enough free space above the 3 GB reserve. Individual files are limited to 20 GB and request chunks to 4 MiB. HTTP 503 means retry later; 507 indicates insufficient storage; 409 may require resuming from the server's reported offset. Verify folder permissions, network and client battery settings. Incomplete uploads older than 24 hours are cleaned during upload processing. Exact Android resume behavior is not verified here.

## Missing thumbnails

```sh
cd ~/tailscale/PocketVault
python3 application/server.py thumbnail-status
python3 application/server.py repair-thumbnails
```

Check Pillow and FFmpeg dependencies. Repair requeues jobs; the running worker processes them. Unsupported formats may remain unavailable.

## Restart and logs

```sh
sudo systemctl restart pocketvault
sudo journalctl -u pocketvault -f
```

HTTP request logging is intentionally disabled; journal output may be limited. For failed logout, revoke the device separately from the Pi before discarding credentials. Report sanitized errors, server/client versions and reproduction steps; do not include tokens, pairing codes or personal media.
