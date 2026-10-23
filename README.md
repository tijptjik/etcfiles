# Managed /etc with chezetc

Setup the system environment before running the [dotfiles](https://github.com/tijptjik/dotfiles) setup with chezmoi.

## Manages

- DNF Repositories
- Tailscale package and daemon lifecycle
- Packages
  - RPM
  - Flatpak
- Fedora release upgrades, with a seven-day reminder after declining an available release
- Local builds that are temporarily required for upstream compatibility
  - Waybar is built from `master` on Hyprland clients until an official release
    containing the Lua workspace-dispatch fix is available from Fedora.
    Chezetc checks for Waybar `0.16.0+` on every apply; once found, it stops the
    local build and asks for this temporary step to be removed.
  - The server builds the WebDAV extension as a local RPM from the pinned
    `nginx-dav-ext-module` v3.0.0 source. It uses Fedora's `nginx-mod-devel`
    sources and rebuilds after system updates, so it stays aligned with Fedora
    Nginx without the GetPageSpeed repository. Fedora's automatic live-upgrade
    trigger is held until the rebuilt module passes `nginx -t`; Chezetc then
    upgrades the running master or starts Nginx if it was inactive. The ABI is read
    from the installed `nginx -v` binary, so duplicate RPM records after an
    interrupted update cannot produce a combined version string. A current
    module is accepted only when the full `nginx -t` check passes, including
    the stream module; rebuilding requires matching Fedora header macros.
- `fstab`

## Supported Hosts

- `fi` : Desktop
- `li` : Laptop
- `si` : Server

## Setup

This script will (1) install required dependencies, (2) clone the `chezetc` repo to `$HOME/.tools/chezetc`, (3) install the configuration to `$HOME/.config/chezetc/chezetc.toml`.

```sh
git clone git@github.com:tijptjik/etcfiles.git $HOME/.local/share/chezetc
$HOME/.local/share/chezetc/setup.sh
```

Now you can manage your `/etc` files with `chezetc`.

```sh
# chezetc is added to the path in the dotfiles, so it is not 
# available before you've set them up with chezmoi.
/opt/chezetc/chezetc apply
```
## Validation

Run `bash scripts/validate.sh` with Bash, Fish, and Python 3 installed. It checks
shell syntax and tests setup with isolated paths and stubbed install commands.
If Chezmoi and its configuration are available, it also renders Fish script
templates for the current host without executing them. Set `CHEZETC_CONFIG` to
use a different configuration. Skipped rendering is reported explicitly.

## Todo

- Reenable Sublime Text, once the [GPG key digest issue is fixed](https://discussion.fedoraproject.org/t/sublime-text-not-able-to-install-in-fedora-43/170396/8)

## Server recovery and reproducibility

See [SERVER-REBUILD.md](SERVER-REBUILD.md) for the service inventory, version-control boundaries, storage guards, restore order, and remaining work toward unattended provisioning. Do not use a blanket apply as a fresh-server recovery procedure yet.


## Client login and screen locking

Chezetc manages `/etc/gdm/custom.conf`: fi and li automatically log in as `io`.
Their home configuration enables `hyprlock-login.service` with the graphical
session, after Hyprland exports its Wayland display. The service launches
`~/.local/bin/tailscale-lock`, which starts Hyprlock. Install and verify that
home configuration before relying on autologin; GDM does not itself wait for
Hyprlock to acquire the session lock.

Select **Hyprland (uwsm-managed)** for the account's saved GDM session. Confirm
`systemctl --user is-enabled hyprlock-login.service` and that `/usr/bin/hyprlock`
and `~/.local/bin/tailscale-lock` exist. Apply the GDM file narrowly with
`chezetc apply --exclude scripts /etc/gdm/custom.conf`. It takes effect on the
next boot/login; do not restart GDM inside a working desktop session.

The server retains its existing automatic login as `m`.

### Hyprvoice (clients)

Chezetc installs the pinned upstream v1.0.2 x86_64 release into
`/opt/hyprvoice/v1.0.2/hyprvoice`, verifying its SHA-256 before installation.
`/usr/local/bin/hyprvoice` and the desktop user's `~/.local/bin/hyprvoice`
point to that binary. Existing unmanaged user binaries are preserved under
`~/.local/state/chezetc/hyprvoice/`. User configuration, shortcuts and the user
service remain managed by the home Chezmoi repository. The installer does not
restart a running dictation session. Update the release version and checksum
together when upgrading. The source checkout in `~/.tools` is not required.

### Tippecanoe (clients)

Every Tjikup apply checks the latest stable `felt/tippecanoe` GitHub release.
Chezetc builds a new release in temporary storage, runs upstream unit tests and
creates a sample MBTiles archive before installing into `/opt/tippecanoe/<tag>`.
The six tools are exposed through `/usr/local/bin`; existing unmanaged executables
are never overwritten. Matching installations are reused. Previous release
directories remain available for rollback. A network or build failure is reported
and leaves the active installation in place. No `.tools` source checkout is needed.
