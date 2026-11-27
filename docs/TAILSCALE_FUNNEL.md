# Tailscale remote access

Official references: [Linux installation](https://tailscale.com/docs/install/linux), [Funnel CLI](https://tailscale.com/docs/reference/tailscale-cli/funnel), [Serve CLI](https://tailscale.com/docs/reference/tailscale-cli/serve).

## Install and sign in

Review the official installation script before executing it.

```sh
curl -fsSL https://tailscale.com/install.sh -o /tmp/tailscale-install.sh
less /tmp/tailscale-install.sh
sh /tmp/tailscale-install.sh
sudo systemctl enable --now tailscaled
sudo tailscale up
tailscale status
```

Follow the sign-in URL and complete authorization.

## Choose access mode

Prefer private Serve for sensitive media. Install Tailscale on the phone and connect it to your authorized tailnet. For a private route:

```sh
sudo tailscale serve --bg --https=443 --set-path=/pocketvault 8092
sudo tailscale serve status
```

Alternatively, Funnel allows public internet access without Tailscale on the phone. RC7 is a release candidate, not independently security-certified. Use non-sensitive test data for public access. Follow any HTTPS or Funnel authorization prompts.

```sh
sudo tailscale funnel status
sudo tailscale funnel --bg --https=443 --set-path=/pocketvault 8092
sudo tailscale funnel status
```

Choose one mode for this HTTPS port: Funnel can make the listener public. Do not reset existing Serve/Funnel configuration or assume other routes on the same listener remain private. Inspect existing configuration before changing it.

Use the displayed HTTPS hostname with /pocketvault as the app server URL, e.g. https://your-pi.your-tailnet.ts.net/pocketvault (replace the example). Test by appending /api/health:

```sh
curl -fsS https://YOUR-HOSTNAME/pocketvault/api/health
```

Background configuration is persistent across normal reboots; tailscaled and PocketVault must both be enabled. After reboot check the selected mode's status and both local and remote health endpoints. Do not repeatedly run setup commands at boot. Account permissions, node authentication expiry and HTTPS eligibility can affect access.

Next: [Android setup](ANDROID_SETUP.md).
