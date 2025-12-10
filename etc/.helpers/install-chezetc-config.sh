#!/bin/sh

# This script installs the chezetc.toml config file.

set -e

# The directory where this script is located.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# The project root is two levels up from the script directory.
PROJECT_ROOT="$SCRIPT_DIR/../.."
CONFIG_DEST_DIR="$HOME/.config/chezetc"

echo "Generating chezetc.toml from template..."
mkdir -p "$CONFIG_DEST_DIR"
chezmoi execute-template < "$PROJECT_ROOT/chezetc.toml" > "$CONFIG_DEST_DIR/chezetc.toml"

echo "Successfully installed chezetc.toml to $CONFIG_DEST_DIR"
