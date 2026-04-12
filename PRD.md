m# PRD — MolForge AI

### Product Requirements Document

**Version:** 1.0 | **Hackathon:** Cognizant Technoverse 2026 | **Domain:** Lifesciences → Drug Discovery

---

## 1. Overview

MolForge AI is an end-to-end agentic drug discovery platform that autonomously takes a disease name as input and outputs a ranked list of novel drug candidates — complete with binding evidence, ADMET safety profiles, and commercial opportunity scores — in under 90 seconds.

**The core promise:** Every molecule in the output is genuinely novel (Tanimoto similarity < 0.85 to any known compound). This is drug _discovery_, not drug _lookup_.

---

## 2. Problem Statement

Drug discovery is the most expensive and failure-prone R&D process in any industry:

- Average timeline: 10–15 years per approved drug
- Average cost: $2.6 billion per approved drug
- Failure rate: 90% of candidates fail in clinical trials
- Root cause of most failures: poor target selection and inadequate early-stage safety prediction — both problems that are data-intensive but not computationally hard

The bottleneck is not scientific knowledge. It is the inability to efficiently synthesise signals across fragmented databases, recent literature, and safety data simultaneously. A researcher today must manually query PubMed, ChEMBL, UniProt, OpenTargets, ClinicalTrials.gov, and run separate chemistry tools — across days or weeks — before a single molecule can be prioritised.

MolForge AI eliminates this bottleneck entirely with an 8-agent autonomous pipeline.

---

## 3. Goals

| Goal | Description                                                                          |
| ---- | ------------------------------------------------------------------------------------ |
| G1   | Accept any disease name and return ranked drug candidates within 90 seconds          |
| G2   | All output molecules must be genuinely novel (Tanimoto < 0.85 vs ChEMBL/PubChem)     |
| G3   | All agents must use only free, open-source tools and APIs (no paid subscriptions)    |
| G4   | Every output must be evidence-grounded — citations, database IDs, accession numbers  |
| G5   | Full ADMET safety profile for every candidate before scoring                         |
| G6   | Market opportunity scoring runs in parallel with science pipeline — no added latency |
| G7   | Live agent activity streaming via WebSocket throughout pipeline execution            |
| G8   | Downloadable PDF report per run                                                      |

## 4. Non-Goals

- This system does NOT replace wet lab validation — it accelerates decisions that precede it
- This system does NOT perform molecular docking simulation (too slow for hackathon scope; P2Rank identifies pocket, docking is future phase)
- This system does NOT handle biologics (antibodies, gene therapy) — small molecules only for MVP
- This system does NOT store user data beyond the active session

---

## 5. User Stories

**As a drug discovery researcher,** I want to type a disease name and get a list of novel candidate molecules with safety profiles, so that I can prioritise which compounds to test in the lab without weeks of manual screening.

**As a biotech founder,** I want to see the commercial opportunity score alongside the scientific scores, so that I can decide whether a drug programme is worth funding before committing resources.

**As a hackathon judge,** I want to see live agent activity as the system runs, so that I understand how the agentic pipeline works and can evaluate its technical sophistication.

**As a pharma R&D strategist,** I want a downloadable PDF report of each run, so that I can share findings with my team and archive candidate data.

---

## 6. Functional Requirements

### FR-001 — Disease Input

- System accepts a plain-text disease name (e.g. "Parkinson's Disease", "Type 2 Diabetes")
- System maps the disease name to ICD-10 code and DisGeNET disease ID automatically
- Input is case-insensitive and handles common abbreviations (T2D, AD, PD)

### FR-002 — Agent 1: Disease Analyst

- Queries PubMed for papers published in the last 3 years using disease keywords
- Queries Europe PMC REST API for additional abstracts
- Queries DisGeNET for gene-disease association scores
- Uses Gemini to extract candidate target proteins from abstracts
- Scores targets by: recency of mention × frequency × DisGeNET association score
- Cross-references with DrugBank to flag targets with low existing drug coverage
- Outputs: 4–6 ranked candidate targets with gene symbols, disease relevance scores, novelty signal

### FR-003 — Agent 2: Target Validator

- Queries OpenTargets GraphQL for disease-target association score (drops < 0.4)
- Queries UniProt for protein function, binding site annotation, known inhibitors
- Queries STRING DB for protein-protein interaction centrality
- Queries Human Protein Atlas for tissue expression matching disease location
- Outputs: 1–2 validated, druggable targets with full evidence dossier

### FR-004 — Agent 3: Structure Resolver

