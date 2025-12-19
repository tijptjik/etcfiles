#!/bin/bash
# Essential packages installer for chezmoi initialization
# This script installs the basic packages needed for dotfiles management

set -euo pipefail

# Install essential packages
echo "[INSTALL] Essential packages for /etc management..."
sudo dnf install -y kitty fish git chezmoi age python-tomli python-tomli-w

# CHEZETC

if [ ! -d "$HOME/.tools/chezetc" ]; then
    echo "[INSTALL] Chezetc"
    git clone https://github.com/SilverRainZ/chezetc.git $HOME/.tools/chezetc
    chmod +x $HOME/.tools/chezetc/chezetc
else
    echo "[SKIP] Chezetc is already installed."
fi

# CHEZETC CONFIG

# The directory where this script is located.
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DEST_DIR="$HOME/.config/chezetc"
ETC_DST="/etc"
ETC_SRC="$HOME/.local/share/chezetc"
ETC_CFG="$CONFIG_DEST_DIR/chezetc.toml"

echo "[CREATE] chezetc.toml from template..."
mkdir -p "$CONFIG_DEST_DIR"
$HOME/.tools/chezetc/chezetc execute-template < "$PROJECT_ROOT/chezetc.toml" > $ETC_CFG

echo "[SUCCESS] Installed chezetc.toml to $CONFIG_DEST_DIR"
