#!/usr/bin/env python3
"""Peak-second writes at the busiest I-UPF: single profiles, post-hoc mixes, native mixes.

Single-profile runs (results/peak, results/peakfull) hold a sparse (upf, second,
writes) series. A post-hoc mix weights the three profile runs of one field that
share a seed index (seed % 10), each run representing the full population.
Native mixed runs (results/mix) simulate one population with per-agent profiles.
"""
import csv, gzip, sys, tomllib
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MIXES = {'80/15/5': (.80, .15, .05), '70/20/10': (.70, .20, .10), '50/30/20': (.50, .30, .20)}
PROFILE = {'RandomWaypoint(5.0, 0.0, 2.0)': 'pedestrian', 'RandomWaypoint(50.0, 0.0, 20.0)': 'urban',
           'GaussMarkov(120.0, 0.85, 5.0)': 'highway'}

def series(run):
    out = Counter()
    with gzip.open(run/'upf_seconds.csv.gz', 'rt') as f:
        next(f)
        for line in f:
            u, t, w = line.rstrip().split(','); out[(u, int(t))] += int(w)
    return out

def peak(s):
    return max(s.values()) if s else 0

def main():
    runs = {}
    for base in ('peak', 'peakfull'):
        for run in sorted((ROOT/'results'/base).glob('row-*')):
            if not (run/'upf_seconds.csv.gz').exists(): continue
            m = tomllib.loads((run/'provenance.toml').read_text())
            key = (m['country'], m['field'], m['operator'], PROFILE[m['mobility_model']], int(m['seed']) % 10)
            runs[key] = (run, m)
    # Determinism: same seed must reproduce the latency sweep's handover count.
    lat = {}
    for p in (ROOT/'results'/'production').glob('*/row-*/provenance.toml'):
        m = tomllib.loads(p.read_text()); lat[(m['field'], m['operator'], int(m['seed']))] = int(m['handovers'])
    same = sum(lat.get((m['field'], m['operator'], int(m['seed']))) == int(m['handovers']) for _, m in runs.values())
    print(f'# single-profile runs {len(runs)}; handovers equal latency sweep in {same}', file=sys.stderr)

    w = csv.writer(sys.stdout)
    w.writerow(['country', 'field', 'operator', 'population', 'seed_index', 'peak_second_writes', 'run_avg_busiest', 'source'])
    fields = sorted({k[:3] for k in runs})
    for f in fields:
        for idx in sorted({k[4] for k in runs if k[:3] == f}):
            prof = {p: runs.get(f+(p, idx)) for p in ('pedestrian', 'urban', 'highway')}
            if any(v is None for v in prof.values()): continue
            ser = {p: series(r) for p, (r, _) in prof.items()}
            for p in prof:
                w.writerow(list(f)+[p, idx, peak(ser[p]), '', 'single'])
            for name, wt in MIXES.items():
                mixed = Counter()
                for p, k in zip(('pedestrian', 'urban', 'highway'), wt):
                    for key, v in ser[p].items(): mixed[key] += k*v
                w.writerow(list(f)+[name, idx, round(peak(mixed)), '', 'posthoc'])
    mixrows = list(csv.DictReader((ROOT/'mix-matrix.csv').open()))
    for run in sorted((ROOT/'results'/'mix').glob('row-*')):
        if not (run/'upf_seconds.csv.gz').exists(): continue
        r = mixrows[int(run.name[4:])-1]
        w.writerow([r['country'], r['field'], r['operator'], r['mobility_model'][4:], int(r['seed']) % 10,
                    peak(series(run)), '', 'native'])

if __name__ == '__main__':
    main()
