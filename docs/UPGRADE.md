# Upgrade an existing server

Do not overwrite a working installation without an independent backup. Schema migration and rollback are not guaranteed for all historical builds.

For the documented ~/tailscale/PocketVault installation:

```sh
cd ~/tailscale/PocketVault
curl -fL https://raw.githubusercontent.com/singhsandy93/PocketVault/main/server/application/server.py -o /tmp/pocketvault-server.py
python3 -m py_compile /tmp/pocketvault-server.py
sudo systemctl stop pocketvault
```

While stopped, copy the complete application and data directories to a separate reliable storage device and verify the copy. Do not proceed until that backup exists and is readable.

```sh
cp /tmp/pocketvault-server.py application/server.py
sudo systemctl start pocketvault
curl -fsS http://127.0.0.1:8092/api/health
sudo journalctl -u pocketvault -n 50 --no-pager
```

Verify remote health, pairing, gallery and a small test upload. Do not delete or reinitialize the data directory. If upgrade fails, stop the service and restore the matching application and data backup together before restarting. Existing installations at a different path must adapt the commands. The APK is distributed separately; do not assume compatibility with arbitrary previous builds.
