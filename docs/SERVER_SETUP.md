# Manual server setup — PocketVault RC2

> **Development / non-sensitive test use only:** RC2 server production hardening and unattended installer are pending. Do not overwrite an existing installation or its database.

Prerequisites: 64-bit Raspberry Pi OS Bookworm, Python 3.11, `python3-pil`, `ffmpeg` and free disk space.

After obtaining this repository's server source, for a **new** installation only:

```sh
mkdir -p ~/PocketVault/application ~/PocketVault/data
cp server/application/server.py ~/PocketVault/application/server.py
chmod 700 ~/PocketVault/data
chmod 600 ~/PocketVault/application/server.py
cd ~/PocketVault
python3 application/server.py init
python3 application/server.py serve --port 8092
```

Leave the server running in the foreground (Ctrl+C to stop). In another terminal:

```sh
cd ~/PocketVault
python3 application/server.py pair
python3 application/server.py devices
# Optional — revoke an identified device
python3 application/server.py revoke DEVICE_ID
```

Verify: `curl -i http://127.0.0.1:8092/api/health`. The server binds to loopback, not the LAN.

Data is stored under `~/PocketVault/data/` with compatibility database `pibackup.db`; original files are stored beneath `data/originals/`. Back up the entire data directory. **Do not rename `pibackup.db` or migrate an existing setup manually.**

Systemd units, a supported `pocketvault` CLI wrapper and automatic installer remain pending.
