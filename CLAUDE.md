# CLAUDE.md — MolForge AI Development Context

> This file is the single source of truth for Claude Code when working on this project.
> Read this FIRST before making any changes to the codebase.

---

## Auto-Invoke Rules — MCP Tools & Skills

> **These are MANDATORY.** When a task matches a trigger below, invoke the corresponding
> tool/skill BEFORE writing any code or response.

### MCP Tools

**Context7 — Library Documentation (ALWAYS use)**
When writing or modifying code that uses any external library:
- **MUST** fetch current docs before writing API calls, class instantiation, or config patterns
- Critical for **LangGraph** — graph API changes between minor versions, node signatures differ
- Critical for **ChromaDB** — major breaking changes between v0.4 and v0.5
- Critical for **DeepChem** — model loading APIs change between releases
- Critical for **RDKit** — many methods have been deprecated; always verify current signatures
- Critical for **langchain-google-genai** — SDK breaking changes between 0.7.x and 0.8.x
- **Skip when:** Pure business logic, string manipulation, arithmetic, no external library API

**GitNexus — Code Intelligence**
Before editing any shared file, run `gitnexus_impact` to understand blast radius:
- **Mandatory before editing:** `graph.py`, `scorer.py`, `config.py`, `state.py`, `base_agent.py`
- These files are shared across all 8 agents — blast radius is high
- Skip for new agent files being created from scratch

### Skills — Auto-Invoke Triggers

**`/develop`** — Auto-invoke when:
- Building a new agent, adding a new API endpoint, creating a new React component
- Modifying orchestrator logic, agent handoff logic, or the scoring engine
- Any task described as "implement", "add", "create", "build", "wire up", "connect"

**`/debug`** — Auto-invoke when:
- Something is broken, failing, or returning errors
- "Agent X is not running", "LangGraph hangs", "RDKit returns None", "ChromaDB empty"
- Any error trace, stack trace, or unexpected agent output

**`/agent-engine`** — Auto-invoke when:
- Modifying any agent file (`disease_analyst.py`, `compound_discovery.py`, etc.)
- Changing agent prompts, tool calls, or output schemas
- "Agent returns wrong format", "Gemini hallucinating molecule names", "ChEMBL query returns nothing"

**`/chem-pipeline`** — Auto-invoke when:
- Working with RDKit (SMILES, scaffolds, fingerprints, descriptors, SA score)
- Working with DeepChem (ADMET models, molecular generation, TDC benchmarks)
- "RDKit invalid molecule", "DeepChem model not loading", "SMILES parsing fails"

**`/ui-dashboard`** — Auto-invoke when:
- Building or modifying any React component, the agent activity panel, results dashboard
- Reviewing UI quality, colors, spacing, animations
- "Dashboard doesn't update", "WebSocket not streaming", "molecule card looks wrong"

**`/code-review`** — Auto-invoke when:
- Reviewing recent changes, checking code quality, reviewing a PR
- "Review this", "is this correct?", "check this implementation"

**`/write-docs`** — Auto-invoke when:
- Writing docstrings, updating API reference, updating README
- "Document this agent", "write the demo script"

**`/gitnexus-impact`** — Auto-invoke BEFORE any non-trivial edit to:
- `graph.py`, `scorer.py`, `state.py`, `config.py`, `base_agent.py`
- Any file that more than one agent imports

### Skill Combinations

- **New agent:** `/develop` + context7 for `langgraph` + `/agent-engine`
- **Chemistry work:** `/chem-pipeline` + context7 for `rdkit`/`deepchem` + `/develop`
- **Bug fix:** `/debug` + `/gitnexus-debugging` to trace the call graph
- **UI work:** `/ui-dashboard` + `/develop`
- **Scoring change:** `/agent-engine` + `/gitnexus-impact` first

---

## UI Design System — MolForge AI Brand

> Always read these tokens before writing any CSS, Tailwind class, or inline style.

### Tech Stack (do not change)

