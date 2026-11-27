# Tailscale and optional public Funnel

Official reference: https://tailscale.com/docs/install/linux and https://tailscale.com/docs/reference/tailscale-cli/funnel

## Install Tailscale on Raspberry Pi

Review Tailscale's official install script before running it:

```sh
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
sudo tailscale status
```

Finish sign-in through the authentication URL shown by Tailscale. Install/upgrade Tailscale from its documented package repositories for your Raspberry Pi OS release.

## Private versus public

Tailscale **Serve** keeps access within your authenticated tailnet; **Funnel is publicly reachable** over HTTPS without Tailscale installed on the visitor's device. Until RC2 hardening is complete, prefer private Serve or non-sensitive test data only.

## Configure a separate PocketVault Funnel path

Start PocketVault on port `8092` first, then:

```sh
sudo tailscale funnel --bg --https=443 --set-path=/pocketvault 8092
sudo tailscale funnel status
```

Use the HTTPS URL and `/pocketvault` path displayed by Tailscale as your Android server URL, for example `https://your-device.your-tailnet.ts.net/pocketvault`.

**Avoid `tailscale funnel reset`:** it may remove other unrelated routes. If you have existing Funnel configuration, inspect `sudo tailscale funnel status` and preserve every preexisting route. Test `https://YOUR-TAILSCALE-FQDN/pocketvault/api/health` and expect a health JSON response. If the app requests storage without pairing, `401 Unauthorized` is expected.

Funnel access controls, node configuration and command syntax can change; consult the official Tailscale documentation before applying changes. Funnel requires account/tailnet eligibility and HTTPS configuration.
