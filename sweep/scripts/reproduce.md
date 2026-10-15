# Reproducing the dataset

Every shipped result comes from the simulator **PLMN-GraphSim** (Julia), commit
`656b82d73b9f4c1545f7fc048253965ed14d7bc6` on branch `chore/multi-country-pipeline`,
run on an 80-core, 250 GB server under **Julia 1.11.9** on
2026-07-30. That stamp is also recorded in `results/sweep-provenance.txt`.

Every run is dispatched through the single entry point `main.jl <run> [args...]`;
`main.jl list` enumerates the available runs and their arguments.

## What "reproduce" means here

**Read this before comparing your output to the shipped CSVs.** Only one of the runs is
bit-reproducible. The others are statistically reproducible, and one derived column is
not reproducible at all.

`national_sweep`, `anchor_sweep`, `federation_continental` and `churn_data_usa`
(k-means UPF/anchor placement, population-weighted agent placement, mobility) draw from
Julia's global RNG, which is seeded from system entropy per process. **No seed is set.**
Rerunning the same command gives a different topology and a different agent population,
so your numbers will differ from the shipped ones. `ntn_sweep` is the exception: it calls
`Random.seed!` before building each target and derives a deterministic per-case seed, so
it reproduces bit-exactly (verified).

### Measured replication tolerance

The shipped data contains ten natural replicate pairs: five (country, operator) targets
appear at the same anchor count, agent count and duration in both `national-sweep.csv`
and `anchor-sweep.csv`, produced by independent processes. Comparing them measures the
run-to-run spread directly, at full production scale:

| Quantity | Max deviation | Mean deviation | Replicates? |
|---|---|---|---|
| `sigma_advantage_pct` | 0.16% relative (≤0.11 pp absolute) | 0.07% | Yes |
| `handovers` | 0.95% | 0.50% | Yes |
| `core_writes_5g` | 1.07% | 0.54% | Yes |
| `core_writes_6grupa` | exactly 0 in every row | — | Structural, not statistical |
| `stretch_excess_km` (ρ) | **236%** | **70%** | **No** |

So: **treat the headline σ and churn results as reproducible to roughly one percent, and
the per-row ρ values as not reproducible.**

> **Why ρ does not replicate.** ρ is a **rare-event mean averaged over a bulk
> denominator**, and that is the whole story.
>
> On every handover the simulator samples `d_pinned − d_nearest`: the distance from the
> new serving edge UPF to the pinned session anchor, minus the distance to the nearest
> anchor. While the user is still inside their own anchor region those two are the same
> anchor, so the sample contributes exactly 0 — but it still counts in the denominator.
> Only handovers made while the user is *displaced* into another anchor region contribute
> anything. Anchor-region crossings are 0.03–0.17% of all handovers, so ρ is roughly one
> sample in a thousand carrying a value of tens to hundreds of kilometres, divided by all
> the rest.
>
> That makes ρ doubly unstable. The number of crossings is a small count with
> Poisson-like scatter (9 vs 11, 65 vs 43, 80 vs 97 across replicate pairs). And the mass
> per crossing depends on *how deep* the user wandered and *how many handovers they made
> before returning* — a heavy-tailed quantity that a handful of users can dominate. The
> two compound: within-country correlation between ρ and the crossing rate is only
> 0.27–0.91, so the crossing count does not even explain all of the movement.
>
> **Longer runs do not fix ρ.** Measured over 24 independent runs at each of two scales
> (Portugal, 300 agents/120 s and 1500 agents/300 s, a 12.5× work increase): σ advantage,
> handovers and core writes shrink by 0.38/0.38/0.46 against the 0.283 expected from
> 1/√N — textbook sampling noise. But the underlying anchor distances shrink only from
> 13.85% to 10.21% CV, a ratio of 0.74. That residual is the unseeded k-means topology
> draw, not the sample, and it does not shrink with more agents or more simulated time.
> ρ is a sub-percent residual of those distances and inherits the floor amplified.
>
> The bulk metrics have the opposite structure and that is why they are stable. σ
> advantage is a ratio over the *same* event stream, so the event count cancels entirely
> and only the depth mix survives — and the mix is a bulk property (L1 share replicates to
> within 0.3 pp). Handovers and core writes are sums over every event, so ordinary
> averaging applies.
>
> What survives for ρ is the **order of magnitude and the direction**, not the value:
> kilometres against hundreds of kilometres of absolute anchor distance, which is the
> claim the paper makes of it (intra-PLMN pinning is cheap; the roaming boundary is where
> it costs). The rise of ρ with anchor density in `anchor-sweep.csv` also survives,
> because it is a 16–132× effect that holds in all 12 country/profile cases, far above the
> noise floor.

### To get bit-reproducible output

