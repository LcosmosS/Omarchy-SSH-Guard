#!/usr/bin/env bash
set -euo pipefail
# Copy only a user-level read-only tool. Never sudo this script.
if [ "$(id -u)" -eq 0 ]; then
  echo "Refusing root installation of a user-writable CLI" >&2
  exit 1
fi
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
install -d -m 700 "$HOME/.local/bin"
install -m 755 "$ROOT/bin/omarchy-guard" "$HOME/.local/bin/omarchy-guard"
printf '%s\n' "Installed unprivileged CLI: $HOME/.local/bin/omarchy-guard"   "Run: omarchy-guard audit" "Do not run this user-writable program via sudo."   "To install the optional widget: review code, then omarchy plugin validate ."
