"""Project logical control costs over the archived national event counts.

One active PDU session per modeled UE; scale=1000, duration=1200s.
Historical byte columns recover integer event classes, not new byte claims.
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'sweep/results/national-sweep.csv'
OUT = ROOT / 'summaries/control-projection.csv'
OUT.parent.mkdir(parents=True, exist_ok=True)
rows = []
for row in csv.DictReader(SOURCE.open()):
    h = int(row['handovers'])
    residual = int(row['sigma_5g_bytes']) - 600*h
    assert residual >= 0 and residual % 550 == 0
    h2 = residual // 550
    h1 = h-h2
    assert 0 <= h2 <= h and int(row['sigma_6grupa_bytes']) == 200*h
    row.update(h1_exact=h1, h2_exact=h2,
               logical_tx_5g_one_pdu=6*h1+10*h2,
               core_rx_5g_one_pdu=5*h1+9*h2,
               core_rx_5g_hour_population=(5*h1+9*h2)*3000,
               core_rx_5g_optional_hour_population=(5*h1+11*h2)*3000,
               mup_st1_replacements_one_prefix=h,
               mup_pe_updates_hour_population_k1=h*3000,
               mup_pe_updates_hour_population_k2=h*6000,
               mup_pe_updates_hour_population_k4=h*12000,
               mup_pe_updates_hour_population_k8=h*24000)
    rows.append(row)
with OUT.open('w') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
    writer.writeheader(); writer.writerows(rows)
for key in ['core_rx_5g_hour_population','mup_pe_updates_hour_population_k1']:
    values = [int(r[key]) for r in rows]
    print(key, 'min', min(values), 'max', max(values))
print('Verified integer depth counts for', len(rows), 'runs')
