# Managed /etc with chezetc

Setup the system environment before running the [dotfiles](https://github.com/tijptjik/dotfiles) setup with chezmoi.

## Manages

- DNF Repositories
- Packages
  - RPM
  - Flatpak
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
