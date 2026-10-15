import csv
import tempfile
import unittest
from pathlib import Path
from analyze_latency import analyze, selected_5g_path_switch_ack_propagation, edge_5g_path_switch_ack_propagation

class LatencyAnalysisTests(unittest.TestCase):
 def setUp(self):
  self.row=dict(level=1,target_pinned_psa_km=100,old_iupf_pinned_psa_km=200,
                new_iupf_pinned_psa_km=300,target_new_iupf_km=10,target_nearest_psa_km=20,
                target_old_iupf_km=10,old_new_iupf_km=0)
 def test_branch_uses_correct_n4_endpoint(self):
  # v=200km/ms: 100km RTT is1ms, d1 adds old-IUPF2ms.
  self.assertEqual(selected_5g_path_switch_ack_propagation(self.row,.01),3.)
  # d2 establishes target IUPF3ms; old deletion2ms must not be added.
  self.row['level']=2
  self.assertEqual(selected_5g_path_switch_ack_propagation(self.row,.01),4.)
  self.assertEqual(selected_5g_path_switch_ack_propagation(self.row,.02),8.)
 def test_distribution_and_placement_scenarios(self):
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'events.csv'
   with path.open('w') as f:
    w=csv.DictWriter(f,fieldnames=self.row.keys());w.writeheader();w.writerow(self.row)
    w.writerow(dict(self.row,level=2))
   rows=analyze(path,stretches=(1.,2.))
  lookup={(r['scenario'],r['route_stretch']):r for r in rows}
  mix=lookup['selected5G_path_switch_ack_propagation',1.]
  self.assertEqual(mix['samples'],2)
  self.assertEqual(mix['median_ms'],3.5)
  self.assertAlmostEqual(mix['p95_ms'],3.95)
  self.assertEqual(lookup['target_RAN_to_colocated_AMF_SMF_RTT',1.]['mean_ms'],1.)
  self.assertAlmostEqual(lookup['local_then_nearest_peer_2exchange_propagation',1.]['mean_ms'],.3)
  self.assertEqual(lookup['selected5G_path_switch_ack_propagation',2.]['median_ms'],7.)
  # Depth split: d1 3ms, d2 4ms, one sample each.
  self.assertEqual(lookup['selected5G_path_switch_ack_propagation_d1',1.]['median_ms'],3.)
  self.assertEqual(lookup['selected5G_path_switch_ack_propagation_d2',1.]['median_ms'],4.)
  self.assertEqual(lookup['selected5G_path_switch_ack_propagation_d2',1.]['samples'],1)
 def test_edge_control_placement(self):
  # AMF/SMF at serving IUPF: d1 is RAN-AMF only, 10km -> .1ms.
  self.assertAlmostEqual(edge_5g_path_switch_ack_propagation(self.row,.01),.1)
  # d2 adds SMF-target IUPF 50km and SMF-PSA 200km: 260km -> 2.6ms.
  self.assertAlmostEqual(edge_5g_path_switch_ack_propagation(dict(self.row,level=2,old_new_iupf_km=50),.01),2.6)
 def test_unsupported_depth_rejected(self):
  with self.assertRaises(ValueError):selected_5g_path_switch_ack_propagation(dict(self.row,level=3),.01)

if __name__=='__main__':unittest.main()
