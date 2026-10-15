#!/usr/bin/env python3
"""Per-UPF 5G forwarding-rule writes from captured handover events.

Applies the simulator's own rule (Handover.jl): each handover rewrites every
session's tunnel state at the serving UPF, scaled by the users per agent.
So an event adds session_count * scale writes to its new I-UPF. Reports the
run total and the load on the busiest I-UPF as an average rate over the run.
"""
import argparse, gzip, json
from collections import Counter
from pathlib import Path

def quantile(xs, p):
    xs = sorted(xs); k = (len(xs)-1)*p; lo = int(k); hi = min(lo+1, len(xs)-1)
    return xs[lo]+(xs[hi]-xs[lo])*(k-lo)

def scalar_toml(path):
    # Top-level 'key = value' pairs only; the servers lack tomllib (Python < 3.11).
    out = {}
    for line in Path(path).read_text().splitlines():
        if line.startswith('['): break
        if ' = ' in line:
            k, v = line.split(' = ', 1); out[k.strip().strip('"')] = v.strip().strip('"')
    return out

def reduce(events, scale, duration_s):
    per_upf = Counter(); per_sec = Counter(); total = 0; n = 0; d2 = 0
    with open(events) as f:
        head = f.readline().rstrip('\n').split(',')
        i_s, i_new, i_lvl = head.index('session_count'), head.index('new_iupf'), head.index('level')
        i_t = head.index('t_s') if 't_s' in head else None
        for line in f:
            c = line.split(',')
            w = int(c[i_s])*scale
            per_upf[c[i_new]] += w; total += w; n += 1
            if i_t is not None:
                per_sec[(c[i_new], int(float(c[i_t])))] += w
            d2 += c[i_lvl] == '2'
    if not n:
        return None
    loads = list(per_upf.values())
    busiest, peak = per_upf.most_common(1)[0]
    extra = {}
    if per_sec:
        (pu, ps), pw = per_sec.most_common(1)[0]
        extra = dict(peak_second_upf=pu, peak_second=ps, peak_second_writes=pw, _per_sec=per_sec)
    return dict(**extra, events=n, d2_share=d2/n, writes_total=total, upfs_written=len(loads),
                busiest_upf=busiest, busiest_writes=peak,
                busiest_rate_per_s=peak/duration_s, mean_rate_per_s=total/len(loads)/duration_s,
                p50_upf_writes=quantile(loads, .5), p99_upf_writes=quantile(loads, .99))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('rundir'); ap.add_argument('--scale', type=int, default=1000)
    a = ap.parse_args(); run = Path(a.rundir)
    prov = scalar_toml(run/'provenance.toml')
    scale = int(prov.get('scale_factor', a.scale))  # recorded since the scale option
    out = reduce(run/'events.csv', scale, float(prov['duration_s']))
    per_sec = out.pop('_per_sec', None) if out else None
    if per_sec:
        # Sparse (upf, second, writes) series, so profiles can be mixed afterwards.
        with gzip.open(run/'upf_seconds.csv.gz', 'wt') as g:
            g.write('upf,second,writes\n')
            for (u, t), w in sorted(per_sec.items()): g.write(f'{u},{t},{w}\n')
    if out and 'core_writes_5g' in prov:
        # Cross-check against the simulator's own counter where recorded.
        out['simulator_writes'] = int(prov['core_writes_5g'])
        out['matches_simulator'] = out['simulator_writes'] == out['writes_total']
    (run/'writes.json').write_text(json.dumps(out, indent=1)+'\n')
