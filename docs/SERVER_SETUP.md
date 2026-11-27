# Manual PocketVault server setup (RC2)

> RC2 is a test release. Production one-command installer and systemd service are not yet provided. Do **not** replace an existing server or its database without an independent backup. All commands below refer to a new, fresh install.

## Prerequisites

Raspberry Pi OS Bookworm, Python 3.11, Pillow (`python3-pil`), ffmpeg and enough disk space. See [Raspberry Pi setup](RASPBERRY_PI_SETUP.md).

## New installation

Download or clone this repository. On the Raspberry Pi, from repository root:

```sh
mkdir -p ~/PocketVault/application ~/PocketVault/data
cp server/application/server.py ~/PocketVault/application/server.py
chmod 700 ~/PocketVault/data
chmod 600 ~/PocketVault/application/server.py
cd ~/PocketVault
python3 application/server.py init
python3 application/server.py serve --port 8092
```

The foreground command runs until Ctrl+C. In another SSH terminal, generate a time-limited pairing code:

```sh
cd ~/PocketVault
python3 application/server.py pair
```

Additional commands:

```sh
python3 application/server.py devices
python3 application/server.py revoke DEVICE_ID
```

Verify locally: `curl -fsS http://127.0.0.1:8092/api/health`. The server binds to loopback; it does not directly listen on the LAN. If enabled, Tailscale reverse-proxies it using Funnel or Serve.

**Data location:** `~/PocketVault/data/` contains `pibackup.db`, `originals/`, `incomplete/` and `thumbnails/`. Back up the entire directory. Use distinct directories and ports for testing alongside existing installations.

**Not yet shipped:** `pocketvault` command-line wrapper, production `setup.sh`, systemd unit, backup/migration tooling. Avoid running a legacy installer from a different PiBackup project.
