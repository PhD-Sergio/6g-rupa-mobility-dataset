# 6G-RUPA vs 5G under mobility: reproducibility dataset

Companion dataset for the paper *"One User Plane to Rule Them All: From Handovers to a
Network of Networks"* (IEEE ICC 2027 submission). It extends the simulation study of
Giménez-Antón et al., "Beyond 5G Architectural Constraints: Designing Scalable-by-Design
User Planes for Mobile Networks via 6G-RUPA", IEEE Access, 2026 (data:
https://doi.org/10.34810/data3210), from static users to mobile users.

All results come from PLMN-GraphSim (https://github.com/Fundacio-i2CAT/PLMN-GraphSim),
a discrete-event simulator in Julia. No prototype or testbed measurements are included.

## Layout

```
sweep/     National mobility sweep (27 operator fields, 6 countries, 3 speed profiles),
           federation and non-terrestrial sweeps, and every input field they use.
           See sweep/README.md and sweep/PROVENANCE.md.
icc/       Additional runs for the ICC paper (September simulator, seeded):
           propagation round trips, per-UPF write load, anchor-count sweep,
           mixed-speed and hysteresis scenarios, scale convergence.
           See icc/README.md.
```

## Licenses

- Derived data (`sweep/results/`, `icc/runs/`, `icc/summaries/`): CC-BY-SA-4.0,
  inheriting OpenCelliD's share-alike terms.
- Inputs (`sweep/inputs/`): under their source licenses (OpenCelliD CC-BY-SA-4.0,
  FCC ASR public domain, ANFR Licence Ouverte 2.0, ISED Open Government Licence –
  Canada, national statistical-office terms). Per-file breakdown in
  `sweep/PROVENANCE.md`.
- Code (`icc/scripts/`, `icc/simulator/`): AGPL-3.0, the license of PLMN-GraphSim.
