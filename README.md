## AI Control Tower for U.S. Supply-Chain Resilience (v0.0.1)

An **AI-driven nerve center for proactive supply chain defense**, focused on protecting U.S. small and medium-sized enterprises (SMEs) from cascading disruptions.

### Vision

- **AI control tower**: Continuously ingests structured risk signals, maps them to real-world SME exposure, and generates **actionable, human-readable resilience reports**.
- **Defense-first orientation**: Prioritizes early warning, triage, and mitigations for SMEs that are often downstream in complex multi-tier supply chains.
- **Extensible by design**: Built to plug in regulatory, logistics, and climate intelligence via future RAG (retrieval-augmented generation) modules.

### Policy & Legislative Alignment

This project is explicitly designed to support and operationalize recent U.S. supply-chain resilience policy:

- **S.257 – Resilient Supply Chains Act**: Provides an analytical and monitoring backbone for identifying vulnerabilities, prioritizing critical sectors, and tracking the impact of disruptions on U.S. SMEs.
- **H.R.6571 (context)**: Aligns with congressional intent to **strengthen supply-chain transparency, monitoring, and risk mitigation** across critical and strategic sectors.
- **Executive Order 14123 – Safe, Secure, and Trustworthy Development and Use of Artificial Intelligence**: Implements AI-driven analytics and decision support in a manner consistent with **safety, robustness, transparency, and accountability**.

The control tower is envisioned as a **policy-aligned technical reference implementation** that federal, state, and regional partners could adapt to:

- Monitor sectoral and geographic risk to SMEs.
- Translate upstream disruptions (ports, weather, geopolitical events, cyber incidents) into downstream business impacts.
- Generate **auditable, text-first resilience briefings** suitable for policymakers, economic development agencies, and SME coalitions.

### v0.0.1 Scope

Version **v0.0.1** focuses narrowly on a minimal but realistic end-to-end path:

1. **Type-safe Risk Signal Ingestion (Pydantic)**
   - Define a strict `RiskSignal` model for external risk events.
   - Enforce schema, type safety, and validation for incoming signals.

2. **Local SME Geography Mapping (Mock Data)**
   - Load a local `sme_registry.json` containing a small registry of SMEs (initially **Monterey County, CA** as a testbed geography).
   - Provide a reusable `geo_utils` tool to map risk locations to potentially affected SMEs.

3. **Automated Resilience Report Generation (Claude 3.5 Sonnet + PydanticAI)**
   - Implement a `resilience_agent` powered by **PydanticAI** (backed by Claude 3.5 Sonnet in downstream deployments).
   - The agent:
     - Consumes a validated `RiskSignal`.
     - Uses tools to lookup SMEs in the affected geography.
     - Produces a **Markdown “Supply Chain Alert”** with structured recommendations.
   - If `risk_score > 0.9`, the agent must generate a **High-Priority Supply Chain Alert**.

### Architecture Overview (v0.0.1)

- **`src/models/`**
  - `signal.py`: Pydantic model(s) for inbound risk signals.
  - `report.py`: Pydantic model(s) describing structured alert / report outputs.

- **`src/tools/`**
  - `geo_utils.py`: Utility and tool functions to map a risk signal’s location to SMEs from the local registry (e.g., by county, city, or ZIP approximation).

- **`src/agents/`**
  - `resilience_agent.py`: PydanticAI-powered agent that orchestrates:
    - Risk signal interpretation.
    - SME lookup via tools.
    - Policy-informed narrative generation (Markdown) for supply-chain resilience.

- **`data/`**
  - `sme_registry.json`: Minimal mocked registry of SMEs in Monterey County with sectors, sizes, and simple location metadata.

### Design Principles

- **Strict typing & Pydantic models**: All inputs/outputs are strongly typed to support monitoring, auditing, and safe extension.
- **Tool-based agent design**: The core logic is decomposed into reusable tools (e.g., geographic mapping) so that future RAG modules for regulatory and sectoral intelligence can be added without rewriting the agent.
- **Auditability**: Every generated alert is backed by explicit inputs (risk signals + SME registry entries) and a typed report structure.
- **Policy extensibility**: Future versions can integrate:
  - RAG over statutory and regulatory texts (e.g., S.257, related statutes, executive orders, and agency guidance).
  - Sector-specific playbooks for critical infrastructure, logistics, agriculture, healthcare, etc.

### Getting Started (Developer Preview)

> Note: v0.0.1 is a **developer preview** and assumes access to Claude 3.5 Sonnet via PydanticAI configuration in your environment.

1. **Install dependencies** (example):

   ```bash
   pip install -r requirements.txt
   ```

2. **Run a sample risk analysis** (placeholder CLI / notebook to be added in later versions):

   - Construct a `RiskSignal` (e.g., port disruption, extreme weather in Monterey County).
   - Invoke the `resilience_agent` to generate a Markdown alert.
   - Review the structured `Report` object and rendered Markdown.

### Roadmap (Beyond v0.0.1)

- **v0.1.x**: CLI & API endpoints; richer SME registry schema (NAICS, upstream/downstream linkages).
- **v0.2.x**: RAG-based regulatory and policy grounding; sector-specific resilience templates.
- **v0.3.x+**: Integration with live data feeds (BTS, NOAA, port operations, critical infrastructure notifications), dashboards, and multi-jurisdiction collaboration workflows.

Contributions, design critiques, and policy feedback are welcome, especially from:

- SME coalitions and regional economic development organizations.
- Federal, state, and local agencies working on supply-chain resilience.
- Researchers and practitioners in logistics, climate risk, and AI safety.

