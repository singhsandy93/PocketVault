# Security policy

## Release status

PocketVault 5.0.0 RC2 is a **test release**, not yet production-security-certified. Do not store sensitive content behind a public Tailscale Funnel until security hardening and threat-model review are complete.

## Operational precautions

- For private use, prefer Tailscale **Serve** within your tailnet over public Funnel.
- Protect pairing codes and API tokens. Pairing codes expire after five minutes; do not paste them into issues.
- Keep Raspberry Pi OS and Tailscale patched. Restrict server binding to 127.0.0.1; restrict backup directory permissions.
- Keep backups of `data/` including the SQLite database. Do not expose the database or original media as static public web directories.
- Never upload logs with credentials, keystores, personal hostnames, private files, or token-bearing requests.
- Do not assume SHA-256 content checking alone protects all upload and concurrency paths against malicious clients.

## Known RC2 gaps

Resource exhaustion, unauthenticated concurrent requests, disk-full behavior, abrupt power loss, orphan cleanup, upload ownership, race conditions and complete regression under fault injection require additional work. Exact cancellation offset reuse has not been independently confirmed. Android gallery UI is not part of RC2.

To report a vulnerability, contact repository maintainers privately rather than posting exploitation details as a public issue.
