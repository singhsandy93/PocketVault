# Raspberry Pi setup (RC2)

Tested with Raspberry Pi 4B, 64-bit Raspberry Pi OS Bookworm and Python 3.11.

1. Use Raspberry Pi Imager to flash Raspberry Pi OS (64-bit). Set a strong password, username and SSH access.
2. Boot, connect to a trusted network, and run:

```sh
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y python3 python3-pil ffmpeg curl ca-certificates git
python3 --version
df -h
```

3. Use reliable storage and keep independent backups of server data. A spare disk/SSD is recommended for important media.
4. Continue with [manual server setup](SERVER_SETUP.md), then optionally [Tailscale and Funnel](TAILSCALE_FUNNEL.md).

The RC2 one-command installer and systemd configuration are **not yet released**.
