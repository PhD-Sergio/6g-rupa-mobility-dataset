# Provenance & Licensing

Every file shipped here is either a standardized copy of a public source, or a
derivation from one. This document records, per file, where it came
from, what was done to it, and under what terms it may be redistributed.

All gNB files are written in the same 14-column OpenCellID layout
(`radio,mcc,net,area,cell,unit,lon,lat,range,samples,changeable,created,updated,averageSignal`)
so the loader can read a crowdsourced field and an official registry through one code
path. For registry-derived files the OpenCellID-specific columns are filled with
placeholders; only `radio,mcc,net,lon,lat` carry meaning.

The standardization scripts referenced below live in
`PLMN-GraphSim/data/processing_scripts/` and are the authoritative record of the
raw → standardized transformation.

## inputs/gnb/ — crowdsourced fields (OpenCellID)

| File | Rows | Selection | Retrieved |
|---|---|---|---|
| `spain-opencellid-214.csv` | 102 360 | MCC 214 | December 2025 |
| `usa-opencellid-310.csv` | 438 525 | MCC 310 | December 2025 |
| `usa-opencellid-311.csv` | 116 825 | MCC 311 | December 2025 |
| `portugal-opencellid-268.csv` | 22 627 | MCC 268 | July 2026 |
| `france-opencellid-208.csv` | 390 737 | MCC 208 | July 2026 |
| `canada-opencellid-302.csv` | 58 979 | MCC 302 | July 2026 |
| `mexico-opencellid-334.csv` | 200 641 | MCC 334 | July 2026 |

