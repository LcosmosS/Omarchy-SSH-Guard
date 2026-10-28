#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.."
python3 -m unittest discover -s tests -v
python3 -m py_compile bin/omarchy-guard bin/omarchy-guard-evidence
python3 -m json.tool manifest.json >/dev/null
python3 -m json.tool schemas/ssh-evidence-v2.schema.json >/dev/null
if command -v omarchy >/dev/null 2>&1; then
  omarchy plugin validate .
else
  echo "Omarchy unavailable: live shell validation must be done on Omarchy." >&2
fi
