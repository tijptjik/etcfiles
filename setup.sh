#!/bin/bash
# Essential packages installer for chezmoi initialization
# This script installs the basic packages needed for dotfiles management

set -euo pipefail

echo "Installing essential packages for /etc management..."

# Install essential packages
echo "Installing essential RPMs..."
sudo dnf install -y kitty fish git chezmoi age

# CHEZETC

if [ ! -d "$HOME/.tools/chezetc" ]; then
    echo "Installing Chezetc"
    git clone https://github.com/SilverRainZ/chezetc.git $HOME/.tools/chezetc
else
    echo "Chezetc already installed."
fi

# CHEZETC CONFIG

# The directory where this script is located.
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DEST_DIR="$HOME/.config/chezetc"

echo "Generating chezetc.toml from template..."
mkdir -p "$CONFIG_DEST_DIR"
chezmoi execute-template < "$PROJECT_ROOT/chezetc.toml" > "$CONFIG_DEST_DIR/chezetc.toml"

echo "Successfully installed chezetc.toml to $CONFIG_DEST_DIR"
