# si provisioning and restore commands

Implemented 2026-10-21. These are explicit commands, not apply hooks. **Do not run the restore sequence on the current healthy server.** Live application databases/configuration remain authoritative.

## Routine updates (`tjikup`)

`tjikup` pulls/pushes source and applies chezmoi and chezetc. Package upgrades, Docker enable/start and nginx module rebuilds retain their normal behavior. Storage guards protect service startup. Provisioning and restore tools are never invoked by these hooks. Review diffs before applying substantial changes; ordinary maintenance can still update packages and managed files.

Neither provisioning nor restoration is an apply hook. Transmission's mutable settings.json is ignored on the server. Application databases and passwords are not template targets. Existing mergerfs is not replaced, existing accounts are not renumbered, existing directory ownership/modes are not recursively changed, and existing Beets files are not overwritten. Auto-m4b remains opt-in.

## Always-on server power policy

On si only, systemd sleep policy disables suspend and hibernation, and the GDM dconf policy disables idle sleep for the greeter. The server-only apply hook compiles that policy without restarting GDM. Client hosts ignore these policy files. This prevents the greeter default (15-minute idle suspend) from taking storage and media services offline even when the logged-in user has already disabled sleep.

## Account and storage bootstrap

Run the planning form first; add `--apply` to make the planned changes:

```fish
sudo python3 /etc/si-provision/provision.py accounts
sudo python3 /etc/si-provision/provision.py accounts --apply
sudo python3 /etc/si-provision/provision.py mergerfs
sudo python3 /etc/si-provision/provision.py mergerfs --apply
```

Mergerfs 2.42.0 is locked to the upstream Fedora 44 x86_64 RPM and publisher SHA256. Other OS/architectures fail closed. Existing installations are preserved regardless of version; upgrading a running pool remains an explicit maintenance operation. The Fedora 44 artifact was hash-verified and passed isolated merged-read, write, rename and delete checks. The removed `use_ino` option is no longer generated. On si, the upgrade was explicitly activated by an orderly reboot; disk UUID checks, normal-user pool writes and cross-process SQLite WAL locking passed. A complete fresh-host recovery rehearsal is still required.

Install the server package declarations deliberately during bootstrap (including Docker, Compose, SnapRAID, Plex, rsync, restic and PyYAML); normal server tjikup package maintenance remains enabled. Keep Docker and Plex stopped until mounts and restored state are ready. Use the selective fstab helper described in SERVER-REBUILD.md, then verify:

```fish
sudo python3 /etc/si-provision/storage.py --check
```

## Fedora 44 to 45: completed upgrade and compatibility notes

Operator decision on 2026-10-21: use Fedora 45's base nginx **1.30.5** packages with the installed DAV extension (ABI 1.30.5), and Fedora/RPM Fusion 45's matching **libheif/libheif-freeworld 1.23.5** pair. Do not mix Fedora 44 repositories into the Fedora 45 transaction. These were transaction-scoped choices; si is now running Fedora 45.

The strict resolver preview passed with no conflicts, skips or `--allowerasing`: 62 installs, 3,138 upgrades, six removals and 12 downgrades, approximately 4 GiB downloaded / 677 MiB net installed growth. Counts can change as repositories move. The removals were the oldest Fedora 43 kernel packages plus `low-memory-monitor`. Downgrades were `gh`, two GStreamer freeworld/ugly packages, the libheif pair, `libopenmpt`, `python3-pyOpenSSL`, three Qt4 packages, and two Xen packages. The downloaded payload subsequently passed the RPM transaction test and was installed successfully (DNF history transaction 86, status Ok).

The following historical preparation commands were already executed on **si in Fish**. Do not repeat the system-upgrade transaction on the upgraded server. They define the reviewed RC repository selection. Exclusions affect only the named testing repositories, leaving the matching Fedora 45 base packages selectable. The assessment cache was reused for the reviewed payload download and offline transaction.

