# Open Analytics Control Tower (OACT)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18530096.svg)](https://doi.org/10.5281/zenodo.18530096)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

**Public-interest decision support for supply-chain disruption risk, built
entirely on open data.**

| | |
|---|---|
| **Live demo** | https://avtmbfenap.us-east-1.awsapprunner.com/ |
| **Project site** | https://resilient-supply-chain.github.io/open-supply-chain-control-tower/ |
| **Preprint** | [SSRN 6256558](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6256558) |
| **Archive** | [10.5281/zenodo.18530096](https://doi.org/10.5281/zenodo.18530096) |
| **Poster** | [UC Open 2026](docs/OACT_UCOpen_2026_Poster_v3.pdf) |

---

## The problem

Supply-chain disruption is no longer driven mainly by single, discrete events.
It is driven by **compound risk** — storm sequencing, antecedent soil
saturation, hydrologic stress and infrastructure fragility interacting over
days. A single atmospheric river rarely takes down a corridor; the third one in
two weeks, arriving on saturated ground, does.

Forecasting systems and consumer routing tools are not built for this. They
report closures after they happen, and they treat hazards independently.
Operators and public agencies therefore learn about a disruption when it is
already a disruption, which is far too late to reroute freight, pre-position
crews or protect cold-chain inventory.

The January 2023 California atmospheric-river cluster is the reference case:
compounding conditions across weeks drove cascading power and transport failure
that discrete-event monitoring did not anticipate.

## Why this matters at national scale

Supply-chain resilience is a stated U.S. national priority. The **Promoting
Resilient Supply Chains Act** ([S.257, 119th Congress](https://www.congress.gov/bill/119th-congress/senate-bill/257))
directs attention to early-warning capability and vulnerability mapping for
critical supply chains. **Executive Order 14017, *America's Supply Chains***,
sets the broader mandate to strengthen resilience across critical sectors.

The capability gap those instruments describe is concentrated in a specific
place. Large logistics firms build proprietary risk analytics in-house. Federal
agencies have their own modelling capacity. Between them sits what this project
calls the **"Missing Middle"** — mid-sized carriers, regional shippers, county
and municipal emergency planners, and rural utilities. They carry real exposure
and have no access to compound-risk analytics.

That gap is an information asymmetry, not a data availability problem. The
underlying signals are already public: NOAA storm events, USGS hydrology, ERA5
reanalysis, DOE outage records. What is missing is the work of turning them into
decisions that a non-specialist can act on and a public body can audit.

## What OACT contributes

**Open data end to end.** No proprietary feeds, no licensed datasets, no vendor
lock-in. Any agency or operator can run the full stack, inspect every input and
reproduce every score.

**Auditable by construction.** Each risk assessment carries an evidence bundle:
source provenance, timestamps, model versions and a decision ID. The risk
formulation follows the likelihood × consequence structure used in
[NIST SP 800-37](https://csrc.nist.gov/projects/risk-management), so outputs map
onto risk-management practice agencies already use rather than presenting an
opaque score.

**Decisions, not dashboards.** Model output is translated into operator-ready
Go / Monitor / No-Go states with a stated driver and recommended action, backed
by a five-step chain of evidence from detection through analysis to
recommendation.

**Local-first and governance-ready.** The stack is containerized and deployable
on an organization's own infrastructure, which matters for public bodies with
data-residency and auditability obligations.

## How it works

Risk is a likelihood × consequence formulation:

```
Risk = P̂(x) × I(x)
```

**P̂(x) — disruption likelihood.** Predicts the probability of a county-day
power outage from atmospheric-river intensity, precipitation, antecedent
precipitation indices, streamflow and gage-height percentiles, snow water
equivalent and wind extremes. Trained on 7,018 county-days with 36 features and
224 positive cases, using SMOTE for class imbalance.

**I(x) — conditional impact.** Given an outage occurred, predicts customers
affected. Log-transformed target with TimeSeriesSplit validation; XGBoost
(MAE 2,194, RMSLE 1.158) outperforms a Ridge baseline.

Their product gives the unconditional expected impact used to rank counties for
emergency response. Full methodology, feature list, per-model metrics and stated
limitations: [`Asset_Data_Team/README.md`](Asset_Data_Team/README.md).

## Current state

The reference implementation scores county-level power disruption risk in
California and replays the January 2023 atmospheric-river cluster end to end:
ingestion → scoring → explanation → UI. Both models are trained and evaluated,
and the dashboard is deployed and publicly reachable.

**Scope limits, stated plainly.** OACT is a research prototype, not production
software. Coverage is California, December 2022 – March 2023; the models are
trained on one state and one season, and generalization beyond that is untested.
The demo is a historical replay, not a live feed. The multi-agent component in
`apps/agent` is an unfinished prototype and is not part of the deployed demo.
There is no test suite.

Roadmap: corridor-specific route actions, expanded transportation overlays,
economic consequence modules, and broader multi-domain resilience workflows.

---

## Repository

```
apps/dashboard/     Web UI and API (TypeScript, Node 20) — the deployed demo
apps/agent/         Multi-agent chatbot prototype (Python) — in development
Asset_Data_Team/    Risk and conditional-impact models (notebooks, training data)
data/               Shared datasets: runtime input/output, plus raw/ source archives
docs/               Project site and architecture diagrams
infra/              AWS provisioning and deployment scripts
paper.md            Manuscript draft
```

**Running it locally, the API surface, deployment and repository conventions are
documented in [`MAINTAINERS.md`](MAINTAINERS.md).**

## Contributing

Issues and Discussions are open, and outside contributions are welcome. Bug
reports that include the failing route and the container logs are the most
useful. For questions about the research direction, contact the PI below.

## Citation

```bibtex
@software{oact,
  title  = {Open Analytics Control Tower (OACT): A Public-Interest
            Infrastructure Resilience System},
  author = {Sung, Yuan-Jiun and Hu, Yidan and He, Hao and Ma, Laisi and
            Sun, Yu and Jiang, Houyu and Jiang, Xiaochong and Zhang, Yu},
  year   = {2026},
  doi    = {10.5281/zenodo.18530096},
  url    = {https://github.com/Resilient-Supply-Chain/open-supply-chain-control-tower}
}
```

## Contributors

**Principal Investigator:** Yuan-Jiun (David) Sung

**Contributors:** Yidan (Lena) Hu, Hao He, Laisi (Maggie) Ma, Yu (Sebastian) Sun,
Houyu (Harry) Jiang, Xiaochong Jiang, Yu Zhang

Contact: yuanjius@alumni.cmu.edu

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
