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
    sources and rebuilds before and after system updates, so it stays aligned
    with Fedora Nginx without the GetPageSpeed repository.
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
$HOME/.tools/chezetc/chezetc apply
```
## Todo

- Reenable Sublime Text, once the [GPG key digest issue is fixed](https://discussion.fedoraproject.org/t/sublime-text-not-able-to-install-in-fedora-43/170396/8)
