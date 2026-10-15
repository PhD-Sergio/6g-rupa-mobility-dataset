# ICC 2027 additional runs

Every run uses PLMN-GraphSim at commit `6bcbc7e7d33f10705803c2454695070140d3020f`
(`simulator/BASE_COMMIT`) plus the observation-only changes in
`simulator/icc-instrumentation.patch` and the new files next to it. The changes add a
per-handover event record (distances between the target gNB, serving I-UPFs and
anchors, the session count and, for later runs, the simulation time) and optional
switches for mixed speed profiles, handover hysteresis and the users represented per
agent. The event record makes no random-number calls, and all switches are off by
default.

Each run is seeded. `provenance.toml` in every run directory records the seed, input
file SHA-256 digests, the simulator commit, the hashes of the modified source files, the
Julia version, the handover count and, where recorded, the simulator's own 5G write
counter (`core_writes_5g`).

## Run sets (`runs/`)

| Directory | Matrix (`simulator/`) | Content |
|---|---|---|
| `production` | `latency-matrix.csv` | 27 fields × 3 speed profiles × 3 seeds (243 runs): round-trip quantiles and per-UPF write load |
| `anchor` | `anchor-matrix.csv` | Spain (Movistar) and US (Verizon) at 2, 10, 20, 40 anchors, plus Spain at 5 anchors as a determinism check (81 runs) |
| `peak`, `peakfull` | `peak-matrix.csv`, `peakfull-matrix.csv` | Timestamped runs for per-second write load |
| `mix` | `mix-matrix.csv` | Mixed speed profiles within one population |
| `real` | `real-matrix.csv` | 70/20/10 % pedestrian/urban/highway mix with a 3 dB A3-style handover offset |
| `sens` | `sens-matrix.csv` | Users represented per agent (scale convergence) |

Per run: `sensitivity.csv` (propagation RTT quantiles per scenario and route stretch,
from `scripts/analyze_latency.py`), `writes.json` (5G writes in total and at the busiest
I-UPF, from `scripts/reduce_writes.py`), `provenance.toml` and `run.log`.

Raw per-event CSVs (about 190 million rows for `production` alone) are not included.
They are regenerated exactly by rerunning a matrix row: handover counts matched the
earlier runs with the same seed in every determinism check.

## Summaries (`summaries/`)

- `latency-summary-s1.csv`, `latency-summary-s2.csv`: per-country range of per-run
  median and p95 RTT, route stretch 1 and 2 (`scripts/aggregate_latency.py`).
- `control-projection.csv`: projected 5G core-function receptions and BGP MUP binding
  updates per represented hour (`scripts/control_projection.py`).
- `peak-summary.csv`: per-second write load summary (`scripts/analyze_peak.py`).

## Method notes

`LATENCY.md` documents the round-trip model and its assumptions: geodesic distance,
fiber at 200 km/ms, AMF and SMF placed at the pinned anchor or at the serving I-UPF
site, propagation only (no processing, queueing or radio interruption).

A 5G move counts one rule rewrite per session at the serving UPF, scaled by the users
per agent; this is the simulator's own rule and a lower bound for I-UPF changes.

## Reproduce one run

```
git clone https://github.com/Fundacio-i2CAT/PLMN-GraphSim && cd PLMN-GraphSim
git checkout 6bcbc7e7d33f10705803c2454695070140d3020f
git apply ../icc/simulator/icc-instrumentation.patch
cp ../icc/simulator/DistanceEvents.jl src/Simulation/
cp ../icc/simulator/latency_run.jl ../icc/simulator/latency_worker.sh scripts/
cp ../icc/simulator/*-matrix.csv .
julia --project=. scripts/latency_run.jl latency-matrix.csv <row> <output_dir>
python3 ../icc/scripts/analyze_latency.py <output_dir>/events.csv --out <output_dir>/sensitivity.csv
python3 ../icc/scripts/reduce_writes.py <output_dir>
```

Input fields are under `../sweep/inputs/` (place them under `data/<country>/` as
described in `../sweep/scripts/reproduce.md`).
