# Tailscale installation and Funnel (RC2)

Read the current official documentation: https://tailscale.com/docs/install/linux and https://tailscale.com/docs/reference/tailscale-cli/funnel .

## Install on Raspberry Pi

Review the official Tailscale installation script before running it:

```sh
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale status
```

Authenticate via the URL displayed during setup. The Pi server should already be running on `127.0.0.1:8092`.

## Public Funnel URL

**Funnel exposes your server publicly.** Prefer Tailscale Serve (private tailnet) until hardening is complete. If using non-sensitive test files and public Funnel:

```sh
sudo tailscale funnel --bg --https=443 --set-path=/pocketvault 8092
sudo tailscale funnel status
```

Copy the displayed hostname and configure the Android URL in the form `https://your-device.your-tailnet.ts.net/pocketvault`. Test the `/pocketvault/api/health` endpoint, which should return a health JSON response. A storage API request before pairing should yield HTTP 401.

**Important:** Inspect existing Funnel routes first and retain them. Do **not** run a global Funnel reset, especially if the Pi hosts other web services. Funnel access depends on tailnet eligibility and current Tailscale behavior.
