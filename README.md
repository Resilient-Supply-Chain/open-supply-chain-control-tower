# Open Analytics Control Tower (OACT)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18530096.svg)](https://doi.org/10.5281/zenodo.18530096)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Node 20](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org/)

**Open-data decision support for supply-chain disruption risk.**

OACT turns public extreme-weather and infrastructure signals into explainable,
county-level disruption-risk assessments for logistics operators and government
emergency planners. Unlike routing tools that display closures after they
happen, OACT models *compound* risk — storm sequencing, antecedent soil
saturation, hydrologic stress — to anticipate disruption before it occurs.

Every output is designed to be auditable: each risk score carries an evidence
bundle with source provenance, timestamps and model versions.

| | |
|---|---|
| **Live demo** | https://avtmbfenap.us-east-1.awsapprunner.com/ |
| **Project site** | https://resilient-supply-chain.github.io/open-supply-chain-control-tower/ |
| **Preprint** | [SSRN 6256558](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6256558) |
| **Archive** | [10.5281/zenodo.18530096](https://doi.org/10.5281/zenodo.18530096) |
| **Poster** | [UC Open 2026](docs/OACT_UCOpen_2026_Poster_v3.pdf) |

---

## Quick start

The dashboard runs from a clean checkout in two commands. **The build context is
the repository root** — the image needs both the app and the `data/` files the
server reads.

```bash
docker build -f apps/dashboard/Dockerfile -t osct-web .
docker run --rm -p 3000:3000 osct-web
```

Open http://localhost:3000.

Without Docker (Node 20):

```bash
cd apps/dashboard && npm ci && npm run build && npm start
```

> The map renders with "development purposes only" watermarks unless you supply
> your own billing-enabled Google Maps key in `apps/dashboard/public/index.html`.
> Everything else — risk scoring, the evidence chain, the API — works regardless.

---

## What it does

The reference implementation scores **county-level power disruption risk in
California** and replays the **January 2023 atmospheric-river event cluster**
end to end: ingestion → scoring → explanation → UI.

The dashboard shows a county risk choropleth, highway corridor overlays, a
Go / Monitor / No-Go decision panel, a five-step chain of evidence
(detect → analyze → recommend), and an audit-trail evidence bundle, across
2022-11-30 to 2023-03-30.

### The model

Risk is a standard likelihood × consequence formulation:

```
Risk = P̂(x) × I(x)
```

**P̂(x) — disruption likelihood.** Predicts the probability of a county-day
power outage from atmospheric-river intensity, precipitation, antecedent
precipitation indices, streamflow and gage-height percentiles, snow water
equivalent and wind extremes. Trained on 7,018 county-days with 36 features and
224 positive cases, using SMOTE for class imbalance. Six classifiers were
compared, optimizing recall on the rare positive class.

**I(x) — conditional impact.** Given an outage occurred, predicts customers
affected. Log-transformed target with TimeSeriesSplit validation; XGBoost
(MAE 2,194, RMSLE 1.158) outperforms a Ridge baseline.

Multiplying the two gives the unconditional expected impact used to rank
counties for emergency response.

Full methodology, feature list, per-model metrics and stated limitations:
[`Asset_Data_Team/README.md`](Asset_Data_Team/README.md).

### API

| Route | Returns |
|---|---|
| `/api/dates` | Available replay dates |
| `/api/risks?date=` | Per-county risk records for that date |
| `/api/highways` | Highway corridor overlay |
| `/api/evidence` | Evidence-chain template |

---

## Repository layout

```
apps/dashboard/     Web UI and API (TypeScript, Node 20) — the deployed demo
apps/agent/         Multi-agent chatbot prototype (Python) — in development
Asset_Data_Team/    Risk and conditional-impact models (notebooks, training data)
data/               Shared datasets: runtime input/output, plus raw/ source archives
docs/               Project site and architecture diagrams
infra/              AWS provisioning and deployment scripts
paper.md            Manuscript draft
```

Maintainer notes — deployment, conventions and the open issue list — are in
[`MAINTAINERS.md`](MAINTAINERS.md).

---

## Scope and maturity

OACT is a **research prototype**, not production software. What that means
concretely:

- The **dashboard and both models work** and are what the preprint and poster
  describe. The demo is a historical replay, not a live feed.
- Coverage is **California, December 2022 – March 2023**. The models are trained
  on one state and one season; generalization beyond that is untested.
- The **agent in `apps/agent` is an unfinished prototype**. It is not part of the
  deployed demo and is not expected to run end to end yet.
- There is **no test suite** and no automated test CI.

Roadmap: corridor-specific route actions, expanded transportation overlays,
economic consequence modules, broader multi-domain resilience workflows.

---

## Contributing

Issues and Discussions are open, and outside contributions are welcome.
Bug reports that include the failing route and the container logs are the most
useful. For questions about the research direction, contact the PI below.

---

## Citation

If you use OACT, please cite the archived release:

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

---

## Contributors

**Principal Investigator:** Yuan-Jiun (David) Sung

**Contributors:** Yidan (Lena) Hu, Hao He, Laisi (Maggie) Ma, Yu (Sebastian) Sun,
Houyu (Harry) Jiang, Xiaochong Jiang, Yu Zhang

Contact: yuanjius@alumni.cmu.edu

---

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
