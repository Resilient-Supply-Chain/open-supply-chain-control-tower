---
title: 'Open Analytics Control Tower (OACT): A Public-Interest Infrastructure Resilience System'
tags:
  - python
  - resilience
  - infrastructure
  - supply chain
  - public policy
  - compound risk
  - risk modeling
authors:
  - name: Yuan-Jiun (David) Sung
    affiliation: 1
  - name: Yidan (Lena) Hu
    affiliation: 2
  - name: Celia Wen
    affiliation: 2
  - name: Houyu (Harry) Jiang
    affiliation: 2
  - name: Yu (Sebastian) Sun
    affiliation: 2
  - name: Xiaochong Jiang
    affiliation: 2
  - name: Laisi (Maggie) Ma
    affiliation: 2
  - name: Hao He
    affiliation: 2
  - name: Yue (Phoebe) Han
    affiliation: 2
  - name: Yu Zhang
    affiliation: 2
affiliations:
 - name: Principal Investigator, OACT Project (Independent Research Prototype)
   index: 1
 - name: OACT Volunteer Research Team
   index: 2
date: 30 January 2026
bibliography: paper.bib
---

# Summary

The Open Analytics Control Tower (OACT) is an open-source, reproducible decision-support system designed to operationalize supply chain resilience using strictly public data [@oact]. Unlike consumer routing tools that primarily display discrete closures, OACT models *compound risk*—such as storm sequencing and antecedent soil saturation—to anticipate infrastructure disruption (e.g., washouts, power outages) and translate model outputs into operator-ready “Go / Monitor / No-Go” decision support [@zscheischler2018]. OACT is built to be local-first and auditable: each output is intended to be traceable to an evidence bundle containing source provenance, timestamps, and model versions.

# Statement of Need

Supply chain resilience is a national priority reflected in legislation such as the *Promoting Resilient Supply Chains Act of 2025* (S.257) [@s257]. However, many mid-sized operators and regional agencies (the “Missing Middle”) lack accessible analytics to preemptively manage climate-driven disruption risk. OACT addresses this gap by providing a “map / monitor / model” reference architecture using only open datasets and a containerized workflow that can be deployed locally for auditability and governance readiness [@odi]. The project also emphasizes clean-room and IP-safe development practices suitable for public-interest prototypes [@calabor].

# Mathematics and Modeling

OACT follows a standard likelihood–consequence formulation aligned with widely used risk-management approaches [@nist]:

$$Risk = \hat{P}(x) \times I(x)$$

where $\hat{P}(x)$ is the predicted probability of a disruption event (e.g., county-level power outage) and $I(x)$ is the conditional impact estimate (e.g., customers affected) using event-correlated outage labels and publicly released outage datasets [@pnnl]. The v0.1 reference implementation focuses on **county-level power disruption risk** using supervised learning on a county-by-day panel (“Dataset X”) derived from public environmental signals and infrastructure context (e.g., NOAA storm events, USGS hydrology, ERA5 reanalysis variables) [@noaa; @usgs; @era5]. To mitigate class imbalance in rare disruption events, the pipeline may apply Synthetic Minority Over-sampling Technique (SMOTE) [@smote].

# Implementation & Architecture

OACT is implemented as a modular stack designed for reproducibility and operational clarity:

* **Data ingestion & normalization:** containerized ETL pipelines convert multi-source public signals into county-day feature panels suitable for historical replay and training [@noaa; @usgs; @era5].
* **Risk modeling:** a two-stage modeling approach estimates disruption likelihood and conditional severity, enabling both thresholded states (Go / Monitor / No-Go) and continuous expected-risk scoring [@nist].
* **Agentic layer (optional component):** an orchestration layer can generate an “evidence-bundled” explanation for why risk is elevated, tethering each claim to verifiable sources and timestamps.
* **Visualization:** a web UI renders risk heatmaps and decision panels for replay scenarios and stakeholder review.

# Use Case

The current release supports a **historical replay** of the January 2023 California atmospheric-river event cluster, illustrating how compounding conditions can elevate disruption risk for logistics corridors (e.g., Monterey County / Salinas River–Hwy 68) [@caltrans; @nasa]. This replay-based approach enables end-to-end validation (ingestion → scoring → explanation → UI) without requiring real-time production integrations.

# Acknowledgements

OACT is a multi-contributor volunteer effort. Some workstreams (e.g., economic impact estimation) may be developed as follow-on modules and integrated in later releases; the v0.1 JOSS submission should reflect the code and artifacts included in the public repository at submission time.

# References