- Framework: React + JavaScript/JSX (Vite) — NOT TypeScript
- Styling: Tailwind CSS v3 utility classes
- Icons: lucide-react ONLY — no emojis as icons
- HTTP: axios with base URL from `VITE_API_BASE_URL`
- Real-time: native WebSocket API
- Charts: recharts for ADMET radar + scoring bars
- Molecule viz: SVG from backend (RDKit renders to SVG/PNG)
- Notifications: react-hot-toast
- Theme: Dark mode only

### MolForge AI Brand Tokens

```
Primary teal:              #0D9488   (teal-600)
Primary teal light:        #14B8A6   (teal-500)
Accent purple:             #7C3AED   (violet-600)
Accent purple light:       #8B5CF6   (violet-500)

Bg base (darkest):         #020617   (slate-950)
Bg card:                   #0F172A   (slate-900)
Bg card hover:             #1E293B   (slate-800)
Bg input:                  #1E293B   (slate-800)
Border default:            #334155   (slate-700)
Border subtle:             #1E293B   (slate-800)

Text primary:              #F8FAFC   (slate-50)
Text secondary:            #94A3B8   (slate-400)
Text muted:                #64748B   (slate-500)

GO badge bg:               rgba(13,148,136,0.15)    — teal-600/15
GO badge text:             #2DD4BF                  — teal-400
GO badge border:           rgba(13,148,136,0.3)

INVESTIGATE badge bg:      rgba(245,158,11,0.15)    — amber-500/15
INVESTIGATE badge text:    #FCD34D                  — amber-300
INVESTIGATE badge border:  rgba(245,158,11,0.3)

NO-GO badge bg:            rgba(239,68,68,0.15)     — red-500/15
NO-GO badge text:          #F87171                  — red-400
NO-GO badge border:        rgba(239,68,68,0.3)

PASS ADMET:                #2DD4BF   teal
WARN ADMET:                #FCD34D   amber
FAIL ADMET:                #F87171   red

Agent active:              #7C3AED   violet (pulsing)
Agent done:                #0D9488   teal
Agent pending:             #334155   slate
```

### Component Rules

- Button border-radius: `rounded-lg` (8px) primary, `rounded-md` secondary
- Card border-radius: `rounded-xl` (12px)
- Font: Inter (Google Fonts in index.html)
- Body text: 14px / font-normal
- Monospace for SMILES strings, molecule IDs, accession numbers
- Agent activity log: monospace, 13px, teal text on dark bg
- Score rings: SVG `<circle>` with `stroke-dasharray`, color = score band
- Molecule cards: collapsible — header shows name + verdict, body shows SMILES viz + ADMET breakdown
- Loading state: animated agent progress with live status text from WebSocket

### Anti-Patterns — NEVER do these

- No light backgrounds anywhere
- No emojis as icons — lucide-react only
- No hardcoded hex values in JSX — use Tailwind classes or CSS variables
- No TypeScript syntax (.tsx, type annotations) — JSX project
- No lorem ipsum placeholder text
- No reinstalling Vite/Tailwind/React/npm init
- No displaying raw SMILES strings to users without 2D viz alongside
- No showing partial ADMET results — show full scorecard or nothing

---

# CLAUDE.md — MolForge AI Development Context

> This file is the single source of truth for Claude Code when working on this project.

---

## Core Principles

1. Think through the problem first, read relevant files before writing any code.
2. Before editing any shared file (`graph.py`, `scorer.py`, `state.py`, `config.py`, `base_agent.py`), run `gitnexus_impact` to understand blast radius.
3. Before any architectural change to the orchestrator or scoring system, check in and get approval.
4. Every step: give a high-level plain-English summary of what changed and why.
5. Keep every change as small as possible. One agent, one feature, one endpoint at a time.
6. Never speculate about code you haven't opened. Read the file first. Always.
7. Always use Context7 before writing any RDKit, DeepChem, LangGraph, or ChromaDB API call.
8. Agent prompt templates are sacred — never modify without explicit approval.
9. Novelty is the core promise — never let any agent output a molecule that is just a known compound from ChEMBL without generating novel analogues.
10. SMILES validity must be checked with RDKit before any molecule is passed downstream.

---

## Project Identity

