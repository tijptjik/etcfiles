#!/bin/sh
# Keep upstream configuration/state names while selecting the Systjik checkout.
export ETC_SRC="${ETC_SRC:-${XDG_DATA_HOME:-$HOME/.local/share}/systjik}"
exec /opt/chezetc/chezetc "$@"
