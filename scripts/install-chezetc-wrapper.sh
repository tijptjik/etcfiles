#!/usr/bin/env bash
# Install the wrapper separately from the per-user system configuration checkout.
set -euo pipefail
if [[ -x /opt/chezetc/chezetc ]]; then
    exit 0
fi
staging=$(mktemp -d)
trap 'rm -rf -- "$staging"' EXIT
if [[ -f "$HOME/.tools/chezetc/chezetc" ]]; then
    cp -a "$HOME/.tools/chezetc/." "$staging/"
else
    git clone https://github.com/SilverRainZ/chezetc.git "$staging"
    git -C "$staging" checkout ce9fc92f2fd694eec946f60c7d8142d3e7c84f3e
fi
python3 - "$staging/chezetc" <<'PY'
from pathlib import Path
import re
import sys
p = Path(sys.argv[1])
s = p.read_text()
pattern = r'(?m)^sudo --preserve-env=([A-Za-z0-9_,]+)(?= --)'
matches = list(re.finditer(pattern, s))
if len(matches) != 1:
    raise SystemExit('Unrecognized Chezetc sudo allowlist')
m = matches[0]
names = m.group(1).split(',')
for name in ('TJIKUP_COLOR', 'TJIKUP_NO_SPIN', 'TJIKUP_REPORT_FILE', 'TJIKUP_SKIP_PREFLIGHT', 'TJIKUP_COLUMNS'):
    if name not in names:
        names.append(name)
p.write_text(s[:m.start(1)] + ','.join(names) + s[m.end(1):])
PY
# A launcher (not a symlink) preserves upstream's dirname-based resource lookup.
printf '#!/bin/sh\nexec /opt/chezetc/chezetc "$@"\n' > "$staging/launcher"
sudo test ! -e /opt/chezetc
if [[ -e /usr/local/bin/chezetc || -L /usr/local/bin/chezetc ]]; then
    echo 'Refusing to replace existing /usr/local/bin/chezetc' >&2
    exit 1
fi
sudo mkdir -p /opt/chezetc /usr/local/bin
sudo cp -a "$staging/." /opt/chezetc/
sudo chown -R root:root /opt/chezetc
sudo chmod -R go-w /opt/chezetc
sudo chmod 755 /opt/chezetc/chezetc
sudo install -o root -g root -m 755 "$staging/launcher" /usr/local/bin/chezetc