- **Name:** MolForge AI
- **Tagline:** "From Disease to Drug Candidate — Autonomously"
- **Type:** End-to-end Agentic Drug Discovery Platform
- **Author:** Ayushmaan Singh Naruka (23CSU067, B.Tech AI & ML, The Northcap University)
- **GitHub:** Nezeon
- **Hackathon:** Cognizant Technoverse Hackathon 2026
- **Domain:** Lifesciences → Drug Discovery
- **Architecture:** React Frontend → FastAPI Backend → LangGraph Orchestrator → 8 Specialized Agents → 11 Free Biomedical APIs

---

## What This Project Does

MolForge AI is an end-to-end agentic drug discovery platform. A user types a disease name. The system autonomously:

1. Mines recent biomedical literature to find emerging, under-explored protein targets (Agent 1)
2. Validates those targets for druggability and disease association using structured databases (Agent 2)
3. Fetches the 3D protein structure and identifies the binding pocket (Agent 3)
4. Seeds from ChEMBL actives, extracts scaffolds, generates novel molecular analogues using RDKit enumeration + DeepChem generative models, and filters for novelty (Agent 4)
5. Predicts ADMET safety for every candidate using RDKit descriptors and DeepChem TDC models (Agent 5)
6. Simultaneously (parallel track): estimates market size, competitive landscape, and commercial opportunity (Agents 6–8)
7. Scores all candidates on a 4D system: Binding × ADMET × Literature × Market → GO/INVESTIGATE/NO-GO (Scorer)
8. Generates a React dashboard with molecule cards, ADMET radar charts, and a downloadable PDF report

The novelty guarantee: Agent 4 runs a Tanimoto similarity filter — any molecule with >0.85 similarity to existing ChEMBL/PubChem compounds is deprioritised. The output always contains molecules that do not yet exist as known drugs.

---

## Repo Structure

```
molforge-ai/
├── CLAUDE.md                              ← YOU ARE HERE
├── PRD.md
├── ARCHITECTURE.md
├── README.md
├── .env.example
├── .gitignore
│
├── .claude/
│   └── skills/
│       ├── develop/SKILL.md
│       ├── debug/SKILL.md
│       ├── agent-engine/SKILL.md
│       ├── chem-pipeline/SKILL.md
│       ├── ui-dashboard/SKILL.md
│       ├── code-review/SKILL.md
│       └── write-docs/SKILL.md
│
├── backend/
│   ├── main.py                            ← FastAPI app + all routes
│   ├── config.py                          ← Env config (python-dotenv) — SHARED
│   ├── models.py                          ← Pydantic request/response models
│   ├── requirements.txt
│   │
│   ├── orchestrator/
│   │   ├── graph.py                       ← LangGraph graph definition — SHARED, HIGH RISK
│   │   ├── state.py                       ← MolForgeState TypedDict — SHARED, HIGH RISK
│   │   └── runner.py                      ← Async graph execution + job management
│   │
│   ├── agents/
│   │   ├── base_agent.py                  ← Base class all agents inherit — SHARED
│   │   ├── disease_analyst.py             ← Agent 1
│   │   ├── target_validator.py            ← Agent 2
│   │   ├── structure_resolver.py          ← Agent 3
│   │   ├── compound_discovery.py          ← Agent 4 — most complex
│   │   ├── admet_predictor.py             ← Agent 5
│   │   ├── market_analyst.py              ← Agent 6
│   │   ├── competitive_scout.py           ← Agent 7
│   │   └── opportunity_scorer.py          ← Agent 8
│   │
│   ├── scorer/
│   │   └── scorer.py                      ← 4D composite scorer — SHARED
│   │
│   ├── tools/
│   │   ├── pubmed_client.py               ← PubMed Entrez API wrapper
│   │   ├── europepmc_client.py            ← Europe PMC REST client
│   │   ├── opentargets_client.py          ← OpenTargets GraphQL client
│   │   ├── uniprot_client.py              ← UniProt REST client
│   │   ├── alphafold_client.py            ← AlphaFold DB API client
│   │   ├── pdb_client.py                  ← RCSB PDB REST client
│   │   ├── chembl_client.py               ← ChEMBL REST API client
│   │   ├── pubchem_client.py              ← PubChem REST API client
│   │   ├── who_gho_client.py              ← WHO GHO API client
│   │   ├── clinicaltrials_client.py       ← ClinicalTrials.gov API client
│   │   └── openfda_client.py              ← OpenFDA API client
│   │
│   ├── chemistry/
│   │   ├── scaffold.py                    ← RDKit scaffold extraction + clustering
│   │   ├── generator.py                   ← R-group enumeration + BRICS + DeepChem
│   │   ├── filters.py                     ← Lipinski, novelty, SA score, validity
│   │   └── visualizer.py                  ← RDKit SMILES → SVG/PNG
│   │
│   ├── rag/
│   │   └── chroma_store.py                ← ChromaDB store for literature RAG
│   │
│   ├── report/
│   │   └── report_generator.py            ← PDF report generation
│   │
│   └── ws/
│       └── manager.py                     ← WebSocket connection manager
│
├── frontend/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx
│   │   ├── components/
│   │   │   ├── DiseaseInput.jsx           ← Disease name input + submit
│   │   │   ├── AgentActivityPanel.jsx     ← Live WebSocket agent stream
│   │   │   ├── ResultsDashboard.jsx       ← Candidate molecule results
│   │   │   ├── MoleculeCard.jsx           ← Per-candidate card (SMILES viz + scores)
│   │   │   ├── AdmetRadar.jsx             ← Recharts radar chart for ADMET
│   │   │   ├── ScoreBadge.jsx             ← GO/INVESTIGATE/NO-GO badge
│   │   │   ├── MarketBrief.jsx            ← Commercial opportunity panel
│   │   │   └── ReportDownload.jsx         ← PDF download button
│   │   └── api/
│   │       └── discover.js                ← API calls to backend
│   ├── index.html
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── package.json
│
└── docs/
    ├── ARCHITECTURE.md
    ├── API_REFERENCE.md
    └── DEMO_SCRIPT.md
```

