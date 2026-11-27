# Raspberry Pi preparation (RC7)

Use Raspberry Pi OS 64-bit. Bookworm with Python 3.11 is the established environment; newer releases have not been independently validated here.

1. Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer.
2. Choose your Pi and Raspberry Pi OS 64-bit. Configure your own username, strong password, network and SSH in Imager. Writing the image erases the selected drive.
3. Boot the Pi and connect via SSH using your configured username and hostname (for example, `ssh youruser@raspberrypi.local`).
4. Run on the Pi:

```sh
sudo apt update
sudo apt upgrade
sudo apt install -y python3 python3-pil ffmpeg curl ca-certificates git
python3 --version
python3 -c 'from PIL import Image; print(Image.__version__)'
ffmpeg -version
ffprobe -version
df -h
```

Python 3.9 or newer is required by the source; Python 3.11 is recommended. Allow more than 3 GB free plus space for your media. Use reliable storage and keep independent backups; an SD card alone is not a durable backup strategy.

Next: [Install PocketVault](SERVER_SETUP.md).
