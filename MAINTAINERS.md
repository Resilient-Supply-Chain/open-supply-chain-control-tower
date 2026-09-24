# Maintainer notes

Operational detail, repository conventions and the open issue list. The
[`README`](README.md) is the front door for people arriving at the project;
this file is for the people working on it.

> This repository is public. Nothing here is private — it is separated from the
> README for prominence and tone, not for confidentiality. Credentials,
> unpublished data and anything genuinely sensitive do not belong in this
> repository at all.

---

## Status

| Component | State |
|---|---|
| Dashboard (`apps/dashboard`) | Working — deployed, builds and runs from a clean checkout |
| Risk + impact models (`Asset_Data_Team`) | Working — trained, evaluated, predictions committed |
| Project site (`docs/`) | Working — auto-publishes to GitHub Pages from `main` |
| Manuscript (`paper.md`) | Draft, not yet submitted |
| Agent / chatbot (`apps/agent`) | Unfinished — demo mode only |
| CI deployment | Blocked — no AWS secrets configured |
| Map rendering | Degraded — Google Maps billing not enabled |

---

## Running it locally

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

The map renders with "For development purposes only" watermarks until a
billing-enabled Google Maps key is supplied — see *Known issues*. Risk scoring,
the evidence chain and the API all work regardless.

The agent, which is unfinished, runs from the repository root:

```bash
pip install -r apps/agent/requirements.txt
cp apps/agent/.env.example apps/agent/.env    # then fill in keys
python apps/agent/main.py
```

### API

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

## Repository conventions

**`data/` must stay at the repository root.** `apps/dashboard/src/server.ts`
resolves data as `../../../data/...` relative to `dist/server.js`, and the agent
resolves it from the repository root too. Moving `data/` silently breaks both.

**`docs/` must stay at `docs/`.** GitHub Pages publishes from `main:/docs`.

**`data/input` and `data/output` are runtime**; the applications read and write
them while running. **`data/raw`** holds source datasets that feed model
training and analysis but that nothing reads at runtime. Only specific `input/`
and `output/` paths are copied into the dashboard image, which keeps the
archives out of it.

**The Docker build context is the repository root**, not `apps/dashboard/`.
Building from inside `apps/dashboard/` fails — the Dockerfile references both
`apps/dashboard/` and `data/` by repository-relative path.

**Agent path roots are split.** `config/` travels with the agent, so
`chatbot.py` loads it from `AGENT_ROOT`. `data/` lives at the repository root,
so `app.py`'s `project_root` resolves there. `main.py` puts `apps/agent/` on
`sys.path`, which is why it must be run from the repository root.

---

## Deployment

The live demo runs on AWS App Runner from an image in ECR.

### Current state: deployment is manual

The GitHub Actions workflow (`.github/workflows/deploy.yml`) **has never
completed successfully.** The repository has no Actions secrets, so every run
fails at *Configure AWS credentials* before reaching the build step. Both
recorded runs — 2026-04-22 on `open-demo` and 2026-09-20 on `main` — failed
there. The currently deployed image was built and pushed by hand.

Note that every merge to `main` triggers another failing run until this is
fixed.

### Fixing CI deployment

Requires **admin** on this repository and access to the AWS account:

1. Run [`infra/setup-aws.sh`](infra/setup-aws.sh). It creates the ECR
   repository, the GitHub OIDC provider and an IAM role scoped to this
   repository, then prints the values needed below. It reads the account ID from
   `aws sts get-caller-identity`, so it works against any account and hardcodes
   nothing.
2. Add two repository secrets under *Settings → Secrets and variables → Actions*:
   `AWS_ROLE_ARN` and `APP_RUNNER_SERVICE_ARN`.
3. Trigger *Deploy to AWS App Runner* from the Actions tab. The workflow accepts
   `workflow_dispatch`, so no new commit is needed.

The workflow then deploys automatically on pushes to `main` and `open-demo`.

### Manual deployment

[`infra/cloudshell-deploy.sh`](infra/cloudshell-deploy.sh) runs in AWS
CloudShell, which already provides Docker and the AWS CLI — no local install
needed.

### Account binding

The App Runner service URL is tied to one specific AWS account. The random
service ID in `avtmbfenap.us-east-1.awsapprunner.com` cannot be transferred or
recreated. Deploying from a different account produces a **different URL**,
which would need updating in [`docs/index.html`](docs/index.html) and would orphan any
link printed in already-published materials — check the poster and the SSRN
preprint before considering a migration.

Whoever owns the account also pays for it. App Runner bills for a long-running
service, so a project or institutional account is a better long-term host than a
member's personal one.

---

## Known issues

### Google Maps billing is not enabled

The API key in `apps/dashboard/public/index.html` belongs to a Google Cloud
project without a billing account. The map renders with "For development
purposes only" watermarks and throws `BillingNotEnabledMapError`. **This affects
the live deployment, not just local builds.**

The key is committed to a public repository. While billing is off it cannot
accrue charges, but the moment billing is enabled it becomes chargeable to
whoever owns the project. **Enable billing and add HTTP referrer restrictions in
the same sitting**, whitelisting `avtmbfenap.us-east-1.awsapprunner.com/*` and
`localhost:3000/*`. Referrer restriction is Google's intended protection for
Maps JS keys, so the key may remain in source once restricted.

### The agent is unfinished

`apps/agent` holds a controller chatbot with demo-mode routing, a TF-IDF RAG
engine over legislative text, geodesic SME-radius filtering, an AWS SES alert
mailer, a Gradio UI and a CSV→JSON data bridge. It does not work end to end:

- `src/tools/data_bridge.py` ships placeholder paths. `DEFAULT_CSV_SOURCE` is
  the literal string `"file_path/..."` and `DEFAULT_JSON_OUTPUT` points outside
  the repository. Only the `run_demo_conversion()` call path supplies real paths.
- Live model inference is not wired up; the chatbot returns deterministic demo
  responses.
- Real functionality needs API keys (see `apps/agent/.env.example`) that are not
  provisioned anywhere shared.

### Unmerged branches

Two branches carry work on the agent and have been untouched since 2026-01-28:

- `v2.4.0/react_mode`
- `v2.4.1/model_explanation`

Both edit `src/` heavily, which moved to `apps/agent/src/` in the restructure.
Git recorded those moves as renames so the branches can follow them, but content
conflicts are likely. **Decide whether this work is still wanted** — if it is
abandoned, deleting the branches is cheaper than resolving conflicts later.

### Versioning is inconsistent

`paper.md` describes a v0.1 reference implementation. Earlier README revisions
described a v2.3.0 release. These describe the same repository. A single version
scheme should be agreed before submission.

---

## Manuscript readiness

Gaps that reviewers check for:

- [ ] Test suite — none exists
- [ ] CI running those tests — none exists
- [ ] `CONTRIBUTING.md`
- [ ] `CITATION.cff`
- [ ] API documentation
- [ ] Single agreed version number
- [x] Open license with `LICENSE` and `NOTICE`
- [x] Archived release with a DOI
- [x] Contributor list consistent across `README`, `paper.md` and `NOTICE`

Note that `docs/index.html` lists the three co-contributors printed on the UC
Open 2026 poster. That is a statement about a published artifact, not a general
attribution list, so it intentionally differs from the full contributor list.
