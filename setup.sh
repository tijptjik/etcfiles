#!/bin/bash
# Essential packages installer for chezmoi initialization
# This script installs the basic packages needed for dotfiles management

set -euo pipefail

step_ok() {
    if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
        gum style --foreground 42 --bold "OK   $*"
    else
        echo "OK   $*"
    fi
}

step_skip() {
    if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
        gum style --foreground 244 --bold "SKIP $*"
    else
        echo "SKIP $*"
    fi
}

step_fail() {
    if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
        gum style --foreground 196 --bold "FAIL $*"
    else
        echo "FAIL $*"
    fi
}

step_run() {
    local title="$1"
    shift

    set +e
    if command -v gum >/dev/null 2>&1 && [ -t 1 ]; then
        gum spin --show-error --title "$title" -- "$@"
    else
        echo "RUN  $title"
        "$@"
    fi

    local status=$?
    set -e
    if [ "$status" -eq 0 ]; then
        step_ok "$title"
    else
        step_fail "$title"
    fi

    return "$status"
}

# Install essential packages
step_run "Install essential packages for /etc management" sudo dnf install -y kitty fish git chezmoi age uv gum

# CHEZETC

if [ ! -d "$HOME/.tools/chezetc" ]; then
    step_run "Clone chezetc" git clone https://github.com/SilverRainZ/chezetc.git "$HOME/.tools/chezetc"
    step_run "Make chezetc executable" chmod +x "$HOME/.tools/chezetc/chezetc"
    step_run "Install TOML extensions" uv pip install tomli tomli_w
else
    step_skip "Chezetc already installed"
fi

# CHEZETC CONFIG

# The directory where this script is located.
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
CONFIG_DEST_DIR="$HOME/.config/chezetc"
ETC_DST="/etc"
ETC_SRC="$HOME/.local/share/chezetc"
ETC_CFG="$CONFIG_DEST_DIR/chezetc.toml"

step_run "Create chezetc config directory" mkdir -p "$CONFIG_DEST_DIR"
if chezmoi execute-template < "$PROJECT_ROOT/chezetc.toml" > "$ETC_CFG"; then
    step_ok "Render chezetc config"
else
    step_fail "Render chezetc config"
    exit 1
fi

step_ok "Installed chezetc.toml to $CONFIG_DEST_DIR"