- Queries AlphaFold DB by UniProt accession (primary source)
- Falls back to RCSB PDB for experimentally resolved structures if available and resolution < 2.5Å
- Runs P2Rank to identify top binding pockets from the structure
- Uses BioPython to clean and preprocess the PDB file
- Flags binding pocket regions with pLDDT < 70 as lower-confidence
- Outputs: clean PDB file + binding pocket coordinates + confidence metadata

### FR-005 — Agent 4: Compound Discovery

- Phase 1 (Seed): Queries ChEMBL for compounds with IC50/Ki/Kd < 1µM against validated target
- Phase 1 (Seed): Queries PubChem for SMILES and properties of each seed
- Phase 1 (Filter): Applies Lipinski's Rule of Five via RDKit
- Phase 2 (Scaffold): Extracts Bemis-Murcko scaffolds using RDKit MurckoScaffold
- Phase 2 (Scaffold): Clusters scaffolds using Butina clustering (Morgan fingerprints)
- Phase 3 (Generate — Strategy A): R-group enumeration with ZINC fragment library
- Phase 3 (Generate — Strategy B): BRICS fragmentation and recombination
- Phase 3 (Generate — Strategy C): DeepChem generative model conditioned on known actives
- Phase 4 (Filter): SMILES validity check, Lipinski filter, SA Score ≤ 6.0
- Phase 4 (Filter): Tanimoto novelty check — molecules with similarity > 0.85 to any known compound are deprioritised
- Outputs: 15–25 novel candidate molecules with SMILES, SA scores, novelty scores, scaffold origin

### FR-006 — Agent 5: ADMET Predictor

- Calculates RDKit molecular descriptors: MW, LogP, TPSA, H-bond donors/acceptors, rotatable bonds
- Predicts absorption: oral bioavailability (Lipinski + Veber), Caco-2 permeability (DeepChem TDC)
- Predicts distribution: BBB penetration (DeepChem TDC), plasma protein binding estimate
- Predicts metabolism: CYP3A4, CYP2D6, CYP2C9 inhibition (DeepChem TDC)
- Predicts excretion: renal clearance estimate from TPSA + charge
- Predicts toxicity: hepatotoxicity, hERG cardiotoxicity, Ames mutagenicity, LD50 (DeepChem TDC)
- Hard disqualifiers: hERG IC50 predicted < 1µM = FAIL, Ames positive = FAIL
- Outputs: per-compound ADMET scorecard, PASS/WARN/FAIL verdict, flag details

### FR-007 — Agent 6: Market Analyst (parallel track)

- Queries WHO GHO API using ICD-10 code for prevalence, incidence, mortality, DALYs
- Queries Wikidata SPARQL for epidemiological data and regional breakdowns
- Uses Gemini to estimate TAM from prevalence × drug pricing benchmarks
- Flags orphan disease if global patient population < 200,000
- Outputs: patient population, market size estimate, DALY score, orphan flag

### FR-008 — Agent 7: Competitive Scout (parallel track)

- Queries ClinicalTrials.gov API v2 for active trials in the indication
- Queries OpenFDA for approved drugs in the indication
- Cross-references DrugBank for mechanism of action details
- Assesses target-level competitive density
- Classifies: White Space / Moderate / Crowded
- Outputs: trial counts by phase, approved drug count, density label

### FR-009 — Agent 8: Opportunity Scorer (parallel track)

- Computes Market Attractiveness sub-score from Agent 6 output
- Computes Competitive White Space sub-score from Agent 7 output
- Uses Gemini for Unmet Need Assessment
- Combines: Score = (Market × 0.4) + (White Space × 0.35) + (Unmet Need × 0.25)
- Rating bands: 0.75+ = EXCEPTIONAL, 0.55–0.74 = HIGH, 0.35–0.54 = MEDIUM, < 0.35 = LOW
- Outputs: opportunity score, rating, 3-sentence commercial brief, key flags

### FR-010 — 4D Scorer

- Receives outputs from all 8 agents
- For each PASS/WARN compound from Agent 5:
  - Binding Evidence Score (30%): normalised bioactivity value from ChEMBL seed data
  - ADMET Safety Score (30%): from Agent 5 verdict (PASS=1.0, WARN=0.6, FAIL=0)
  - Literature Support Score (15%): PubMed citation count + recency for target-disease link
  - Market Opportunity Score (25%): from Agent 8 output
- Composite score: weighted sum of all four dimensions
- Verdict: score ≥ 0.7 = GO, 0.5–0.69 = INVESTIGATE, < 0.5 = NO-GO
- Outputs: final ranked candidates list