Set a seed before the run. Neither the shipped data nor the commands below do this, so
adding one will reproduce *a* valid dataset, not *this* dataset:

```bash
julia --project -e 'using Random; Random.seed!(20260730); include("main.jl")' national_sweep
```

### Verifying a rerun against the shipped data

Compare aggregates, not rows: check that `sigma_advantage_pct` lands within ±0.2 pp of
the shipped value for the same target and profile, that `core_writes_6grupa` is 0
everywhere, and that the reported ranges (66.9–71.5% national, 86.15%/65.39% federation)
are recovered. Do not diff ρ.

The shipped aggregates are exact concatenations of the per-shard CSVs in `results/raw/`
— verified, 81/81 and 216/216 rows — so the aggregation step itself can be re-derived
without rerunning anything.

## 0. Environment

```bash
cd PLMN-GraphSim
julia --project -e 'using Pkg; Pkg.instantiate()'
julia --project -e 'using DesJulia6gRupa'   # warm the precompile cache once,
                                            # before launching parallel shards
```

Julia 1.11+. Key packages: ConcurrentSim (discrete-event core), Clustering (k-means
UPF/PSA placement), SGP4 (orbital propagation for the NTN runs); the rest come from
the repo's `Project.toml`.

## 1. Inputs

Place the shipped inputs under the simulator's data tree:

```
PLMN-GraphSim/data/spain/opencellid/214.csv       <- inputs/gnb/spain-opencellid-214.csv
PLMN-GraphSim/data/portugal/opencellid/268.csv    <- inputs/gnb/portugal-opencellid-268.csv
PLMN-GraphSim/data/usa/opencellid/310.csv         <- inputs/gnb/usa-opencellid-310.csv
PLMN-GraphSim/data/usa/opencellid/311.csv         <- inputs/gnb/usa-opencellid-311.csv
PLMN-GraphSim/data/usa/asr/310.csv                <- inputs/gnb/usa-fcc-asr-310.csv
PLMN-GraphSim/data/france/opencellid/208.csv      <- inputs/gnb/france-opencellid-208.csv
PLMN-GraphSim/data/france/anfr/208.csv            <- inputs/gnb/france-anfr-208.csv
PLMN-GraphSim/data/canada/opencellid/302.csv      <- inputs/gnb/canada-opencellid-302.csv
PLMN-GraphSim/data/canada/ised/302.csv            <- inputs/gnb/canada-ised-302.csv
PLMN-GraphSim/data/mexico/opencellid/334.csv      <- inputs/gnb/mexico-opencellid-334.csv

PLMN-GraphSim/data/<country>/municipalities.csv   <- inputs/population/<country>-municipalities.csv
PLMN-GraphSim/data/<country>/regions.geojson      <- gunzip inputs/population/<country>-regions.geojson.gz
```

```bash
for f in inputs/population/*-regions.geojson.gz; do
  c=$(basename "$f" -regions.geojson.gz)
  gunzip -c "$f" > "PLMN-GraphSim/data/$c/regions.geojson"
done
```

The UPF/PSA topology is *not* shipped and does not need to be: `load_and_deploy_network`
rebuilds it from the gNB field and the requested counts on every run
(k-means over gNBs for edge UPFs, hierarchical k-means over those for PSAs).

## 2. National sweep → `results/national-sweep.csv` (81 rows)

```bash
julia --project main.jl national_sweep                     # all 27 targets x 3 profiles
julia --project main.jl national_sweep france,canada       # country subset
julia --project main.jl national_sweep all 2000 300        # smoke: 2000 agents, 300 s
```

Args: `<targets> <agent override; 0 = population-derived> <duration_s> <output> <mobility filter>`.

Targets are (country, source, operator) triples; `field` selects the crowdsourced
OpenCellID set or the official registry where one exists. Defaults: 1200 s, agents =
population × 0.82 adoption / 1000 scale, edge UPFs and PSAs per country as fixed in the
run script's `TARGETS` table.

**Sharding.** The published run split the 27 × 3 matrix into 81 independent processes so
wall time tracks the longest single job rather than the sum, using the target-index and
mobility-filter arguments:

```bash
julia --project main.jl national_sweep idx:$T 0 1200 results/raw/national-shards/t${T}_${M}.csv $M
```

for `T` in 1..27 and `M` in {pedestrian, urban, highway}, 40 concurrent. Concatenating
the 81 shard CSVs under one header reproduces `national-sweep.csv`; the shards and their
per-shard logs ship in `results/raw/`.

## 3. Population scaling → `results/churn-data-*.csv`

```bash
julia --project=. runs/churn_data_usa.jl results/churn-data-verizon-1200.csv 1200 verizon-opencellid
```

Holds the deployment fixed (Verizon US, 817 edge UPFs, 5 anchors, highway Gauss–Markov)
and sweeps represented population 1 M → 274.7 M. `churn-data-usa.csv` is the earlier
300 s paired OpenCellID/FCC ASR variant of the same run.

