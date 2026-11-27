# Install PocketVault RC7

For a fresh installation, complete [Pi preparation](RASPBERRY_PI_SETUP.md). Run as your normal Pi user, not root. Existing installations should follow the [upgrade guide](UPGRADE.md).

```sh
mkdir -p ~/tailscale/PocketVault/application
curl -fL https://raw.githubusercontent.com/singhsandy93/PocketVault/main/server/application/server.py -o ~/tailscale/PocketVault/application/server.py
cd ~/tailscale/PocketVault
python3 application/server.py init
python3 application/server.py serve --port 8092
```

In another SSH session:

```sh
curl -fsS http://127.0.0.1:8092/api/health
```

Expect JSON containing status ok and release 5.0.0-rc7 for this version. The server listens only on loopback. Stop the foreground server with Ctrl+C before installing [automatic startup](AUTO_START.md). Then configure [Tailscale](TAILSCALE_FUNNEL.md).

## Pair and manage devices

```sh
cd ~/tailscale/PocketVault
python3 application/server.py pair
python3 application/server.py devices
```

Pairing codes expire in five minutes and are single use; five incorrect attempts invalidate a code. To revoke a device, run `python3 application/server.py revoke DEVICE_ID` with its actual ID.

## Storage

The data directory is created automatically beside application:
- data/pibackup.db: SQLite metadata, token hashes and pairing state.
- data/originals/: media, organized by reported source folder for new uploads.
- data/thumbnails/: derived previews.
- data/incomplete/: unfinished uploads.

Do not edit the database or move originals manually. Keep an independent backup of the complete data directory. The server limits files to 20 GB, chunks to 4 MiB and maintains a 3 GB free-space reserve for uploads. Trash references expire after 30 days.

Next: [Automatic startup](AUTO_START.md).