### FR-011 — Report Generator

- Generates per-run PDF containing:
  - Disease + validated target summary
  - Architecture diagram (static)
  - Per-candidate molecule cards: 2D structure image + ADMET radar chart + scores
  - Market opportunity brief
  - Evidence citations for all data sources used
- PDF is stored at `./backend/jobs/{job_id}.pdf`
- Accessible via GET /api/report/{job_id}

### FR-012 — Frontend Dashboard

- Disease input with loading state during pipeline execution
- Agent Activity Panel: live WebSocket stream of agent start/done messages
- Results Dashboard: ranked molecule cards with GO/INVESTIGATE/NO-GO badges
- Per-molecule ADMET radar chart (recharts)
- Market brief panel with opportunity rating
- PDF download button
- Pre-loaded demo buttons: "Parkinson's Disease", "Type 2 Diabetes", "Alzheimer's Disease"

### FR-013 — WebSocket Live Streaming

- Backend streams status updates as each agent starts and completes
- Message types: agent_start, agent_done, progress, complete, error
- Frontend displays updates in real-time in Agent Activity Panel
- If WebSocket disconnects, frontend falls back to polling /api/status/{job_id}

---

## 7. Non-Functional Requirements

| Requirement                 | Target                                                                            |
| --------------------------- | --------------------------------------------------------------------------------- |
| End-to-end pipeline runtime | < 90 seconds for any disease input                                                |
| API retry logic             | 3 retries, exponential backoff on all external API calls                          |
| SMILES validity             | 100% of output molecules pass RDKit validation                                    |
| Novelty guarantee           | ≥ 80% of output molecules have Tanimoto < 0.85 vs ChEMBL                          |
| External APIs               | 100% free and open-source — zero paid subscriptions                               |
| Concurrent jobs             | Support at least 3 concurrent pipeline runs                                       |
| Error handling              | Non-fatal agent failures log and continue; fatal failures return structured error |
| Demo fallback               | 3 pre-cached disease results for live demo reliability                            |

---

## 8. Data Sources

| Source                  | Agent | Access         | Auth                          |
| ----------------------- | ----- | -------------- | ----------------------------- |
| PubMed (NCBI Entrez)    | 1     | REST API       | Optional API key (rate limit) |
| Europe PMC              | 1     | REST API       | None                          |
| DisGeNET                | 1     | REST API       | Free account                  |
| DrugBank Open Data      | 1, 7  | CSV download   | None                          |
| OpenTargets             | 2     | GraphQL API    | None                          |
| UniProt                 | 2     | REST API       | None                          |
| STRING DB               | 2     | REST API       | None                          |
| Human Protein Atlas     | 2     | REST API       | None                          |
| AlphaFold DB (EMBL-EBI) | 3     | REST API       | None                          |
| RCSB PDB                | 3     | REST API       | None                          |
| ChEMBL                  | 4     | REST API       | None                          |
| PubChem                 | 4     | REST API       | None                          |
| ZINC Fragments          | 4     | File download  | None                          |
| TDC ADMET Benchmarks    | 5     | Python library | None                          |
| WHO GHO                 | 6     | REST API       | None                          |
| Wikidata                | 6     | SPARQL         | None                          |
| ClinicalTrials.gov      | 7     | REST API v2    | None                          |
| OpenFDA                 | 7, 8  | REST API       | None                          |

---

## 9. Success Metrics (Hackathon Evaluation)

| Cognizant Criterion | How MolForge AI Satisfies It                                                                                             |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Business Value      | ADMET-gated, commercially-scored candidates directly reduce pharma R&D cost and failure rate                             |
| Uniqueness          | Hybrid retrieval + generation with Tanimoto novelty filter — competitors will query databases, we generate new chemistry |
| Implementability    | All open-source stack, free APIs, runs on AWS environment provided by Cognizant                                          |
| Scalability         | LangGraph orchestration is horizontally scalable; new agents plug in without changing existing ones                      |

---

## 10. Out of Scope for MVP

- Molecular docking simulation (AutoDock, Glide) — too slow, future phase
- 3D visualisation of protein-ligand binding (py3Dmol interactive) — nice to have, not MVP
- User authentication and saved history — not needed for hackathon
- Multi-disease batch mode — single disease per run for MVP
- Biologics (antibodies, peptides) — small molecules only
- Synthesis route planning — future phase using ASKCOS or similar

---

_MolForge AI PRD v1.0 — Cognizant Technoverse Hackathon 2026_
