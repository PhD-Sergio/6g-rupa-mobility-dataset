#!/usr/bin/env python3
"""Summarize per-run propagation quantiles by country.

Per-run files hold quantiles, not samples, so we report the range across runs of
each run's median and p95; no pooled quantile is inferred.
"""
import csv, sys, tomllib
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCENARIOS = [
    'selected5G_path_switch_ack_propagation_d1',
    'selected5G_path_switch_ack_propagation_d2',
    'edge5G_path_switch_ack_propagation_d1',
    'edge5G_path_switch_ack_propagation_d2',
    'local_attachment_RTT',
    'peer_at_nearest_PSA_RTT',
    'peer_at_pinned_PSA_RTT',
]

def load(base):
    runs = []
    for prov in sorted(base.glob('*/row-*/provenance.toml')):
        sens = prov.parent/'sensitivity.csv'
        if not sens.exists() or sens.read_text().startswith('No events'):
            continue
        meta = tomllib.loads(prov.read_text())
        rows = {(r['scenario'], float(r['route_stretch'])): r for r in csv.DictReader(sens.open())}
        runs.append((prov.parent.name, meta, rows))
    return runs

def main(stretch=1.0):
    runs = load(ROOT/'results'/'production')
    seen = {}
    for name, meta, rows in runs:
        seen.setdefault(name, (meta, rows))
    by_country = defaultdict(list)
    for meta, rows in seen.values():
        by_country[meta['country']].append(rows)
    w = csv.writer(sys.stdout)
    w.writerow(['country', 'runs', 'scenario', 'stretch', 'median_lo', 'median_hi', 'p95_lo', 'p95_hi', 'samples'])
    for country in sorted(by_country):
        group = by_country[country]
        for sc in SCENARIOS:
            hits = [r[sc, stretch] for r in group if (sc, stretch) in r]
            if not hits:
                continue
            med = [float(h['median_ms']) for h in hits]
            p95 = [float(h['p95_ms']) for h in hits]
            w.writerow([country, len(hits), sc, stretch, f'{min(med):.2f}', f'{max(med):.2f}',
                        f'{min(p95):.2f}', f'{max(p95):.2f}', sum(int(h['samples']) for h in hits)])
    print(f'# distinct runs: {len(seen)}', file=sys.stderr)

if __name__ == '__main__':
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 1.0)