```fish
set -l si_fc45_options \
    --releasever=45 \
    --setopt=cachedir=/var/cache/si-fedora45-assessment \
    --disablerepo=rpmfusion-free-updates \
    --disablerepo=rpmfusion-nonfree-updates \
    --enablerepo=updates-testing \
    --enablerepo=rpmfusion-free-updates-testing \
    --enablerepo=rpmfusion-nonfree-updates-testing \
    '--setopt=updates-testing.excludepkgs=nginx*,libheif*' \
    '--setopt=rpmfusion-free-updates-testing.excludepkgs=libheif*' \
    --best

sudo python3 /etc/si-provision/storage.py --check
sudo nginx -t
sudo dnf check
df -h / /boot
sudo dnf $si_fc45_options system-upgrade download --assumeno
```

Review that nginx remains 1.30.5, the libheif pair is 1.23.5, and the removal/downgrade list still matches the decision. `--assumeno` deliberately exits without downloading/staging. The observed free space was 9.1 GiB on `/` and 128 MiB on `/boot`; check it again before downloading. Do not add `--allowerasing` to bypass a new dependency error.

Take a fresh application backup on **si**, then inspect the new success receipt:

```fish
sudo systemctl start si-app-backup.service
sudo journalctl -u si-app-backup.service -n 15 --no-pager
sudo cat /var/lib/si-app-backup/last-success.json
sudo restic -r /mnt/data/disk42/.recovery-preservation/app-backups/repository \
    -p /etc/si-app-backup/password snapshots --host si --tag app-state --latest 1 --json
```

On **fi**, fetch and verify the current retained snapshots (fi initiates SSH):

```fish
systemctl --user start si-app-backup-pull.service
journalctl --user -u si-app-backup-pull.service -n 15 --no-pager
cat ~/.local/share/si-app-backups/last-success.json
```

Require a new successful server receipt and a local receipt whose source time matches the latest server snapshot. The server backup receipt's `completedAt` is the job completion time; the snapshot/fi `sourceTime` is the capture time, so those timestamps are not expected to be identical. The local job verifies all repository data before recording success. Never print or commit either repository password.