---

## Environment Variables

```env
# backend/.env
GEMINI_API_KEY=your_gemini_api_key_here
CHROMA_PERSIST_DIR=./chroma_db
PUBMED_API_KEY=                          # Optional — increases rate limit
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
LOG_LEVEL=INFO
MAX_CANDIDATES=25                        # Max compounds from Agent 4
NOVELTY_THRESHOLD=0.85                   # Tanimoto similarity cutoff
SA_SCORE_MAX=6.0                         # Max synthetic accessibility score

# frontend/.env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000
```

---

## LangGraph State Schema (state.py — DO NOT MODIFY without approval)

```python
class MolForgeState(TypedDict):
    # Input
    disease_name: str
    job_id: str

    # Agent 1 output
    candidate_targets: List[Dict]         # [{name, gene_id, relevance_score, novelty_score, source}]

    # Agent 2 output
    validated_target: Dict                # {name, uniprot_id, druggability_score, evidence}

    # Agent 3 output
    protein_structure: Dict               # {pdb_file_path, binding_pocket_coords, plddt_score, source}

    # Agent 4 output
    candidate_compounds: List[Dict]       # [{smiles, name, source, novelty_score, sa_score, scaffold_origin}]

    # Agent 5 output
    admet_results: List[Dict]             # [{smiles, absorption, distribution, metabolism, excretion, toxicity, verdict}]

    # Agent 6 output
    market_data: Dict                     # {patient_population, market_size_usd, daly_score, orphan_flag}

    # Agent 7 output
    competitive_data: Dict                # {trial_count, approved_drug_count, density_label, white_space_flag}

    # Agent 8 output
    opportunity_score: Dict               # {score, rating, commercial_brief, key_flags}

    # Scorer output
    final_candidates: List[Dict]          # [{smiles, composite_score, binding_score, admet_score, lit_score, market_score, verdict}]

    # System
    status_updates: List[str]             # Live messages streamed to frontend via WebSocket
    errors: List[str]                     # Non-fatal errors collected during run
```

---

## Core API Contracts

