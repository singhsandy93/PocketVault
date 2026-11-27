# V4 candidate — not yet compiled
Open this separate project in Android Studio. Run Gradle tasks testDebugUnitTest and assembleDebug, then Run on the existing test phone. Do not uninstall V3 (pairing and settings use the same package). No Pi changes required.

Changes: MediaStore content-triggered WorkManager request (photos/videos), periodic fallback, strict active Wi-Fi check, custom interval 15–10080 minutes, estimated next scan based on last success (not actual scheduler time), grouped file headings, selected chips, per-chunk byte status, foreground restriction fallback and transient retry/status retention. Original read implementation unchanged.

Limitations: content triggers cover media indexed by MediaStore, not every SAF document; fallback handles missed changes. Event work rearmed after successful run or subsequent periodic scan. Foreground fallback may hit ordinary worker runtime limits. VPN transport may obscure Wi-Fi. No guarantee of exact next time. Existing file-level failure summary may still include transient failures. No full Android automated regression suite yet.

Device regression: verify existing pairing/settings; repeat original hashes; test event trigger while app closed; periodic fallback; disable auto; custom interval; Wi-Fi/mobile and charging/battery; interrupt a new large upload and capture same upload ID/offset; verify SHA; check grouping, notifications, cancel, two parallel uploads, limited permissions and rebackup. Do not delete original phone files.
