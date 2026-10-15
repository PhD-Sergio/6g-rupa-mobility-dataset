#!/usr/bin/env bash
set -euo pipefail
# One Julia process per worker; scheduler splits rows into bounded shards.
root=$(cd "$(dirname "$0")/.." && pwd)
first=${1:?first row}; last=${2:?last row}; out=${3:?results root}
export JULIA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
for ((row=first; row<=last; row++)); do
  target="$out/row-$(printf '%03d' "$row")"
  [[ -f "$target/provenance.toml" ]] && continue
  mkdir -p "$target"
  nice -n 15 julia --startup-file=no --project="$root" "$root/scripts/latency_run.jl" "$root/latency-matrix.csv" "$row" "$target" > "$target/run.log" 2>&1
done
