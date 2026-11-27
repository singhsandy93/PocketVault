# Raspberry Pi preparation

Tested environment: Raspberry Pi 4B (4 GB), Raspberry Pi OS 64-bit Bookworm, Python 3.11, SQLite. A 64-bit Raspberry Pi OS installation is recommended, with reliable storage and adequate free space for backups.

1. Write the current Raspberry Pi OS 64-bit image using Raspberry Pi Imager. Set a username, strong password and SSH access in Imager settings.
2. Boot and connect your Pi to a trusted network. Update packages:

```sh
sudo apt update && sudo apt full-upgrade -y
sudo apt install -y python3 python3-pil ffmpeg curl ca-certificates
```

3. Confirm prerequisites with `python3 --version`, `ffmpeg -version`, and `df -h`.
4. Use a stable, adequately powered disk or SSD for valuable media. Do not assume the SD card alone is durable backup storage.
5. Continue with [server setup](SERVER_SETUP.md), then optionally [Tailscale/Funnel](TAILSCALE_FUNNEL.md).

External storage setup, data migration and boot-time systemd installation are not automated in RC2.
