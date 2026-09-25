# Contributing to OACT

OACT is a volunteer, public-interest research project. Contributions are
welcome — from bug reports and data corrections to model work and documentation.

## Getting oriented

- [`README.md`](README.md) — what the project is and what the demonstration covers
- [`MAINTAINERS.md`](MAINTAINERS.md) — how to run it, repository conventions, deployment, known issues
- [`Asset_Data_Team/README.md`](Asset_Data_Team/README.md) — model methodology, features and metrics

Start the dashboard locally before changing anything:

```bash
docker build -f apps/dashboard/Dockerfile -t osct-web .
docker run --rm -p 3000:3000 osct-web
```

The build context is the repository root, not `apps/dashboard/`. That and the
other non-obvious conventions are explained in `MAINTAINERS.md`.

## Reporting a bug

Open an issue. The most useful reports include:

- The route or page that failed, and what you expected instead
- Container logs (`docker logs <container>`) or the browser console
- Whether it reproduces on the [live demo](https://avtmbfenap.us-east-1.awsapprunner.com/) or only locally

If the map shows "For development purposes only" watermarks, that is a known
issue with the Google Maps key, not a bug in your setup — see *Known issues* in
`MAINTAINERS.md`.

## Asking a question

Use [GitHub Discussions](https://github.com/Resilient-Supply-Chain/open-supply-chain-control-tower/discussions)
for questions about using OACT or interpreting its output. For questions about
the research direction or collaboration, contact the Principal Investigator at
yuanjius@alumni.cmu.edu.

## Proposing a change

1. **Open an issue first** for anything beyond a typo or an obvious fix. It is
   cheaper to agree on the approach than to rework a finished branch — several
   parts of this repository have non-obvious path constraints.
2. **Branch from `main`.** Use a descriptive prefix: `fix/`, `feat/`, `docs/`,
   `chore/`.
3. **Keep the change focused.** One concern per pull request.
4. **Say what you verified.** There is no test suite yet, so the pull request
   description carries that weight. State what you ran and what you observed —
   "built the image and confirmed `/api/risks` still returns 200 for 2023-01-07"
   is worth more than "should work".
5. **Open a pull request** describing the problem, the approach, and anything
   you chose not to do.

### Things that break silently

Worth knowing before you move files:

- **`data/` must stay at the repository root.** `apps/dashboard/src/server.ts`
  resolves it as `../../../data/...` relative to `dist/server.js`.
- **`docs/` must stay at `docs/`.** GitHub Pages publishes from `main:/docs`.
- Only specific `data/input` and `data/output` paths are copied into the
  dashboard image. A new runtime data file needs a matching `COPY` in the
  Dockerfile.

## Contributing data or model work

Model changes should state, in the pull request:

- What data the change is trained or evaluated on, and its provenance
- Which metrics moved and in which direction
- Whether the change affects the `Risk = P̂(x) × I(x)` composition

OACT is built on **public data only**. Contributions must not introduce
proprietary, licensed or otherwise non-redistributable datasets — reproducibility
from open sources is a design constraint, not a preference.

## Citing policy and legislation

Cite legislation and executive orders with a source and an accessed date, the
way `paper.bib` does for S.257. Do not assert current alignment with an
instrument in prose without checking its status first — one previously cited
executive order had been revoked.

## Attribution

Contributors are credited in [`NOTICE`](NOTICE), [`CITATION.cff`](CITATION.cff)
and the manuscript author list. If your contribution warrants it and you are not
listed, say so in your pull request or contact the PI.

## Code of conduct

Be straightforward and courteous. Assume good faith, critique work rather than
people, and keep discussion on the technical and scientific merits.

## License

By contributing, you agree that your contributions are licensed under the
[Apache License 2.0](LICENSE), the same license that covers this project.
