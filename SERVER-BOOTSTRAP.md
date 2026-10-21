# si provisioning and restore commands

Implemented 2026-10-21. These are explicit commands, not apply hooks. **Do not run the restore sequence on the current healthy server.** Live application databases/configuration remain authoritative.

## Routine updates (`tjikup`)

`tjikup` pulls/pushes source and applies chezmoi and chezetc. Package upgrades, Docker enable/start and nginx module rebuilds retain their normal behavior. Storage guards protect service startup. Provisioning and restore tools are never invoked by these hooks. Review diffs before applying substantial changes; ordinary maintenance can still update packages and managed files.

Neither provisioning nor restoration is an apply hook. Transmission's mutable settings.json is ignored on the server. Application databases and passwords are not template targets. Existing mergerfs is not replaced, existing accounts are not renumbered, existing directory ownership/modes are not recursively changed, and existing Beets files are not overwritten. Auto-m4b remains opt-in.

## Account and storage bootstrap

Run the planning form first; add `--apply` to make the planned changes:

```fish
sudo python3 /etc/si-provision/provision.py accounts
sudo python3 /etc/si-provision/provision.py accounts --apply
sudo python3 /etc/si-provision/provision.py mergerfs
sudo python3 /etc/si-provision/provision.py mergerfs --apply
```

Mergerfs 2.42.0 is locked to the upstream Fedora 43 x86_64 RPM and publisher SHA256. Other OS/architectures fail closed. Existing installations are preserved regardless of version. This avoids upgrading si's active 2.32.6 mount. The new package was downloaded and hash-verified, but a fresh mounted-array rehearsal is still required.

Install the server package declarations deliberately during bootstrap (including Docker, Compose, SnapRAID, Plex, rsync, restic and PyYAML); normal server tjikup package maintenance remains enabled. Keep Docker and Plex stopped until mounts and restored state are ready. Use the selective fstab helper described in SERVER-REBUILD.md, then verify:

```fish
sudo python3 /etc/si-provision/storage.py --check
```

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

Start **only** the pinned MariaDB container on a fresh data directory, allowing it to initialize. Then:

```fish
sudo python3 /etc/si-provision/restore.py import-mariadb \
  --stage /mnt/data/disk42/.recovery-preservation/restore-STAMP
```

The importer verifies the container's config mount, refuses existing application tables or other running applications, and records a receipt before importing. A partial import requires manual diagnosis; it is never retried automatically. The all-databases dump restores users/grants as well as application data; use the compatible pinned image. Restore the backup credentials before bringing dependent services up.

Validate Compose (`docker compose config --quiet`), paths, tokens and mounts, then create `/etc/si-provision/services-ready` and explicitly start the services/timers as described in SERVER-REBUILD.md. Keep Auto-m4b held.

## Image and customization updates

Compose image references are immutable digests from the deployed containers; `home/dockers/image-lock.json` records them. The locally built Lidarr base is a separately resolved fixed registry digest, rather than an inferred digest for the old local build; its ffmpeg package dependency is still fetched during build. A bit-for-bit reproducible custom image would require publishing and pinning the built artifact too. No image pulls or container recreation were done here.

Nonsecret Beets plugin source and genre tools are under chezmoi `home/dockers/beets-customizations/`. Credentials belong in Bitwarden, not Git, including encrypted credential archives. Provisioning must resolve secrets from Bitwarden at runtime without printing them or writing them into repository sources. The proposed Beets credential archive is cancelled; none was exported. Existing application backups may contain credential-bearing application state; restoring that state is distinct from version-controlling credentials. A Beets-specific Bitwarden item mapping has not yet been implemented; do not invent item IDs or replace existing secrets.

Validation: 21 regression tests pass; account collisions, active writers, populated destinations, snapshot selection and existing mergerfs preservation are covered. This does not replace a complete fresh-host recovery rehearsal; no live restore was attempted.
