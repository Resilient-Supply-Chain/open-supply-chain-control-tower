# Open Analytics Control Tower (OACT)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18530096.svg)](https://doi.org/10.5281/zenodo.18530096)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Node 20](https://img.shields.io/badge/node-20-green.svg)](https://nodejs.org/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/)

OACT turns open extreme-weather and infrastructure signals into explainable,
county-level disruption-risk assessments for supply chains and government
emergency planners. It is a public-interest research prototype built entirely on
public data, and it models *compound* risk — storm sequencing, antecedent soil
saturation, hydrologic stress — rather than displaying discrete closures.

The reference implementation scores **county-level power disruption risk in
California** and replays the **January 2023 atmospheric-river event cluster**
end to end: ingestion → scoring → explanation → UI.

| | |
|---|---|
| Live demo | https://avtmbfenap.us-east-1.awsapprunner.com/ |
| Project site | https://resilient-supply-chain.github.io/open-supply-chain-control-tower/ |
| Preprint | [SSRN 6256558](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=6256558) |
| Archive | [Zenodo 10.5281/zenodo.18530096](https://doi.org/10.5281/zenodo.18530096) |
| Poster | [UC Open 2026](docs/OACT_UCOpen_2026_Poster_v3.pdf) |

---

## Status at a glance

| Component | State | Notes |
|---|---|---|
| Dashboard (`apps/dashboard`) | **Working** | Deployed and serving; builds and runs from a clean checkout |
| Risk + impact models (`Asset_Data_Team`) | **Working** | Trained, evaluated, predictions committed |
| Project site (`docs/`) | **Working** | Auto-publishes to GitHub Pages from `main` |
| JOSS paper (`paper.md`) | **Draft** | v0.1 draft, not yet submitted |
| Agent / chatbot (`apps/agent`) | **Unfinished** | Demo mode only; several paths are placeholders — see below |
| CI deployment | **Blocked** | Repository has no AWS secrets configured — see below |
| Map rendering | **Degraded** | Google Maps billing is not enabled — see below |

---

## Repository layout

```
apps/
  dashboard/            Live demo UI (TypeScript + Express, Node 20)
    public/             index.html, ca-counties.geojson
    src/                client.ts, server.ts
    tools/              signal generators (JS + Python)
    Dockerfile          builds from the REPOSITORY ROOT, not from here
  agent/                Unfinished multi-agent chatbot (Python)
    src/agents/         chatbot, refactor agent, data checker
    src/tools/          RAG, geo, SES mailer, PDF parsing, data bridge
    src/ui/app.py       Gradio UI
    src/workflow/       graph + router
    config/             settings.yaml, prompts.yaml
    main.py             entrypoint

Asset_Data_Team/        Risk model + conditional impact model (notebooks, data)

data/                   Shared by both apps — keep at the repository root
  input/signals/        58 per-county risk event JSONs (dashboard reads these)
  input/highways.json   Highway corridor overlay
  input/registered_provider/   Risk-model predictions consumed by the dashboard
  output/               Generated artifacts (data_series.json, alerts.json)
  raw/oe-417/           DOE OE-417 annual outage summaries, 2010-2023

docs/                   GitHub Pages site (source: main branch, /docs) + diagrams
infra/                  AWS setup and manual deployment scripts
assets/screenshots/     Screenshots used in documentation
paper.md, paper.bib     JOSS submission draft
```

**`data/` must stay at the repository root.** `apps/dashboard/src/server.ts`
resolves it as `../../../data/...` relative to `dist/server.js`, and the agent
resolves it from the repository root too.

`input/` and `output/` are what the applications read and write at runtime;
`raw/` holds source datasets that feed model training and analysis but that
nothing reads at runtime. Only `input/` and `output/` files are copied into the
dashboard image.

---

## The dashboard — `apps/dashboard`

The deployed demo: a California county choropleth of disruption risk, highway
corridor overlays, a Go / Monitor / No-Go decision panel, a five-step
chain-of-evidence panel (detect → analyze → recommend), an audit-trail evidence
bundle, and a date selector covering 2022-11-30 through 2023-03-30.

### Run it

Docker is the supported path. **The build context is the repository root** — the
image needs both `apps/dashboard/` and the `data/` files the server reads.

```bash
docker build -f apps/dashboard/Dockerfile -t osct-web .
docker run --rm -p 3000:3000 osct-web
```

Then open http://localhost:3000.

Without Docker:

```bash
cd apps/dashboard && npm ci && npm run build && npm start
```

### Endpoints

| Route | Serves | Reads |
|---|---|---|
| `/api/dates` | Available replay dates | `data/input/registered_provider/.../OSCCT_risk_predict_model.csv` |
| `/api/risks?date=` | Per-county risk records | `data/input/signals/*.json` |
| `/api/highways` | Corridor overlay | `data/input/highways.json` |
| `/api/evidence` | Evidence-chain template | `data/output/ui_output_template.json` |

### Regenerating signals

```bash
node apps/dashboard/tools/generate_signals.js
python apps/dashboard/tools/regenerate_signals.py
```

Both read `data/output/data_series.json` and write `data/input/signals/`.

---

## The models — `Asset_Data_Team`

Two models compose the risk formula `Risk = P̂(x) × I(x)`:

**Risk model** — predicts the probability of a county-day power outage from
atmospheric-river, precipitation, hydrologic and antecedent-condition features
(7,018 county-days, 36 features, 224 positives). SMOTE for class imbalance; six
classifiers compared, optimizing Class-1 recall. Logistic regression reaches the
highest recall (0.733) at a high false-positive cost; gradient boosting gives the
best precision (0.474).

**Conditional impact model** — given an outage occurred, predicts customers
affected. Log-transformed target, TimeSeriesSplit validation. XGBoost
(MAE 2,194, RMSLE 1.158) beats a Ridge baseline (2,918 / 1.336).

Multiplying the two gives the unconditional expected impact used to rank
counties for emergency response.

Full methodology, feature list, per-model metrics and stated limitations:
[`Asset_Data_Team/README.md`](Asset_Data_Team/README.md).

---

## The agent — `apps/agent` (unfinished)

A multi-agent chatbot intended to generate evidence-bundled explanations and
broadcast resilience alerts. **It is a work in progress and is not part of the
deployed demo.** It is kept here because the RAG, geo and SES scaffolding is
worth resuming from, not because it currently works end to end.

What exists: a controller chatbot with demo-mode routing, a TF-IDF RAG engine
over legislative text, geodesic SME-radius filtering, an AWS SES alert mailer, a
Gradio UI, and a CSV→JSON data bridge.

What does not work yet:

- `src/tools/data_bridge.py` ships placeholder paths — `DEFAULT_CSV_SOURCE` is
  the literal string `"file_path/..."` and `DEFAULT_JSON_OUTPUT` points outside
  the repository. Only the `run_demo_conversion()` call path supplies real paths.
- Live model inference is not wired up; the chatbot runs deterministic demo
  responses.
- Real functionality needs API keys (see `apps/agent/.env.example`) that no
  contributor currently has provisioned in a shared place.
- Two branches carry unmerged work on this code and have been untouched since
  2026-01-28: `v2.4.0/react_mode` and `v2.4.1/model_explanation`.

### Run it

```bash
pip install -r apps/agent/requirements.txt
cp apps/agent/.env.example apps/agent/.env    # then fill in keys
python apps/agent/main.py                      # run from the repository root
```

Run it **from the repository root**: the agent writes to `data/` at the root and
several call sites resolve that path against the working directory. `main.py`
puts `apps/agent/` on `sys.path` so imports work regardless.

---

## Deployment

The live demo runs on AWS App Runner from an image in ECR.

**Today, deployment is manual.** The GitHub Actions workflow
(`.github/workflows/deploy.yml`) has never completed successfully: the
repository has **no Actions secrets configured**, so every run fails at
*Configure AWS credentials* before reaching the build. The currently deployed
image was built and pushed by hand.

To make CI deployment work, someone with **admin** on this repository and access
to the AWS account must:

1. Run [`infra/setup-aws.sh`](infra/setup-aws.sh). It creates the ECR
   repository, the GitHub OIDC provider and an IAM role scoped to this
   repository, then prints the values needed below. It reads the account ID from
   `aws sts get-caller-identity`, so it works against any account.
2. Add two repository secrets under *Settings → Secrets and variables → Actions*:
   `AWS_ROLE_ARN` and `APP_RUNNER_SERVICE_ARN`.
3. Trigger *Deploy to AWS App Runner* from the Actions tab — the workflow accepts
   `workflow_dispatch`, so no new commit is needed.

The workflow also deploys automatically on pushes to `main` and `open-demo`.

For a manual deployment in the meantime, [`infra/cloudshell-deploy.sh`](infra/cloudshell-deploy.sh)
runs in AWS CloudShell, which already has Docker and the AWS CLI.

Note that the App Runner service URL is tied to one specific AWS account.
Deploying from a different account produces a different URL, which would need
updating in [`docs/index.html`](docs/index.html) and would orphan any link
printed in already-published materials.

---

## Known issues

**No AWS secrets** — CI deployment is blocked; see *Deployment* above.

**Google Maps billing is not enabled.** The API key in
`apps/dashboard/public/index.html` belongs to a Google Cloud project without a
billing account, so the map renders with "For development purposes only"
watermarks and throws `BillingNotEnabledMapError`. This affects the live
deployment, not just local builds. When billing is enabled the key becomes
chargeable, and it is committed to a public repository — **enable billing and
add HTTP referrer restrictions in the same sitting**, whitelisting
`avtmbfenap.us-east-1.awsapprunner.com/*` and `localhost:3000/*`. Referrer
restriction is Google's intended protection for Maps JS keys, so the key may
stay in source once restricted.

**Project versioning is inconsistent.** `paper.md` describes a v0.1 reference
implementation; the previous README described a v2.3.0 release. These describe
the same repository. A single version scheme should be agreed before JOSS
submission.

**JOSS readiness gaps.** No test suite, no CI for tests, no `CONTRIBUTING.md`,
no `CITATION.cff`. JOSS review checks for these.

---

## Publications

Sung, Y.-J., Hu, Y., Wen, C., Jiang, H., Sun, Y., Jiang, X., Ma, L., He, H.,
Han, Y., Zhang, Y. *Open Analytics Control Tower (OACT): A Public-Interest
Infrastructure Resilience System.* Draft, see [`paper.md`](paper.md).

Archived release: [10.5281/zenodo.18530096](https://doi.org/10.5281/zenodo.18530096)

---

## Contributors

**Principal Investigator:** Yuan-Jiun (David) Sung

**Contributors:** Yidan (Lena) Hu, Hao He, Laisi (Maggie) Ma, Yu (Sebastian) Sun,
Houyu (Harry) Jiang, Xiaochong Jiang, Yu Zhang

See [`NOTICE`](NOTICE) and [`paper.md`](paper.md) for attribution details.

Contact: yuanjius@alumni.cmu.edu · Issues and Discussions are open.

---

## License

Apache License 2.0 — see [`LICENSE`](LICENSE) and [`NOTICE`](NOTICE).