### POST /api/discover
**Request:**
```json
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

### GET /api/status/{job_id}
```json
{
  "job_id": "job_a1b2c3d4",
  "status": "running",
  "current_agent": "compound_discovery",
  "progress_pct": 45,
  "updates": ["Disease Analyst: found 5 targets", "Target Validator: LRRK2 validated (0.87)"]
}
```

### GET /api/results/{job_id}
```json
{
  "job_id": "job_a1b2c3d4",
  "disease": "Parkinson's Disease",
  "validated_target": {"name": "LRRK2", "uniprot_id": "Q5S007", "druggability_score": 0.87},
  "final_candidates": [
    {
      "smiles": "CC1=CC=C(C=C1)NC2=NC=CC(=N2)N3CCN(CC3)C",
      "composite_score": 0.81,
      "binding_score": 0.85,
      "admet_score": 0.78,
      "literature_score": 0.72,
      "market_score": 0.91,
      "verdict": "GO",
      "admet_detail": {"absorption": "PASS", "herg": "PASS", "hepatotoxicity": "WARN"},
      "svg_url": "/api/molecule/svg/job_a1b2c3d4/0",
      "novelty_score": 0.94
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

### GET /api/molecule/svg/{job_id}/{candidate_index}
Returns SVG image of the 2D molecule structure (Content-Type: image/svg+xml).

### GET /api/report/{job_id}
Returns PDF binary (Content-Type: application/pdf).

### WebSocket /ws/{job_id}
Streams JSON messages:
```json
{"type": "agent_start", "agent": "compound_discovery", "message": "Seeding from ChEMBL..."}
{"type": "agent_done", "agent": "compound_discovery", "message": "Generated 18 novel candidates"}
{"type": "progress", "pct": 60}
{"type": "complete", "message": "Analysis complete. 3 GO candidates found."}
{"type": "error", "agent": "market_analyst", "message": "WHO GHO rate limit, retrying..."}
```

### GET /health
```json
{"status": "ok", "chroma": "connected", "gemini": "reachable", "rdkit": "ok"}
```

---

## Agent Prompt Templates (SACRED — never modify without approval)

### Agent 1 — Disease Analyst
```python
DISEASE_ANALYST_PROMPT = """
You are a biomedical research expert analyzing scientific literature on {disease_name}.

RECENT ABSTRACTS (last 3 years):
{abstracts}

DISGENET ASSOCIATIONS:
{disgenet_data}

TASK:
Extract all protein targets mentioned in relation to {disease_name}.
For each target return:
- gene_symbol: official HGNC gene symbol
- protein_name: full protein name
- mechanism: how this target relates to disease pathology (1 sentence)
- evidence_strength: HIGH / MEDIUM / LOW based on frequency and recency of mentions
- novelty_signal: TRUE if this target has fewer than 3 approved drugs targeting it

Return ONLY a valid JSON array. No markdown. No explanation.
Schema: [{"gene_symbol": "", "protein_name": "", "mechanism": "", "evidence_strength": "", "novelty_signal": bool}]
"""
```

### Agent 4 — Compound Discovery (novelty framing is critical)
```python
NOVELTY_ASSESSMENT_PROMPT = """
You are a medicinal chemist reviewing generated molecular analogues.

SEED SCAFFOLD: {scaffold_smiles}
GENERATED ANALOGUE: {analogue_smiles}
TANIMOTO SIMILARITY TO NEAREST KNOWN COMPOUND: {tanimoto_score}
NEAREST KNOWN COMPOUND: {nearest_compound}

Assess whether this analogue represents genuine chemical novelty.
Return JSON: {"is_novel": bool, "novelty_rationale": "1 sentence", "medicinal_chemistry_quality": "HIGH/MEDIUM/LOW"}
"""
```

### Agent 5 — ADMET Predictor
```python
ADMET_INTERPRETATION_PROMPT = """
You are a pharmacokinetics expert reviewing ADMET predictions for a drug candidate.

MOLECULE: {smiles}
COMPUTED PROPERTIES:
{admet_properties}

Interpret these results for a non-expert researcher.
Flag any showstopper properties (hERG IC50 < 1µM = immediate FAIL, Ames positive = FAIL).
Return JSON: {"overall_verdict": "PASS/WARN/FAIL", "key_flags": [], "interpretation": "2-3 sentences"}
"""
```

### Opportunity Scorer — Unmet Need Assessment
```python
UNMET_NEED_PROMPT = """
You are a pharmaceutical market analyst assessing commercial opportunity.

DISEASE: {disease_name}
CURRENT TREATMENTS: {current_treatments}
PATIENT POPULATION: {patient_population}
ACTIVE TRIALS: {trial_count}
DISEASE BURDEN (DALY): {daly_score}

Assess the unmet medical need on a scale of 0-1.
Consider: treatment gaps, side effect burden, resistant subpopulations, geographic access.
Return JSON: {"unmet_need_score": float, "rationale": "2-3 sentences", "key_opportunity": "1 sentence"}
"""
```

---

## ChromaDB Collections

| Collection | Contents | Used By |
|---|---|---|
| `disease_literature` | Abstracts from PubMed/Europe PMC for current disease | Agent 1 RAG |
| `target_evidence` | Validated target evidence dossiers | Agent 2 RAG |
| `compound_context` | Seed compound bioactivity summaries from ChEMBL | Agent 4 context |

Collections are **per-job** — prefixed with `{job_id}_`. Cleared after 24 hours to manage disk.

---

## Do / Don't

| DO | DON'T |
|---|---|
| Use Context7 before any RDKit/DeepChem/LangGraph API call | Guess method signatures — they change between versions |
| Validate every SMILES with `Chem.MolFromSmiles()` before passing downstream | Pass unvalidated SMILES to any downstream agent |
| Run novelty check (Tanimoto < 0.85) before Agent 4 output | Output a known compound as a "discovery" |
| Handle Gemini returning JSON wrapped in markdown fences | Assume Gemini always returns clean JSON |
| Add retry logic (3x, exponential backoff) for all external API calls | Fail hard on first API timeout — all APIs have occasional downtime |
| Run `gitnexus_impact` before editing `graph.py`, `scorer.py`, `state.py` | Edit orchestrator files without blast radius check |
| Use `python-dotenv` for all env vars | Hardcode API keys anywhere in source |
| Stream agent status via WebSocket as each agent starts/completes | Wait until full pipeline is done to send any feedback to frontend |
| Log every external API call with URL + response time | Make silent API calls with no logging |
| Save job results to `./backend/jobs/{job_id}.json` | Keep results only in memory |
| Render SMILES as 2D SVG via RDKit before showing to user | Display raw SMILES strings as the primary output |
| Check AlphaFold pLDDT score before using structure | Use low-confidence AlphaFold regions for docking |
| Return `{"error": "...", "detail": "...", "agent": "..."}` on failures | Return unstructured error strings |
| Pre-cache 3 demo diseases (Parkinson's, T2 Diabetes, Alzheimer's) | Demo live without a fallback |

---

## Common Pitfalls

**RDKit:**
- `Chem.MolFromSmiles()` returns `None` for invalid SMILES — always null-check before any operation
- Morgan fingerprints: use `radius=2` for drug-likeness work, `radius=3` for scaffold similarity
- SA Score is not in core RDKit — import from `rdkit.Contrib.SA_Score`
- MurckoScaffold: import from `rdkit.Chem.Scaffolds.MurckoScaffold`

**DeepChem:**
- TDC model loading requires the TDC dataset to be downloaded first on first run — add a `--preload` script
- DeepChem and RDKit share MoleculeNet datasets — version pin both together
- ADMET models from TDC return numpy arrays — always `.item()` scalar values before JSON serialisation

**LangGraph:**
- State must be a `TypedDict` — plain dicts will cause type errors in newer versions
- Parallel branches: use `START` → `[agent_a, agent_b]` syntax not chained `.add_edge()`
- Graph must be compiled with `.compile()` before `.invoke()` or `.astream()`
- Always use `async` node functions for agents that make HTTP calls

**ChEMBL:**
- ChEMBL REST API rate limit: 5 requests/second — add `asyncio.sleep(0.2)` between calls
- Activity type filter: always filter `standard_type` to `IC50`, `Ki`, or `Kd` — other types are not binding-relevant
- Molecule SMILES from ChEMBL are canonical — no need to re-canonicalize with RDKit

**AlphaFold DB:**
- URL format: `https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}`
- Returns a list — always take `[0]` for the primary prediction
- `pdbUrl` field gives the direct download URL for the structure

**P2Rank:**
- Requires Java — check `java -version` before running
- Command: `java -jar p2rank.jar predict -f input.pdb -o output_dir`
- Output: `output_dir/input.pdb_predictions.csv` — parse this for pocket coordinates

---

## Running Locally

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate          # Mac/Linux
venv\Scripts\activate             # Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
# → http://localhost:5173

# Verify backend
curl http://localhost:8000/health
# → {"status": "ok", "chroma": "connected", "gemini": "reachable", "rdkit": "ok"}

# Pre-load DeepChem TDC models (run once before first use)
cd backend
python tools/preload_models.py
```

---

## Build Order

```
Phase 1 — Foundation
  config.py → models.py → state.py → base_agent.py → ws/manager.py

Phase 2 — Chemistry Core (test in isolation first)
  tools/alphafold_client.py → tools/pdb_client.py → agents/structure_resolver.py
  tools/chembl_client.py → tools/pubchem_client.py
  chemistry/scaffold.py → chemistry/generator.py → chemistry/filters.py
  agents/compound_discovery.py
  chemistry/visualizer.py → agents/admet_predictor.py

Phase 3 — Literature + Target Layer
  tools/pubmed_client.py → tools/europepmc_client.py → rag/chroma_store.py
  agents/disease_analyst.py
  tools/opentargets_client.py → tools/uniprot_client.py
  agents/target_validator.py

Phase 4 — Market Layer (fully parallel, build any time after Phase 1)
  tools/who_gho_client.py → agents/market_analyst.py
  tools/clinicaltrials_client.py → tools/openfda_client.py → agents/competitive_scout.py
  agents/opportunity_scorer.py

Phase 5 — Orchestration
  orchestrator/graph.py → orchestrator/runner.py → main.py (routes)

Phase 6 — Frontend
  DiseaseInput.jsx → AgentActivityPanel.jsx → ScoreBadge.jsx
  AdmetRadar.jsx → MoleculeCard.jsx → MarketBrief.jsx
  ResultsDashboard.jsx → ReportDownload.jsx → App.jsx

Phase 7 — Report + Polish
  report/report_generator.py → DEMO_SCRIPT.md → README.md
```

---

## GitNexus — Code Intelligence

This project is indexed by GitNexus as **molforge-ai**.

### Always Do
- **MUST run impact analysis before editing any shared symbol.**
  `gitnexus_impact({target: "symbolName", direction: "upstream"})`
- **MUST run `gitnexus_detect_changes()` before committing.**
- **MUST warn** if impact analysis returns HIGH or CRITICAL risk.

### High-Risk Files (always run gitnexus_impact before editing)
- `graph.py` — wires all 8 agents; any change affects the entire pipeline
- `state.py` — all agents read/write this; schema changes break everything
- `scorer.py` — changes affect final output for all candidates
- `base_agent.py` — all 8 agents inherit from this
- `config.py` — all modules import from this

### Tools Quick Reference

| Tool | When | Command |
|---|---|---|
| `query` | Find code by concept | `gitnexus_query({query: "admet prediction"})` |
| `context` | 360° view of one symbol | `gitnexus_context({name: "run_agent"})` |
| `impact` | Blast radius before editing | `gitnexus_impact({target: "MolForgeState", direction: "upstream"})` |
| `detect_changes` | Pre-commit check | `gitnexus_detect_changes({scope: "staged"})` |
| `rename` | Safe rename | `gitnexus_rename({symbol_name: "old", new_name: "new", dry_run: true})` |

### Keeping Index Fresh
```bash
npx gitnexus analyze
# or with embeddings:
npx gitnexus analyze --embeddings
```

---

*MolForge AI — Cognizant Technoverse Hackathon 2026*
*Author: Ayushmaan Singh Naruka (Nezeon)*