## 4. Anchor sensitivity → `results/anchor-sweep.csv` (60 rows)

```bash
julia --project main.jl anchor_sweep                       # 6 countries, anchors 2..40
julia --project main.jl anchor_sweep spain 2,5,10,20       # one country, chosen counts
julia --project main.jl anchor_sweep all 2,5 3000 300      # smoke
```

Args: `<countries> <anchor counts CSV> <agent override> <duration_s> <output>`. Defaults
`2,5,10,20,40`, 1200 s, {pedestrian, highway}. The anchor set is re-clustered for each
count, so each row is a genuine redeployment rather than a relabelling.

> **Reproduction caveat.** Anchor placement clamps to `k = min(requested, #edge UPFs)`.
> Portugal has 18 edge UPFs, so `psa=20` and `psa=40` both actually run at 18 and the
> `psa` column records the request, not the deployment. See the README for what that
> does to ρ in those four rows.

## 5. Continental federations → `results/federation-continental.csv` (60 rows)

Four runs, each writing its own 15-row file; concatenate under one header.

```bash
julia --project main.jl federation_continental europe        reestablish 0 1200 all
julia --project main.jl federation_continental europe        ideal_ho    0 1200 all
julia --project main.jl federation_continental north_america reestablish 0 1200 all
julia --project main.jl federation_continental north_america ideal_ho    0 1200 all
```

Args: `<federation> <5G semantics> <agents; 0 = population-derived> <duration_s>
<mobility: pedestrian|urban|highway|all> <output>`.

Each federation grows K = 2..6 by adding a *country* before adding a second operator
within one, so K widens the geography rather than the operator list:

- `europe`: Movistar ES → MEO PT → Orange FR → Vodafone ES → NOS PT → SFR FR
- `north_america`: Verizon US → Telus CA → Telcel MX → AT&T US → Rogers CA → Movistar MX

Members keep their national edge/PSA partition when they join, and member fields are
built once and reused across K.

## 6. Terrestrial–NTN → `results/ntn-sweep.csv` (216 rows)

```bash
julia --project main.jl ntn_sweep                          # all 9 country/source targets
julia --project main.jl ntn_sweep canada-ised              # one target
julia --project main.jl ntn_sweep idx:3 20000 600          # smoke
```

Args: `<targets> <agent cap> <duration_s> <output> <mobility filter> <r_terr CSV>
<satellite-HO semantics CSV> <constellation>`. Defaults: 50 000-agent cap (so every
country costs the same and satellite-served share stays a per-agent statistic), 1200 s,
`5,10,20,30` km, `xn,n2`, Starlink. Fixed seed 20260728; SGP4 propagation from
`tles_starlink_550_sgp.txt` (550 km shell) with one-second shared snapshots and a 25°
minimum elevation.

**Sharding.** The published run split by (target, r_terr) into 36 processes, 20
concurrent, each emitting 6 rows (3 mobility profiles × 2 satellite-HO semantics):

```bash
julia --project main.jl ntn_sweep idx:$N 50000 1200 results/raw/ntn-shards/n${N}_r${R}.csv all $R
```

for `N` in 1..9 and `R` in {5, 10, 20, 30}. Shards and logs ship in `results/raw/`.

> **The sharded form is the only one that reproduces the shipped CSV.** `ntn_sweep`
> derives its per-case seed as `SEED + 100·ri + mi`, where `ri` is the *index of the range
> within the `R_SWEEP` list*, not the range value. A shard passes a single range, so
> `ri = 1` always; the unsharded default passes `5,10,20,30`, so the same physical
> configuration gets a different seed and different numbers. Measured on Portugal at
> r_terr = 10 km, 400 agents, 120 s: satellite-served share is 11.28% when 10 is the only
> range and 9.33% when it is the second of four — same configuration, seeds apart.
>
> Running `julia --project main.jl ntn_sweep` with its documented defaults will therefore
> *not* reproduce `ntn-sweep.csv`. Use the sharded loop above. This is a latent bug in the
> seed derivation (it should key off the range value, not its list position); it is
> recorded rather than fixed, because changing it would invalidate the shipped data.

## 7. Trajectories (not shipped)

```bash
julia --project main.jl trajectories
```

Emits `viz/data/{trajectories,gnbs,meta}-<country>.json` for the deck.gl demo. Each
`trajectories-*.json` is an array of
`{path:[[lon,lat]...], ts:[...], ho:[[lon,lat,t,level]...]}` per agent, where `level` ∈
{1 = L1 Xn (same edge UPF), 2 = L2 N2 (edge change, PSA pinned)}. Hundreds of MB at full
national agent count, and not an input to any reported number, so it is excluded from
this dataset.
