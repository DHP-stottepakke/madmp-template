#!/usr/bin/env bash
# Render every format of the template for one or more document contexts with dsw-tdk
# (the DSW 5 engine) and validate each output against its RDA DCS / OSTrails schema.
#
#   bash tools/check.sh CONTEXT.json [CONTEXT2.json ...]
#   LOCALE_PO=locales/nb.po bash tools/check.sh CONTEXT.json   # render with a translation
set -euo pipefail
cd "$(dirname "$0")/.."
[ $# -ge 1 ] || { echo "usage: $0 CONTEXT.json [...]" >&2; exit 2; }
. .venv/bin/activate
OUT=output
rm -rf "$OUT" && mkdir -p "$OUT"

declare -A FORMATS=(
  [dcs-1.3]="JSON (DCS 1.3)"
  [dcs-1.2]="JSON (DCS 1.2)"
  [dcs-1.1]="JSON (DCS 1.1)"
  [dcs-1.0]="JSON (DCS 1.0)"
  [ostrails]="JSON (OSTrails AP)"
)
PO_ARGS=()
[ -n "${LOCALE_PO:-}" ] && PO_ARGS=(--po "$LOCALE_PO")

status=0
for ctx in "$@"; do
  base=$(basename "$ctx" .json)
  for key in "${!FORMATS[@]}"; do
    target="$OUT/$base.$key.json"
    if ! dsw-tdk render . -c "$ctx" -F "${FORMATS[$key]}" -o "$target" -f "${PO_ARGS[@]}" >/dev/null; then
      echo "FAIL render $ctx (${FORMATS[$key]})"; status=1
    fi
  done
done
python tools/validate.py "$OUT"/*.json || status=1
exit $status
