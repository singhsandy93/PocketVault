# Start PocketVault automatically at boot

Complete [server setup](SERVER_SETUP.md) and stop any foreground PocketVault instance before proceeding. Run as the ordinary Pi account that owns the server files. The example unit assumes the installation directory ~/tailscale/PocketVault.

```sh
curl -fL https://raw.githubusercontent.com/singhsandy93/PocketVault/main/systemd/pocketvault.service -o /tmp/pocketvault.service
sed "s|/home/YOUR_PI_USER|$HOME|g; s|YOUR_PI_USER|$(id -un)|g" /tmp/pocketvault.service > /tmp/pocketvault-local.service
cat /tmp/pocketvault-local.service
sudo install -m 644 /tmp/pocketvault-local.service /etc/systemd/system/pocketvault.service
sudo systemctl daemon-reload
sudo systemctl enable --now pocketvault.service
systemctl status pocketvault --no-pager
curl -fsS http://127.0.0.1:8092/api/health
```

Review the generated paths and user before installing. If a service already exists, inspect it first with systemctl cat pocketvault. The service runs as your ordinary user, starts at boot and restarts five seconds after unexpected exit.

## Verify after reboot

When it is safe to interrupt backups:

```sh
sudo reboot
```

Reconnect via SSH and run:

```sh
systemctl is-enabled pocketvault tailscaled
systemctl is-active pocketvault tailscaled
curl -fsS http://127.0.0.1:8092/api/health
```

If using Tailscale, check the selected Serve/Funnel status and remote health URL as well. If not using Tailscale, omit tailscaled from these checks.

## Routine management

```sh
sudo systemctl restart pocketvault
sudo systemctl stop pocketvault
sudo systemctl start pocketvault
sudo journalctl -u pocketvault -n 50 --no-pager
```

After edits to the unit run sudo systemctl daemon-reload before restarting. No cron or shell login is required.
