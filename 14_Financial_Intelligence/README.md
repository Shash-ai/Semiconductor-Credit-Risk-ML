# Phase 14 — Corporate Financial Intelligence

## Objective

Build a professional, evidence-backed corporate-finance layer around the semiconductor project universe without converting public project investment into bank exposure or inventing private underwriting variables.

Phase 14 treats three objects separately:

1. **Project company / sponsor identity** — the entity named in the semiconductor project dataset.
2. **Financial reporting entity** — the exact company, subsidiary, sponsor or parent whose financial statements are being analysed.
3. **Semiconductor project** — the approved project itself.

A parent company's balance sheet must never be represented as the project SPV's financial statements. Public corporate financial analysis also does not create PD, LGD, EAD, ECL, loan DSCR, collateral coverage or covenant headroom unless those inputs are genuinely available from appropriate evidence.

## Phase 14 roadmap

### 14A — Company Financial Master & evidence contract

Implemented through `01_Entity_Master/build_company_financial_master.py`.

Phase 14A establishes:

- stable project-company and financial-entity identifiers;
- exact project-to-financial-entity relationship states;
- a longitudinal financial-statement schema;
- migration of already verified Phase-6F company financial observations;
- a staging table for additional audited financial-statement collection;
- a company-level data-gap register;
- source, scope, audit and verification metadata for every financial observation.

The longitudinal master stores financial-statement facts, not derived credit conclusions. Ratios are deliberately deferred to Phase 14C so raw evidence and analytical transformations remain separable and auditable.

### 14B — Financial statement acquisition & normalization

Collect 5–10 years where available from audited annual reports, stock-exchange/regulatory filings, SEC filings for foreign listed parents, and credible rating-agency financial disclosures. Preserve reporting scope, currency, units and source references.

### 14C — Ratio and DuPont engine

Profitability, leverage, liquidity, coverage, operating efficiency, cash conversion, ROA/ROE/ROCE and DuPont decomposition where the required underlying data are available.

### 14D — Financial trend engine

YoY change, CAGR, margin trend, leverage trend, cash-flow quality, volatility, drawdowns and deterioration/recovery flags.

### 14E — Peer benchmarking

Peer-group percentiles and relative financial positioning. Peer definitions must be explicit and reviewed rather than inferred from the structural project clusters.

### 14F — Semiconductor investment-capacity layer

Analyse project investment relative to verified company scale, such as project investment / revenue, project investment / net worth and project investment / operating cash flow. These are analytical affordability indicators, not sanctioned exposure or EAD.

### 14G — Corporate financial early-warning system

Evidence-driven deterioration and strengthening signals based on longitudinal company fundamentals.

### 14H — Market & credit intelligence

Listed-company market data, valuation, ratings/outlooks and rating transitions where applicable. Market data remain separate from audited accounting facts.

### 14I — Integrated financial-risk layer

Combine corporate financial intelligence with the existing structural, stress, execution and evidence layers while preserving component-level interpretability.

### 14J — Finance dashboard

Professional company tear sheets, longitudinal statements, ratio trends, peer comparisons, project-affordability analysis and evidence confidence.

### 14K — Validation and audit

Statement reconciliation, provenance checks, duplicate-period checks, scope consistency, unit/currency controls and reproducibility.

## Source hierarchy

Preferred evidence order:

1. audited annual report / audited financial statements;
2. stock-exchange or statutory regulatory filing;
3. SEC or equivalent foreign regulator filing;
4. company investor-relations filing;
5. credit-rating-agency financial disclosure;
6. other secondary sources only as cross-checks, not primary accounting evidence.

## Core Phase 14A files

- `00_Config/financial_data_contract.json`
- `01_Entity_Master/Company_Financial_Entity_Master.csv` — generated
- `02_Staging/Financial_Statement_Staging.csv` — generated template; human/source-reviewed inputs enter here
- `03_Master/Company_Financials_Longitudinal.csv` — generated and seeded only from already verified Phase-6F observations
- `04_Audit/Financial_Data_Gap_Register.csv` — generated
- `04_Audit/Phase_14A_Run_Log.jsonl` — generated

## Guardrails

- Project investment is not bank exposure/EAD.
- Parent financials are sponsor context unless the project company and financial reporting entity are demonstrably the same.
- Total liabilities are not automatically treated as financial debt.
- Missing values remain missing; do not infer them from peers or ratios.
- Accounting scope (standalone, consolidated, parent, subsidiary/entity-level) must be stored explicitly.
- Financial years, currencies and units must be source-backed.
- Phase 14 outputs remain research/decision-support analytics and do not automate lending approval or rejection.
