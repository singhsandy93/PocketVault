# Using PocketVault

A compatible Android APK is required and is not currently distributed in this repository. See [Android setup](ANDROID_SETUP.md) for pairing. Client screens and feature availability may differ; the following describes the RC7 server capabilities and intended workflow, not independently verified Android interactions.

1. Pair the phone with the server using its HTTPS base URL and a fresh pairing code.
2. Choose the phone folders you wish to back up and grant access.
3. Run a small backup. Verify the files on the server before relying on automatic backups.
4. If the client supports scheduling, configure it and confirm a subsequent backup completes.

## Browse and recover

The RC7 server provides gallery filtering by device, exact source folder, name and date, thumbnails, original downloads and video streaming. Identical files share stored content and can have multiple references. All paired active devices share the server's gallery and trash; it is not a multi-tenant isolation system.

Server trash supports selected-reference or all-reference deletion, restore and permanent purge. Trash expires after 30 days. Deleting all references also suppresses future uploads of that hash; restoring clears suppression. Server trash does not by itself delete local Android files. Client-side deletion and restore-to-phone depend on the app and Android permissions. Do not delete phone originals until you have verified independent recoverable copies.

Use the app storage display if available or run df -h on the Pi. Revoke a lost phone using the devices and revoke commands in [server setup](SERVER_SETUP.md). Treat device tokens as passwords.
