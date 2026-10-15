#!/usr/bin/env python3
"""Convert measured topology geometry to explicit propagation-only sensitivities."""
import argparse, csv, statistics
from array import array
from pathlib import Path

def quantile(xs,p):
 xs=sorted(xs); k=(len(xs)-1)*p; lo=int(k);hi=min(lo+1,len(xs)-1)
 return xs[lo]+(xs[hi]-xs[lo])*(k-lo)
def selected_5g_path_switch_ack_propagation(row, rtt_ms_per_km):
 # TS23.502 §4.9.1.2.2/.4, selected retained-context Xn branches;
 # AMF=SMF=PSA at pinned PSA. AMF–SMF and SMF–PSA RTTs are zero by
 # placement, not by protocol. d2 old-IUPF deletion is off the Ack path.
 level=int(row['level'])
 if level not in (1,2):raise ValueError(f"No grounded Ack path for level {level}")
 edge_term='old_iupf_pinned_psa_km' if level == 1 else 'new_iupf_pinned_psa_km'
 return rtt_ms_per_km*(float(row['target_pinned_psa_km'])+float(row[edge_term]))

def edge_5g_path_switch_ack_propagation(row, rtt_ms_per_km):
 # Same Ack path with AMF=SMF retained at the serving (old) I-UPF site:
 # d1 RAN-AMF only (N4 local); d2 adds SMF-target IUPF then SMF-PSA.
 # Favourable to 5G: AMF/SMF relocation and I-SMF insertion are ignored.
 level=int(row['level'])
 if level not in (1,2):raise ValueError(f"No grounded Ack path for level {level}")
 km=float(row['target_old_iupf_km'])
 if level==2:km+=float(row['old_new_iupf_km'])+float(row['old_iupf_pinned_psa_km'])
 return rtt_ms_per_km*km

def analyze(events, speed_km_ms=200., stretches=(1.,1.5,2.)):
 # Keep packed numeric samples instead of millions of Python row dictionaries.
 # Positive route stretch scales quantiles exactly; sort each scenario only once.
 names=[
  'selected5G_path_switch_ack_propagation',
  'selected5G_path_switch_ack_propagation_d1',
  'selected5G_path_switch_ack_propagation_d2',
  'edge5G_path_switch_ack_propagation_d1',
  'edge5G_path_switch_ack_propagation_d2',
  'target_RAN_to_colocated_AMF_SMF_RTT',
  'colocated_SMF_to_old_IUPF_RTT',
  'colocated_SMF_to_target_IUPF_RTT',
  'local_attachment_RTT',
  'peer_at_nearest_PSA_RTT',
  'peer_at_pinned_PSA_RTT',
  'local_then_nearest_peer_2exchange_propagation',
  'local_then_pinned_peer_2exchange_propagation',
 ]
 samples={name:array('d') for name in names}
 with open(events) as event_file:
  for r in csv.DictReader(event_file):
   pin=float(r['target_pinned_psa_km'])
   old=float(r['old_iupf_pinned_psa_km']);new=float(r['new_iupf_pinned_psa_km'])
   local=float(r['target_new_iupf_km']);nearest=float(r['target_nearest_psa_km'])
   ack=selected_5g_path_switch_ack_propagation(r,1.)
   edge=edge_5g_path_switch_ack_propagation(r,1.)
   vals=[ack,None,None,None,None,pin,old,new,local,nearest,pin,local+nearest,local+pin]
   d1=r['level']=='1';vals[1 if d1 else 2]=ack;vals[3 if d1 else 4]=edge
   for name,value in zip(names,vals):
    if value is not None:samples[name].append(value)
 if not samples[names[0]]:return []
 def q_sorted(xs,p):
  k=(len(xs)-1)*p;lo=int(k);hi=min(lo+1,len(xs)-1)
  return xs[lo]+(xs[hi]-xs[lo])*(k-lo)
 result=[]
 for name in names:
  vals=sorted(samples.pop(name));n=len(vals)
  if not n:continue
  med=q_sorted(vals,.5);p95=q_sorted(vals,.95);p99=q_sorted(vals,.99);mean=statistics.mean(vals)
  for stretch in stretches:
   if stretch<=0:raise ValueError('Route stretch must be positive')
   factor=2*stretch/speed_km_ms
   result.append(dict(scenario=name,route_stretch=stretch,samples=n,
    median_ms=med*factor,p95_ms=p95*factor,p99_ms=p99*factor,mean_ms=mean*factor))
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('events');ap.add_argument('--out',required=True);a=ap.parse_args()
 rows=analyze(a.events)
 if rows:
  with open(a.out,'w') as f:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 else:Path(a.out).write_text('No events; no latency distribution inferred.\n')
