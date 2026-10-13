#!/usr/bin/env bash
## Managed by Ansible. Local changes will be overwritten.
## Emit OK when no pgcleanup.py process has reached the runtime threshold.

set -euo pipefail

threshold=${1:-36000}
if ! [[ $threshold =~ ^[0-9]+$ ]]; then
    echo "THRESHOLD_SECONDS must be a non-negative integer" >&2
    exit 2
fi

ok=1
while read -r pid; do
    # etimes is wall-clock elapsed time in seconds. Skip processes that exited.
    runtime=$(ps -o etimes= -p "$pid") || continue
    runtime=${runtime//[[:space:]]/}
    [[ -n $runtime ]] || continue
    if ((runtime >= threshold)); then
        ok=0
        break
    fi
done < <(pgrep -f '[p]gcleanup\.py' || true)

printf 'pgcleanup-watchdog ok=%si\n' "$ok"
