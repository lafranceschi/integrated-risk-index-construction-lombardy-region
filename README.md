# integrated-risk-index-construction
Open-source Python scripts and GIS workflows for constructing an integrated municipal risk index to support local risk assessment and decision-making. The repository is part of the work entitled "A methodology for assemble municipal-scale integrated risk index to support civil protection planning: a case-study from Lombardy (N-Italy)" which is currently under submission.

## Municipal Risk Index – Computational Workflow

This repository contains the Python scripts used to construct a municipal-scale risk framework based on heterogeneous geospatial datasets. The workflow produces a set of intermediate outputs that progressively transform raw spatial information into standardized indicators and, ultimately, into a final municipal risk index.

Input datasets are not included due to licensing and size constraints. All data sources are publicly available through institutional geoportals. The repository is intended to ensure transparency, reproducibility, and methodological clarity of the computational workflow.

---

### Conceptual Overview

The framework is organized into three main processing streams:

- **Pre-existing risk indicators:** institutional risk scores directly standardized for comparability.
- **Hazard-based components:** indicators derived from spatial aggregation of physical susceptibility and exposure.
- **Damage-based components:** observed impacts attributed to municipal units through spatial association.

Each stream follows a dedicated processing pathway and contributes to the final integrated risk index.

---

### Repository Structure
## Repository Structure

scripts/

01_risk_data/
- a_risk_wildefire/
  - 1_risk_wildfire_normalisation.py

02_hazard_data/
- a_hazard_seismic/
  - 1_hazard_seismic_haz_calculation.py
  - 2_hazard_seismic_damage_score_adding.py
- b_hazard_hydraulic/
  - 1_hazard_hydraulic_overlap_removing.py
  - 2_hazard_hydraulic_haz_calculation.py
  - 3_hazard_hydraulic_sens_an
  - 4_hazard_hydraulic_damage_score_adding.py
- c_hazard_hydrogeological/
  - 1_hazard_hydrogeological_haz_calculation.py
  - 2_hazard_hydrogeological_sens_an.py
  - 3_hazard_hydrogeological_damage_score_adding.py
- d_hazard_avalanche/
  - 1_hazard_avalanche_haz_calculation.py
  - 2_hazard_avalanche_sens_an.py
  - 3_hazard_avalanche_damage_score_adding.py

03_damage_data/
- a_adv_w_fen/
  - 1_damage_adw_w_fen_damage_score_adding.py
  
04_integrated_risk_index/
- a_int_risk_index
  - 1_int_risk_index_spatial_analysis


Each folder contains:
- Python scripts for spatial processing and indicator construction
- Intermediate outputs used in subsequent processing stages

---

#### Workflow Summary

The computational workflow follows a sequential pipeline:

1. Spatial processing and municipal aggregation of input datasets  
2. Transformation of qualitative or raw variables into quantitative scores  
3. Normalization of indicators onto a common scale for comparability  
4. Integration of all components into a unified municipal risk index  

---

#### Intermediate Outputs

The workflow generates intermediate products at each stage, including:
- municipal-level hazard layers  
- damage attribution datasets  
- standardized risk indicators  
- intermediate scoring tables  

These outputs ensure full traceability and allow verification of each processing step.

---

#### Reproducibility

All scripts are developed in Python within a GIS environment. The workflow is fully modular and allows independent execution of each component of the analysis.

---

#### Notes

- The repository does not include raw datasets.
- All data sources are publicly accessible via institutional repositories.
- The structure is designed to ensure consistency across heterogeneous datasets while preserving their original semantic meaning.
