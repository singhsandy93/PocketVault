# Security policy

PocketVault RC2 is a **test release**, not production-security-certified. Do not make sensitive media publicly accessible through Tailscale Funnel until hardening and independent tests are complete.

For private use, prefer Tailscale Serve with tailnet authentication over public Funnel. Secure SSH, patch the Raspberry Pi, avoid running as root, and back up the entire server `data/` directory. Never publish keystores, pairing codes, device tokens, databases, photographs or server-specific credentials.

**Known RC2 gaps:** resource exhaustion, burst unauthenticated connections, disk-full and abrupt power-loss recovery, crash-safe filesystem/SQLite coordination, and full threat-model testing. Exact reuse of the upload byte offset after an interruption has not been independently observed. The server still uses the compatibility database filename `pibackup.db`.

Report vulnerabilities privately to maintainers; please do not post exploitable details or sensitive logs as public issues.