After those checks, this **si** command downloads the approximately 4 GiB payload, checks that the packages can be installed (DNF5's RPM transaction test), and prepares the offline transaction. It does **not** reboot or install Fedora 45 into the running system:

```fish
sudo dnf $si_fc45_options system-upgrade download
sudo dnf offline status
```

The operator authorized `sudo dnf -y system-upgrade reboot` at 19:04 HKT on 2026-10-21. The offline transaction completed and si returned at about 19:20 HKT on Fedora 45, kernel `7.2.11-300.fc45.x86_64`; no offline transaction remains queued. Post-upgrade `dnf check` and duplicate-package checks passed. Normal package updates, Docker startup and nginx convergence remain enabled.

The running mergerfs process is 2.42.0 (the preserved Fedora 44 RPM). All expected disk UUID mounts and the pool passed storage checks; normal-user writes, fsync and removal through `/home/m/downloads` passed. Plex remains claimed, nginx/DAV passes `nginx -t`, `/tmp` remains root:root 1777, Node 22/npm run, and logind refuses suspend.

Fedora 45 moved its vendor repository files to `/usr/share/dnf5/repos.d`; DNF reads those alongside administrator files in `/etc/yum.repos.d`. The effective defaults enable Fedora 45 base/updates and RPM Fusion 45 base/testing, with Fedora updates-testing disabled and the unavailable released RPM Fusion updates disabled. Ordinary `dnf upgrade --assumeno --best` resolves successfully and reports nothing to do. No Fedora 44 repository URLs or persistent testing-repository overrides were added. Reassess nginx/DAV ABI and matching libheif/freeworld versions before enabling additional testing updates.

All 22 intended containers are running without restart loops, and the checked Plex, Sonarr, Radarr, Lidarr, Prowlarr, Navidrome, Audiobookshelf, Grimmory, Feishin, Byparr, FlareSolverr and Ephemera endpoints return HTTP 200. Radarr required about six minutes for its existing ownership scan; the media guard recovered automatically when the API became ready. Transmission retains its 100 KB/s download cap; the Radarr client remains disabled, the Sonarr client enabled, and Auto-m4b stopped. Backup, parity and media-guard timers are active. After confirming that no Linux MD RAID arrays are configured, the unused `mdmonitor.service` was disabled, masked and cleared from failed state. Its mask is managed only on si; mdadm remains installed for OS dependencies. The system now has no failed units.

A fresh post-upgrade application backup completed at 19:29 HKT, snapshot `cf72bbe0f375d5b40f2c127bd5fa1dafbc874f98afa69d4141a464e108bc6857`. SQLite validation, the MariaDB logical dump and the server restic check passed. The independent encrypted fi copy completed at 19:30 HKT with the same source snapshot/time; `restic check --read-data` read all 188 packs without errors. Pre- and post-upgrade snapshots are retained. Operational evidence stays outside Git at `/mnt/data/disk42/.recovery-preservation/fc45-preparation-20261021/`.

The mergerfs bootstrap pin still targets Fedora 44; existing installations are preserved, while a fresh Fedora 45 bootstrap needs an explicitly selected, verified artifact. A full fresh-host recovery rehearsal remains outstanding.

## Outstanding follow-up audit (2026-10-21)

This list excludes media reacquisition. Zero failed systemd units does not prove every scheduled job or recovery path has run successfully.

- **SnapRAID content-format compatibility is the immediate blocker.** Fedora 45 upgraded SnapRAID 14.1 to 15.0. A read-only `snapraid status` fails with `Legacy content format is no longer supported` and instructs using SnapRAID 14.x `sync` to upgrade the content file. The installed daily sync/weekly scrub will remain blocked until a guarded 14.x conversion sync is completed and the result is checked with 15.x. Preserve content/config/parity recovery metadata and review the diff before any sync; do not recreate content files or force a sync. No conversion or parity write was performed during this audit.
- **First scheduled maintenance receipts:** neither `last-sync-success.json` nor `last-scrub-success.json` exists yet. After resolving the format blocker, verify the first daily 05:00 sync and Sunday 08:00 scrub, including writer pause/resume and failure reporting. Historical recovery scrubs are distinct from the new scheduled workflow.
- **Onsite connectivity/security:** public ingress and remote SSH/offsite pull from another network remain deferred until si returns onsite. Validate DNS, firewall and both media ingress and fi's remote backup route there. SELinux is currently permissive; an enforcing policy has not been validated.
- **Fresh Fedora 45 rebuild:** select and hash-verify an appropriate mergerfs bootstrap artifact, finish secret-input mapping (including Beets Bitwarden items) and declarative integration policy, and rehearse provisioning plus application restore on a disposable clean host. Existing backup content restore and an isolated MariaDB import have been tested; a complete new-machine service recovery has not. Avoid treating the historical audit checklist in SERVER-REBUILD.md as proof that already-implemented tools are still missing.
- **Recovery-key handoff:** fi's owner-only `~/.config/si-app-backup/RECOVERY-KEYS.txt` exists with mode 0600. Saving these recovery keys independently in Bitwarden remains a user handoff; vault storage was not verified. Never commit it.
- **Ephemera provider login:** the current boot logs report `Refresh token expired or invalid. Please re-authenticate.` Its web/health endpoint works and its queue remains paused; the affected provider session needs reauthentication before use.
- **First real archive import:** guard, Unpackerr and Plex notification connections are verified, but a new legitimate completed archive-to-Plex import has not yet been witnessed end to end. Observe the next eligible import without launching a backlog search for this test.
- **Auto-m4b remains deliberately held:** review its populated conversion queue and enable input backups before an explicit start.

The VIDEO destination currently contains 665 files / 361,976,855,220 bytes. All five files still present in fi's source VIDEO tree have matching destination sizes. This is a size-based check of the remaining source, not a full checksum verification of the original transfer.

## Restore application state and secrets

Recover the restic repository password out of band. It is intentionally excluded from its own backup; no restore tool generates or replaces it. Supply the repo path (server or fi copy) and an **exact full snapshot ID** from `restic snapshots --json`. Keep the password file root-readable only.

Use a fresh staging path on a filesystem with enough space; the command verifies restored contents and each database before any installation:

```fish
sudo python3 /etc/si-provision/restore.py stage \
  --repository /path/to/repository \
  --password-file /path/to/root-only-password \
  --snapshot FULL_64_CHARACTER_SNAPSHOT_ID \
  --stage /mnt/data/disk42/.recovery-preservation/restore-STAMP
```

Explicitly stop service timers/writers before installation. The tool refuses active containers or Plex, serializes with the backup/SnapRAID lock, and prechecks **all destinations before copying**. Default targets are appData, Audiobookshelf persistent metadata, native Plex state, MariaDB configuration, and m's SSH/age credentials. Destinations must be absent or empty: no forced overwrite, merge of existing app state, deletion or restore-on-update behavior.

```fish
sudo python3 /etc/si-provision/restore.py install \
  --stage /mnt/data/disk42/.recovery-preservation/restore-STAMP
```

Optional `--include` flags replace the default list. Supported extra targets: `/home/m/.config`, `/home/m/dockers`, `/home/m/.local/bin`, `/etc/nginx`, `/etc/pki/tls/private`, `/etc/pki/tls/certs`. Each still must be absent/empty. This deliberately refuses to overwrite an installed OS's TLS directories or managed files. Extract/reconcile individual existing-system secrets manually after review; never restore the whole `/etc` over a new OS. Staging itself contains secrets; keep it private and remove it after the verified recovery according to your retention policy.

After restoring (not before, as creating per-service directories would make appData nonempty):

```fish
sudo python3 /etc/si-provision/provision.py directories
sudo python3 /etc/si-provision/provision.py directories --apply
sudo python3 /etc/si-provision/provision.py beets --apply
```

The directory inventory records deployed bind-directory numeric owners/modes. Existing paths are preserved. A conflicting downloads or Plex symlink target aborts; move any package-created empty Plex directory out of the way explicitly after checking it. Beets seeding only fills missing custom source files; all YAML configuration and secrets are recovered through the application backup.

Start **only** the MariaDB container on a fresh data directory, allowing it to initialize. Then:

```fish
sudo python3 /etc/si-provision/restore.py import-mariadb \
  --stage /mnt/data/disk42/.recovery-preservation/restore-STAMP
```

The importer verifies the container's config mount, refuses existing application tables or other running applications, and records a receipt before importing. A partial import requires manual diagnosis; it is never retried automatically. The all-databases dump restores users/grants as well as application data; use an image version compatible with the backup. Restore the backup credentials before bringing dependent services up.

Validate Compose (`docker compose config --quiet`), paths, tokens and mounts, then create `/etc/si-provision/services-ready` and explicitly start the services/timers as described in SERVER-REBUILD.md. Keep Auto-m4b held.

## Image and customization updates

Compose uses the intended upstream tags; only explicitly chosen pins in Compose are retained (currently Unpackerr). There is no separate image-lock.json. Lidarr builds from its original nightly tag. Pull/recreate services deliberately and verify a current application backup before upgrades; database migrations may require restoring that backup to roll back. No automatic image-update service is added.

Nonsecret Beets plugin source and genre tools are under chezmoi `home/dockers/beets-customizations/`. Credentials belong in Bitwarden, not Git, including encrypted credential archives. Provisioning must resolve secrets from Bitwarden at runtime without printing them or writing them into repository sources. The proposed Beets credential archive is cancelled; none was exported. Existing application backups may contain credential-bearing application state; restoring that state is distinct from version-controlling credentials. A Beets-specific Bitwarden item mapping has not yet been implemented; do not invent item IDs or replace existing secrets.

Validation: 21 regression tests pass; account collisions, active writers, populated destinations, snapshot selection and existing mergerfs preservation are covered. This does not replace a complete fresh-host recovery rehearsal; no live restore was attempted.
