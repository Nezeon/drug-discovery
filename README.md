<div align="center">

# MolForge AI

### From Disease to Drug Candidate — Autonomously

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.135-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.1-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![RDKit](https://img.shields.io/badge/RDKit-2026.3-FF6F00?style=for-the-badge)](https://www.rdkit.org)
[![DeepChem](https://img.shields.io/badge/DeepChem-2.8-8B5CF6?style=for-the-badge)](https://deepchem.io)
[![License](https://img.shields.io/badge/License-MIT-0D9488?style=for-the-badge)](LICENSE)

<br/>

**An end-to-end agentic drug discovery platform that takes a disease name as input and autonomously outputs a ranked list of novel drug candidates — complete with binding evidence, ADMET safety profiles, and commercial opportunity scores.**

<br/>

[Getting Started](#getting-started) | [Architecture](#architecture) | [How It Works](#how-it-works) | [API Reference](#api-reference) | [Demo](#demo)

<br/>

<img src="https://img.shields.io/badge/Cognizant_Technoverse_Hackathon_2026-Lifesciences-0D9488?style=for-the-badge" alt="Hackathon Badge"/>

</div>

---

## The Problem

Conventional drug discovery takes **10-15 years** and costs over **$2.6 billion** per approved drug. Early-stage target identification and lead generation alone consume 3-5 years of researcher time — most of it spent on repetitive literature mining, database lookups, and manual compound screening.

## The Solution

MolForge AI compresses the entire early-stage discovery pipeline into a single autonomous run. Type a disease name. In under 90 seconds, receive a ranked list of genuinely novel drug candidates with full safety profiles and market analysis.

**Every molecule is novel.** A Tanimoto similarity filter ensures all output compounds have <0.85 similarity to any known drug in ChEMBL or PubChem. These are not database lookups — they are newly generated molecular structures.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **8 Specialized AI Agents** | Each agent handles one domain — literature mining, target validation, structure resolution, compound generation, ADMET prediction, and market analysis |
| **Genuine Molecular Novelty** | RDKit enumeration + BRICS fragmentation + Tanimoto filtering guarantee molecules that don't yet exist as known drugs |
| **4D Composite Scoring** | Binding x ADMET x Literature x Market scores produce GO / INVESTIGATE / NO-GO verdicts |
| **11 Free Biomedical APIs** | PubMed, ChEMBL, AlphaFold, OpenTargets, UniProt, ClinicalTrials.gov, and more — zero paid subscriptions |
| **Real-Time Agent Streaming** | WebSocket-powered live feed shows each agent's progress as it runs |
| **ADMET Safety Gating** | DeepChem TDC models predict absorption, metabolism, toxicity — hERG and Ames failures are auto-rejected |
| **Parallel Market Analysis** | Market sizing, competitive landscape, and opportunity scoring run simultaneously with the science track |
| **PDF Report Generation** | Downloadable publication-ready reports with molecule cards, ADMET summaries, and market briefs |
| **Evidence-Grounded** | Every output links back to PubMed IDs, ChEMBL IDs, UniProt accessions, and clinical trial numbers |
| **Dark-Mode Dashboard** | React + Tailwind UI with molecule visualizations, ADMET radar charts, and animated score rings |

---

## Architecture

```
                          User enters disease name
                                    |
                                    v
                        +---------------------+
                        |    React Frontend    |
                        |  (Vite + Tailwind)   |
                        +---------------------+
                           |             ^
                    POST /discover    WebSocket
                           |             |
                           v             |
                        +---------------------+
                        |   FastAPI Backend    |
                        |   (Uvicorn ASGI)     |
                        +---------------------+
                                    |
                                    v
                        +---------------------+
                        | LangGraph Orchestrator|
                        +---------------------+
                                    |
                    +---------------+---------------+
                    |                               |
              Science Track                   Market Track
              (sequential)                    (parallel)
                    |                               |
        +-----------+-----------+          +--------+--------+
        |           |           |          |        |        |
   Agent 1     Agent 2     Agent 3    Agent 6   Agent 7   Agent 8
   Disease     Target     Structure   Market   Competitive Opportunity
   Analyst    Validator   Resolver    Analyst    Scout      Scorer
        |           |           |          |        |        |
        v           v           v          +--------+--------+
   Agent 4     Agent 5                             |
   Compound     ADMET                              |
   Discovery   Predictor                           |
        |           |                              |
        +-----------+------------------------------+
                    |
                    v
            +---------------+
            | 4D Scorer &   |
            |    Ranker     |
            +---------------+
                    |
                    v
            +---------------+
            |    Report     |
            |   Generator   |
            +---------------+
                    |
                    v
        GO / INVESTIGATE / NO-GO
          + PDF Report Download
```

### Agent Pipeline

| # | Agent | Role | Data Sources | Output |
|---|-------|------|-------------|--------|
| 1 | **Disease Analyst** | Mine literature for emerging protein targets | PubMed, Europe PMC, DisGeNET | Ranked target list with novelty signals |
| 2 | **Target Validator** | Validate druggability and disease association | OpenTargets, UniProt, STRING, HPA | Validated target with druggability score |
| 3 | **Structure Resolver** | Fetch 3D structure and identify binding pockets | AlphaFold DB, RCSB PDB | PDB file + binding pocket coordinates |
| 4 | **Compound Discovery** | Generate novel molecular candidates | ChEMBL (seeds), RDKit, DeepChem | 15-25 novel compounds with scaffolds |
| 5 | **ADMET Predictor** | Predict safety and pharmacokinetics | DeepChem TDC models, RDKit descriptors | Full ADMET profile per compound |
| 6 | **Market Analyst** | Estimate patient population and market size | WHO GHO, Wikidata | Market sizing + orphan drug flag |
| 7 | **Competitive Scout** | Map competitive landscape | ClinicalTrials.gov, OpenFDA | Trial counts, approved drugs, density |
| 8 | **Opportunity Scorer** | Synthesize commercial opportunity | Aggregated market + competitive data | Opportunity score + commercial brief |

---

## How It Works

### 1. Literature Mining & Target Discovery

The Disease Analyst fetches up to 50 recent abstracts from PubMed and Europe PMC, stores them in a ChromaDB vector store, and uses Gemini 2.0 Flash to extract protein targets with evidence strength and novelty signals. Targets with fewer than 3 existing approved drugs are flagged as novel.

### 2. Target Validation

The Target Validator cross-references each candidate target against OpenTargets (association score >= 0.4), UniProt (protein existence), STRING DB (protein-protein interactions), and Human Protein Atlas (tissue expression). Only targets passing all checks proceed.

### 3. Structure Resolution

AlphaFold DB or RCSB PDB provides the 3D protein structure. The system validates pLDDT confidence scores and identifies binding pockets for downstream analysis.

### 4. Novel Compound Generation

This is the core innovation. The Compound Discovery agent:

1. **Seeds** from ChEMBL actives (IC50/Ki/Kd < 1 uM) for the validated target
2. **Extracts** Bemis-Murcko scaffolds and clusters by Butina diversity (cutoff 0.4)
3. **Generates** via two parallel strategies:
   - **R-group enumeration**: 20 drug-like substituents (F, Cl, CF3, methoxy, cyclopropyl, piperidyl, etc.) applied to each seed scaffold
   - **BRICS fragmentation**: RDKit BRICS decomposition + recombination of fragment pools
4. **Filters** every molecule through a 4-stage pipeline:
   - SMILES validity (RDKit parse check)
   - Lipinski Rule of Five (MW <= 500, LogP <= 5, HBD <= 5, HBA <= 10)
   - Synthetic Accessibility score <= 6.0
   - **Novelty**: Tanimoto similarity < 0.85 vs all known ChEMBL compounds (Morgan fingerprints, radius=2, 2048 bits)

### 5. ADMET Safety Prediction

DeepChem TDC models predict:
- **Absorption**: Caco-2 permeability
- **Distribution**: Blood-brain barrier penetration
- **Metabolism**: CYP3A4/CYP2D6/CYP2C9 inhibition
- **Excretion**: Clearance estimation
- **Toxicity**: hERG cardiotoxicity, Ames mutagenicity, LD50

Hard disqualifiers: hERG IC50 < 1 uM or Ames positive = immediate **FAIL**.

### 6. Parallel Market Track

Running simultaneously with the science pipeline:
- **Market Analyst** queries WHO GHO + Wikidata for patient population, DALYs, and market sizing
- **Competitive Scout** queries ClinicalTrials.gov + OpenFDA for active trials and approved drugs
- **Opportunity Scorer** synthesizes a commercial opportunity score (40% market + 35% white space + 25% unmet need)

### 7. 4D Composite Scoring

Every candidate receives a composite score:

```
Composite = (0.30 x Binding) + (0.30 x ADMET) + (0.15 x Literature) + (0.25 x Market)
```

| Verdict | Threshold | Meaning |
|---------|-----------|---------|
| **GO** | >= 0.70 | Strong candidate for further development |
| **INVESTIGATE** | 0.50 - 0.69 | Promising but needs additional validation |
| **NO-GO** | < 0.50 | Does not meet minimum criteria |

---

## Tech Stack

### Backend

| Technology | Version | Purpose |
|-----------|---------|---------|
| Python | 3.12+ | Runtime |
| FastAPI | 0.135.3 | REST API + WebSocket server |
| LangGraph | 1.1.6 | Agent orchestration with parallel branches |
| LangChain | 1.2.15 | LLM framework + tool integration |
| Gemini 2.0 Flash | latest | LLM for agent reasoning |
| RDKit | 2026.3.1 | Cheminformatics (SMILES, fingerprints, scaffolds) |
| DeepChem | 2.8.1 | ADMET prediction models |
| ChromaDB | 0.5.23 | Vector store for literature RAG |
| ReportLab | 4.2.5 | PDF report generation |
| httpx | 0.28.1 | Async HTTP client |

### Frontend

| Technology | Version | Purpose |
|-----------|---------|---------|
| React | 18.3.1 | UI framework |
| Vite | 6.0.5 | Build tool + dev server |
| Tailwind CSS | 4.0.0 | Utility-first styling |
| Framer Motion | 12.38.0 | Animations and transitions |
| Recharts | 2.13.3 | ADMET radar charts + score bars |
| 3Dmol.js | 2.5.4 | 3D protein structure viewer |
| Lucide React | 0.468.0 | Icon library |
| Axios | 1.7.7 | HTTP client |

### External APIs (all free)

| API | Used By | Purpose |
|-----|---------|---------|
| PubMed (NCBI Entrez) | Agent 1 | Biomedical literature search |
| Europe PMC | Agent 1 | Additional literature coverage |
| DisGeNET | Agent 1 | Gene-disease associations |
| OpenTargets | Agent 2 | Target-disease association scores |
| UniProt | Agent 2 | Protein metadata + existence validation |
| STRING DB | Agent 2 | Protein-protein interaction networks |
| Human Protein Atlas | Agent 2 | Tissue expression data |
| AlphaFold DB | Agent 3 | Predicted protein structures |
| RCSB PDB | Agent 3 | Experimental protein structures |
| ChEMBL | Agent 4 | Known active compounds (seeds) |
| PubChem | Agent 4 | Compound cross-reference |
| WHO GHO | Agent 6 | Global disease burden statistics |
| Wikidata | Agent 6 | Epidemiological data via SPARQL |
| ClinicalTrials.gov | Agent 7 | Active clinical trials |
| OpenFDA | Agent 7, 8 | Approved drugs and adverse events |

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- A Google Gemini API key ([get one free](https://aistudio.google.com/apikey))

### Installation

```bash
# Clone the repository
git clone https://github.com/Nezeon/drug-discovery.git
cd drug-discovery

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Pre-load DeepChem ADMET models (run once)
python tools/preload_models.py

# Start backend
uvicorn main:app --reload --port 8000
```

```bash
# Frontend setup (new terminal)
cd frontend
npm install

# Configure environment
cp .env.example .env

# Start frontend
npm run dev
# Open http://localhost:5173
```

### Verify Installation

```bash
curl http://localhost:8000/health
# {"status": "ok", "chroma": "connected", "gemini": "reachable", "rdkit": "ok"}
```

### Environment Variables

```env
# backend/.env
GEMINI_API_KEY=your_gemini_api_key_here    # Required
CHROMA_PERSIST_DIR=./chroma_db             # ChromaDB storage path
PUBMED_API_KEY=                            # Optional — increases rate limit
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
MAX_CANDIDATES=25                          # Max molecules from Agent 4
NOVELTY_THRESHOLD=0.85                     # Tanimoto similarity cutoff
SA_SCORE_MAX=6.0                           # Max synthetic accessibility

# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

---

## API Reference

### Start Discovery Pipeline

```http
POST /api/discover
Content-Type: application/json

{
  "disease": "Parkinson's Disease"
}
```

**Response:**
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "started",
  "ws_url": "ws://localhost:8000/ws/job_a1b2c3d4"
}
```

### Poll Job Status

```http
GET /api/status/{job_id}
```

```json
{
  "status": "running",
  "current_agent": "compound_discovery",
  "progress_pct": 45,
  "updates": [
    "Disease Analyst: found 5 targets",
    "Target Validator: LRRK2 validated (0.87)"
  ]
}
```

### Get Results

```http
GET /api/results/{job_id}
```

```json
{
  "disease": "Parkinson's Disease",
  "validated_target": {
    "gene_symbol": "LRRK2",
    "uniprot_id": "Q5S007",
    "druggability_score": 0.87
  },
  "final_candidates": [
    {
      "smiles": "CC1=CC=C(C=C1)NC2=NC=CC(=N2)N3CCN(CC3)C",
      "composite_score": 0.81,
      "binding_score": 0.85,
      "admet_score": 0.78,
      "literature_score": 0.72,
      "market_score": 0.91,
      "verdict": "GO",
      "novelty_score": 0.94,
      "admet_detail": {
        "absorption": "PASS",
        "herg": "PASS",
        "hepatotoxicity": "WARN"
      },
      "svg_url": "/api/molecule/svg/job_a1b2c3d4/0"
    }
  ],
  "market_brief": {
    "patient_population": "10M globally",
    "market_size": "$6.1B",
    "opportunity_rating": "EXCEPTIONAL"
  },
  "report_url": "/api/report/job_a1b2c3d4"
}
```

### Other Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness check (Gemini, RDKit, ChromaDB) |
| `GET` | `/api/molecule/svg/{job_id}/{index}` | 2D molecule structure as SVG |
| `GET` | `/api/candidate/{job_id}/{index}` | Full candidate detail |
| `GET` | `/api/protein/pdb/{job_id}` | PDB file download |
| `GET` | `/api/report/{job_id}` | PDF report download |
| `WS` | `/ws/{job_id}` | Real-time agent activity stream |

### WebSocket Messages

```json
{"type": "agent_start",  "agent": "compound_discovery", "message": "Seeding from ChEMBL..."}
{"type": "agent_done",   "agent": "compound_discovery", "message": "Generated 18 novel candidates"}
{"type": "progress",     "pct": 60}
{"type": "complete",     "message": "Analysis complete. 3 GO candidates found."}
{"type": "error",        "agent": "market_analyst", "message": "WHO GHO rate limit, retrying..."}
```

---

## Scoring System

### 4D Composite Score

Each candidate is scored across four independent dimensions:

```
Composite = (0.30 x Binding) + (0.30 x ADMET) + (0.15 x Literature) + (0.25 x Market)
```

| Dimension | Weight | Source | Range |
|-----------|--------|--------|-------|
| **Binding** | 30% | ChEMBL IC50 data or novelty proxy | 0.0 - 1.0 |
| **ADMET** | 30% | DeepChem TDC model predictions | 0.0 - 1.0 |
| **Literature** | 15% | OpenTargets association score | 0.0 - 1.0 |
| **Market** | 25% | Opportunity Scorer output | 0.0 - 1.0 |

### Verdict Bands

| Verdict | Score Range | Action |
|---------|------------|--------|
| **GO** | >= 0.70 | Strong candidate — advance to lead optimization |
| **INVESTIGATE** | 0.50 - 0.69 | Promising — needs additional validation or analog exploration |
| **NO-GO** | < 0.50 | Below threshold — deprioritize |

### ADMET Hard Disqualifiers

- hERG IC50 < 1 uM (cardiotoxicity risk) = **immediate FAIL**
- Ames positive (mutagenicity) = **immediate FAIL**

---

## Novelty Guarantee

MolForge AI does not simply retrieve known drugs from databases. Every output molecule is verified to be genuinely novel:

1. **Seed compounds** are fetched from ChEMBL as starting material
2. **Scaffolds** are extracted and clustered for diversity
3. **New molecules** are generated via R-group enumeration (20 drug-like substituents) and BRICS fragmentation/recombination
4. **Novelty filter** computes Tanimoto similarity using Morgan fingerprints (radius=2, 2048 bits) against all known ChEMBL compounds for the target
5. **Any molecule with similarity >= 0.85 is rejected**

The result: every compound in the output represents a structurally novel chemical entity that does not exist in ChEMBL or PubChem.

---

## Project Structure

```
molforge-ai/
|
+-- backend/
|   +-- main.py                       # FastAPI app + all routes
|   +-- config.py                     # Environment configuration
|   +-- models.py                     # Pydantic request/response schemas
|   |
|   +-- orchestrator/
|   |   +-- graph.py                  # LangGraph pipeline definition
|   |   +-- state.py                  # MolForgeState TypedDict
|   |   +-- runner.py                 # Async job execution manager
|   |
|   +-- agents/
|   |   +-- base_agent.py             # Shared base class (retry, JSON parsing)
|   |   +-- disease_analyst.py        # Agent 1 - Literature mining
|   |   +-- target_validator.py       # Agent 2 - Druggability validation
|   |   +-- structure_resolver.py     # Agent 3 - Protein structure
|   |   +-- compound_discovery.py     # Agent 4 - Novel molecule generation
|   |   +-- admet_predictor.py        # Agent 5 - Safety prediction
|   |   +-- market_analyst.py         # Agent 6 - Market sizing
|   |   +-- competitive_scout.py      # Agent 7 - Competitive landscape
|   |   +-- opportunity_scorer.py     # Agent 8 - Commercial opportunity
|   |   +-- biologics_analyst.py      # Biologics modality analysis
|   |
|   +-- chemistry/
|   |   +-- scaffold.py               # Bemis-Murcko scaffolds + Butina clustering
|   |   +-- generator.py              # R-group enumeration + BRICS generation
|   |   +-- filters.py                # Lipinski, SA score, novelty filtering
|   |   +-- visualizer.py             # SMILES to SVG/PNG rendering
|   |
|   +-- scorer/
|   |   +-- scorer.py                 # 4D composite scoring engine
|   |
|   +-- tools/                        # External API client wrappers
|   |   +-- pubmed_client.py          # PubMed Entrez API
|   |   +-- europepmc_client.py       # Europe PMC REST
|   |   +-- opentargets_client.py     # OpenTargets GraphQL
|   |   +-- uniprot_client.py         # UniProt REST
|   |   +-- alphafold_client.py       # AlphaFold DB API
|   |   +-- pdb_client.py             # RCSB PDB REST
|   |   +-- chembl_client.py          # ChEMBL REST (rate-limited)
|   |   +-- pubchem_client.py         # PubChem REST
|   |   +-- who_gho_client.py         # WHO Global Health Observatory
|   |   +-- clinicaltrials_client.py  # ClinicalTrials.gov v2
|   |   +-- openfda_client.py         # OpenFDA REST
|   |   +-- disgenet_client.py        # DisGeNET associations
|   |   +-- string_client.py          # STRING PPI network
|   |   +-- hpa_client.py             # Human Protein Atlas
|   |   +-- docking_client.py         # Docking proxy
|   |   +-- retrosynthesis_client.py  # ASKCOS retrosynthesis
|   |   +-- wikidata_client.py        # Wikidata SPARQL
|   |   +-- preload_models.py         # DeepChem TDC model downloader
|   |
|   +-- rag/
|   |   +-- chroma_store.py           # ChromaDB literature vector store
|   |
|   +-- report/
|   |   +-- report_generator.py       # ReportLab PDF generation
|   |
|   +-- ws/
|   |   +-- manager.py                # WebSocket connection manager
|   |
|   +-- tests/                        # Integration + unit tests
|
+-- frontend/
|   +-- src/
|   |   +-- App.jsx                   # Root app with page routing
|   |   +-- main.jsx                  # React entry point
|   |   +-- index.css                 # Tailwind base + custom styles
|   |   +-- api/
|   |   |   +-- discover.js           # Backend API client
|   |   |   +-- history.js            # Job history management
|   |   +-- components/
|   |       +-- DiseaseInput.jsx      # Hero section + search form
|   |       +-- AgentActivityPanel.jsx # WebSocket agent stream
|   |       +-- ResultsDashboard.jsx  # Main results layout
|   |       +-- MoleculeCard.jsx      # Candidate molecule card
|   |       +-- MoleculeViz.jsx       # 2D molecule renderer
|   |       +-- AdmetRadar.jsx        # Recharts ADMET radar chart
|   |       +-- ScoreBadge.jsx        # GO/INVESTIGATE/NO-GO badge
|   |       +-- ScoreRing.jsx         # Animated SVG score ring
|   |       +-- MarketBrief.jsx       # Market opportunity panel
|   |       +-- CandidateDetail.jsx   # Full candidate deep-dive
|   |       +-- ProteinViewer.jsx     # 3Dmol protein structure viewer
|   |       +-- ReportDownload.jsx    # PDF download button
|   |       +-- ParticleBackground.jsx # Animated background
|   +-- index.html
|   +-- vite.config.js
|   +-- tailwind.config.js
|   +-- package.json
```

---

## Demo

### Quick Start Demo

MolForge AI supports three pre-validated demo diseases for reliable demonstrations:

| Disease | Expected Target | Expected GO Candidates |
|---------|----------------|----------------------|
| Parkinson's Disease | LRRK2 | 2-4 |
| Type 2 Diabetes | GLP1R / DPP4 | 3-5 |
| Alzheimer's Disease | BACE1 / TREM2 | 1-3 |

```bash
# Start both servers, then open http://localhost:5173
# Type "Parkinson's Disease" and click Discover
# Watch the agent activity panel stream in real-time
# Browse molecule cards, ADMET radars, and market briefs
# Download the PDF report
```

---

## Design System

MolForge AI uses a dark-mode-only design system built on Tailwind CSS:

| Token | Value | Usage |
|-------|-------|-------|
| Primary Teal | `#0D9488` | Buttons, GO badges, agent-done indicators |
| Accent Violet | `#7C3AED` | Active agent pulse, secondary actions |
| Background Base | `#020617` | Page background (slate-950) |
| Card Background | `#0F172A` | Cards, panels (slate-900) |
| Text Primary | `#F8FAFC` | Headings, body text (slate-50) |
| Text Secondary | `#94A3B8` | Labels, metadata (slate-400) |

### Verdict Badges

| Verdict | Background | Text | Border |
|---------|-----------|------|--------|
| **GO** | `teal-600/15` | `#2DD4BF` | `teal-600/30` |
| **INVESTIGATE** | `amber-500/15` | `#FCD34D` | `amber-500/30` |
| **NO-GO** | `red-500/15` | `#F87171` | `red-500/30` |

---

## Testing

```bash
cd backend

# Run individual agent tests
python -m pytest tests/test_disease_analyst.py -v
python -m pytest tests/test_target_validator.py -v
python -m pytest tests/test_structure_resolver.py -v
python -m pytest tests/test_compound_discovery.py -v
python -m pytest tests/test_admet_predictor.py -v
python -m pytest tests/test_market_pipeline.py -v

# Run full pipeline integration test
python -m pytest tests/test_full_pipeline.py -v
python -m pytest tests/test_complete_pipeline.py -v

# Run all tests
python -m pytest tests/ -v
```

---

## Configuration Reference

### Novelty & Chemistry Thresholds

| Parameter | Default | Description |
|-----------|---------|-------------|
| `NOVELTY_THRESHOLD` | 0.85 | Maximum Tanimoto similarity to known compounds |
| `SA_SCORE_MAX` | 6.0 | Maximum synthetic accessibility (1=easy, 10=hard) |
| `MAX_CANDIDATES` | 25 | Maximum compounds from Agent 4 |
| Morgan FP radius | 2 | Fingerprint radius for similarity computation |
| Morgan FP bits | 2048 | Fingerprint vector length |
| Butina cutoff | 0.4 | Scaffold clustering distance cutoff |
| Lipinski MW | <= 500 | Molecular weight limit |
| Lipinski LogP | <= 5 | Partition coefficient limit |
| Lipinski HBD | <= 5 | Hydrogen bond donor limit |
| Lipinski HBA | <= 10 | Hydrogen bond acceptor limit |

### Scoring Weights

| Dimension | Weight | Adjustable In |
|-----------|--------|---------------|
| Binding | 0.30 | `scorer/scorer.py` |
| ADMET | 0.30 | `scorer/scorer.py` |
| Literature | 0.15 | `scorer/scorer.py` |
| Market | 0.25 | `scorer/scorer.py` |

### API Rate Limits

| API | Limit | Handling |
|-----|-------|----------|
| ChEMBL | 5 req/s | `asyncio.sleep(0.2)` between calls |
| PubMed | 3 req/s (10 with key) | Optional `PUBMED_API_KEY` |
| All APIs | Various | 3 retries, exponential backoff (2^n seconds) |

---

## How It's Different

| Feature | Traditional Screening | Database Lookup Tools | **MolForge AI** |
|---------|----------------------|----------------------|-----------------|
| Novel molecules | No (screens existing) | No (retrieves known) | **Yes (generates + filters)** |
| ADMET before scoring | Rarely | No | **Yes (every candidate)** |
| Market analysis | Separate team | No | **Parallel, automated** |
| Time to candidates | Months | Minutes | **< 90 seconds** |
| Evidence trail | Manual | Partial | **Full (PubMed, ChEMBL, UniProt IDs)** |
| Cost | $$$$ | $ | **Free (all open APIs)** |
| Live progress | No | No | **WebSocket streaming** |

---

## Limitations

- **No wet lab validation** — MolForge AI is a computational accelerator, not a replacement for experimental validation
- **No molecular dynamics or docking** — binding scores are proxy-based from ChEMBL bioactivity data, not from physics-based simulations
- **Small molecules only** — biologics analysis is informational, not generative
- **No user authentication** — single-user deployment assumed
- **API dependency** — external APIs may have downtime; retry logic mitigates but doesn't eliminate this

---

## Built With

This project was built for the **Cognizant Technoverse Hackathon 2026** in the **Lifesciences** domain.

**Author:** Ayushmaan Singh Naruka (23CSU067)
B.Tech Artificial Intelligence & Machine Learning
The NorthCap University

**GitHub:** [@Nezeon](https://github.com/Nezeon)

---

## License

This project is open source under the [MIT License](LICENSE).

---

<div align="center">

**MolForge AI** — Accelerating the journey from disease to drug candidate.

</div>
