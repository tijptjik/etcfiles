#!/bin/bash
# Essential packages installer for chezmoi initialization
# This script installs the basic packages needed for dotfiles management

set -euo pipefail

echo "Installing essential packages for /etc management..."

# Install essential packages
echo "Installing essential RPMs..."
sudo dnf install -y kitty fish git chezmoi age python-tomli python-tomli-w

# CHEZETC

if [ ! -d "$HOME/.tools/chezetc" ]; then
    echo "Installing Chezetc"
    git clone https://github.com/SilverRainZ/chezetc.git $HOME/.tools/chezetc
    chmod +x $HOME/.tools/chezetc/chezetc
else
    echo "Chezetc already installed."
fi

# CHEZETC CONFIG

# The directory where this script is located.
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DEST_DIR="$HOME/.config/chezetc"
ETC_SRC="$HOME/.local/share/chezetc"
ETC_DST="/etc"
ETC_CFG="$HOME/.config/chezetc/chezetc.toml"

echo "Generating chezetc.toml from template..."
echo $PROJECT_ROOT
echo $ETC_CFG  
mkdir -p "$CONFIG_DEST_DIR"
$HOME/.tools/chezetc/chezetc execute-template < "$PROJECT_ROOT/chezetc.toml" > $ETC_CFG

echo "Successfully installed chezetc.toml to $CONFIG_DEST_DIR"