- **Source:** OpenCellID (https://opencellid.org), community-collected cell database.
- **Selection:** whole-MCC export, no filtering. Operator selection happens at load
  time via the `net` (MNC) column, so one file serves every operator in that country.
- **Note:** OpenCellID rows are *cells*, not sites — a three-sector site appears as
  roughly three rows. This is why the crowdsourced counts run 2–3× above the official
  registries for the same country and operator, and why coverage-hole measurements
  from these fields must be read beside a registry row (see README, NTN section).
- **License:** CC-BY-SA-4.0. Attribution: "© OpenCellID contributors". Share-alike
  propagates, so every derived product in this dataset is also CC-BY-SA-4.0.

## inputs/gnb/ — official registries

### usa-fcc-asr-310.csv (192 816 rows)
- **Source:** US FCC Antenna Structure Registration, https://www.fcc.gov/uls
  (bulk file `r_tower.zip` from `data.fcc.gov/download/pub/uls/complete/`).
- **Retrieved:** June 2025.
- **Processing** (`standardize_usa.py`): parsed `CO.dat` coordinate records, converted
  DMS → decimal degrees, filtered to the CONUS bounding box (lat 24–50, lon −125 to
  −66), de-duplicated by registration number, emitted with a synthetic `net=999` tag.
- **Caveat:** ASR records the *structure owner*, not the serving operator, so per-site
  operator attribution is impossible. It is modelled as an operator-agnostic
  all-macro-site field and used only as a density upper bound.
- **License:** US Government work, public domain (17 U.S.C. §105). No restriction.

### france-anfr-208.csv (135 092 rows)
- **Source:** ANFR, Base Nationale des Installations Radioélectriques (BNIR) monthly
  export — every radio installation above 5 W must be declared by law.
  https://www.data.gouv.fr/datasets/donnees-sur-les-installations-radioelectriques-de-plus-de-5-watts-1/
- **Retrieved:** July 2026.
- **Processing** (`standardize_france_anfr.py`): joined `SUP_SUPPORT.txt` (support
  geometry, DMS coordinates) → `SUP_STATION.txt` (station → ADM_ID) →
  `SUP_EXPLOITANT.txt` (ADM_ID → operator), mapped ANFR operator ids to the real MNCs
  used by OpenCellID (Orange 1, SFR 10, Free 15, Bouygues 20) so the two French fields
  compare operator by operator.
- **Unit difference:** ANFR rows are *sites* (one station per operator per support) and
  positions are operator-declared, not crowd-estimated.
- **License:** Licence Ouverte / Open Licence 2.0 (Etalab). Attribution to ANFR
  required; redistribution and derivation permitted.

### canada-ised-302.csv (43 201 rows)
- **Source:** ISED Terrestrial Spectrum Licence Site Data Extract
  (`Site_Data_Extract_FX.zip`),
  https://ised-isde.canada.ca/site/spectrum-management-system/en/download-sms-data
- **Retrieved:** July 2026.
- **Processing** (`standardize_canada_ised.py`): one raw row is a (licence, frequency,
  site) combination, so sites repeat; de-duplicated on rounded coordinates per
  operator. Licensee-name fragments mapped to MNCs (Telus 220 — filed under two account
  names, Rogers 720 — including the Fido brand which shares its network, Bell 610).
- **Caveat:** this is *not* the Technical and Administrative Frequency List
  (`TAFL_LandMobile`), which covers private land mobile radio and contains almost no
  carrier cell sites.
- **License:** Open Government Licence – Canada 2.0. Attribution to ISED required.

## inputs/population/

Per country: `<country>-municipalities.csv` (`id,name,population,lat,lon`) and
`<country>-regions.geojson.gz` (FeatureCollection, `properties.id` joins the CSV `id`).
Municipality centroids and populations weight agent placement; the polygons are used
for rejection sampling so agents land inside real inhabited area rather than on a
bounding box. Boundaries are gzipped because the uncompressed set is 262 MB.

| Country | Units | Level | Population source | Boundary source | Script |
|---|---|---|---|---|---|
| Spain | 8 044 | Municipios | INE, via CNIG nomenclator (COD_INE) | CNIG / ESRI municipios | `standardize_spain.py` |
| Portugal | 278 | Concelhos | INE Portugal, Censos 2021 definitive (indicator 0011609) | DGT CAOP 2025, mainland | `standardize_portugal.py` |
| France | 34 746 | Communes | INSEE legal population via geo.api.gouv.fr | IGN ADMIN-EXPRESS contours via geo.api.gouv.fr | `standardize_france.py` |
| USA | 3 109 | Counties | US Census Bureau estimates | US Census county boundaries | `standardize_usa.py` |
| Canada | 4 830 | Census subdivisions | Statistics Canada 2021 Census (table 98100002) | StatCan `lcsd000b21a_e`, EPSG:3347 → WGS84 | `standardize_canada.py` |
| Mexico | 2 463 | Municipios | INEGI Censo 2020 ITER (`LOC == 0000` rows) | CONABIO republication of INEGI Marco Geoestadístico (`muni_2018gw`) | `standardize_mexico.py` |

**Territorial cuts.** Each country is reduced to one contiguous landmass so mobility
models do not teleport agents across ocean: metropolitan France only (departments
01–95 plus Corsica 2A/2B, overseas departments excluded), mainland Portugal only
(CAOP Continente, 278 concelhos — Madeira and the Azores fall out of the join),
mainland Spain (Canary filter), CONUS only for the USA.

**Geometry simplification.** Canadian and Mexican polygons are simplified at a ~200 m
tolerance (`SIMPLIFY_TOLERANCE_DEG = 0.002`); the simulator only needs them for
rejection sampling, not for cartography.

**Licenses.** INE (ES) and INE Portugal: free reuse with attribution. DGT CAOP: open
data, attribution required. INSEE/IGN via Etalab: Licence Ouverte 2.0. US Census:
public domain. Statistics Canada: Statistics Canada Open Licence, attribution
required. INEGI / CONABIO: INEGI terms of free use, attribution required.

## results/

Aggregated sweeps. Provenance for all four is stamped in
`results/sweep-provenance.txt`: generated 2026-07-30T10:24:17Z on server
an 80-core server, Julia 1.11.9, PLMN-GraphSim commit
`656b82d73b9f4c1545f7fc048253965ed14d7bc6` (branch `chore/multi-country-pipeline`).

- `national-sweep.csv` — 81 rows, 27 (country, source, operator) targets × 3 mobility
  profiles. `main.jl national_sweep`. 1200 s, agents = population × 0.82 / 1000.
- `anchor-sweep.csv` — 60 rows, 6 countries × anchor counts {2,5,10,20,40} ×
  {pedestrian, highway}. `main.jl anchor_sweep`. See the README for the Portugal
  clamp artifact at 20 and 40 anchors.
- `federation-continental.csv` — 60 rows, 2 continental federations × K=2..6 × both 5G
  semantics × 3 mobility profiles. `main.jl federation_continental <federation>
  <semantics> 0 1200 all`.
- `ntn-sweep.csv` — 216 rows, 9 (country, source) targets × r_terr {5,10,20,30} km × 3
  mobility profiles × {Xn, N2} satellite handover semantics. `main.jl ntn_sweep`.
  Starlink 550 km shell, `tles_starlink_550_sgp.txt`, SGP4 propagation with
  one-second shared snapshots, 25° minimum elevation, 50 000-agent cap, seed 20260728.
- `churn-data-verizon-1200.csv` — full-duration (1200 s) Verizon population sweep used
  by the headline churn figure. `runs/churn_data_usa.jl`.
- `churn-data-usa.csv` — earlier paired 300 s Verizon OpenCellID / FCC ASR population
  sweep, retained as a source check. `runs/churn_data_usa.jl`.

`sweep-provenance.txt` reports row counts for the national and NTN sweeps only; the
anchor and federation sweeps were produced in the same session on the same commit and
their row counts are stated above.

### results/raw/
Primary evidence behind the aggregates, kept so the concatenation can be audited:

- `national-shards/` — one CSV per (target, mobility profile). The 27 × 3 matrix is
  sharded into 81 independent jobs so wall time tracks the longest single job rather
  than the sum.
- `ntn-shards/` — one CSV per (agent count, r_terr) partition, named `n<i>_r<r>.csv`.
- `logs/` — raw stdout per shard.

License for everything under `results/`: CC-BY-SA-4.0, inherited from OpenCellID.

## Not shipped

- **`topology/`** — the two-tier UPF/PSA deployment (edge UL-CL UPFs by k-means over
  the gNB field, PSAs by hierarchical k-means over the edge UPFs, edge→PSA map from
  the same clustering) is rebuilt at load time by
  `DataLoading/Loader.jl` from `inputs/gnb/` plus the anchor count. Shipping it would
  duplicate state that can silently drift from the inputs.
- **`trajectories/`** — per-agent mobility traces for the deck.gl demo, regenerable via
  `main.jl trajectories`. Hundreds of MB, and not an input to any reported number.
- **Raw pre-standardization source bundles** — the ANFR monthly export, ISED
  `Site_Data_Extract_FX.zip`, INEGI/CONABIO shapefiles, StatCan boundary files and
  Census tables are all downloadable from the URLs above. The
  `PLMN-GraphSim/data/processing_scripts/standardize_*.py` scripts reproduce the
  shipped standardized files from them.
