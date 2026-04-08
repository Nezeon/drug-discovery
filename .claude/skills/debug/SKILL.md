# /debug — Debugging Skill

> Auto-invoked when something is broken, failing, or returning unexpected output.
> Read this before touching any code.

---

## Debug Protocol (always in this order)

1. **Read the error message completely** — the answer is usually in the traceback
2. **Identify the file and line number** — open that file before doing anything else
3. **Run `gitnexus_query`** with the error symptom to find related execution flows
4. **Run `gitnexus_context`** on the suspect function to see all callers and callees
5. **Read the actual code** — never guess what it does
6. **Form a hypothesis** — state it before making any change
7. **Make the smallest possible fix** — one change, then verify

---

## Common MolForge AI Failure Patterns

### LangGraph Hangs / Never Completes
- Check if an agent is blocking on a synchronous HTTP call — all calls must be `async`
- Check if the graph was compiled: `.compile()` must be called before `.invoke()`
- Check if a node is returning `state` — every node MUST return the full state object
- Check for missing edges in `graph.py` — a node with no outgoing edge halts the graph silently

### RDKit Returns None
```python
mol = Chem.MolFromSmiles(smiles)
# If mol is None here — the SMILES is invalid
# Fix: always null-check before any RDKit operation
if mol is None:
    state["errors"].append(f"Invalid SMILES: {smiles}")
    continue
```

### DeepChem Model Fails to Load
- Models need to be pre-downloaded — run `python tools/preload_models.py` first
- Check TDC and DeepChem version compatibility — they must be pinned together
- TDC returns numpy arrays — use `.item()` before serialising to JSON

### ChEMBL Returns Empty Results
- Verify the target ChEMBL ID is correct — get it from UniProt cross-references
- Confirm `standard_type` filter is set: `IC50`, `Ki`, or `Kd` only
- Check rate limit: ChEMBL allows 5 req/s — add `asyncio.sleep(0.2)` between calls

### AlphaFold Returns 404
- Confirm UniProt accession format: `P12345` (no version suffix like `.1`)
- Some proteins have no AlphaFold prediction — fall back to RCSB PDB
- URL format: `https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}` — takes a list, use `[0]`

### Gemini Returns Malformed JSON
```python
# Always strip markdown fences before parsing
response_text = response.text
response_text = response_text.strip()
if response_text.startswith("```"):
    response_text = response_text.split("```")[1]
    if response_text.startswith("json"):
        response_text = response_text[4:]
result = json.loads(response_text.strip())
```

### WebSocket Not Streaming to Frontend
- Check CORS origins in `config.py` include `http://localhost:5173`
- Check WebSocket manager is receiving the `job_id` before pipeline starts
- Verify the frontend is connecting to `ws://` not `http://`
- Check the job_id in the WebSocket URL matches the one from POST /api/discover

### ChromaDB Empty / Not Finding Results
- Check `CHROMA_PERSIST_DIR` path in `.env` — must be absolute or relative to `backend/`
- ChromaDB collections are per-job (`{job_id}_disease_literature`) — verify prefix
- Embedding must be complete before querying — don't query mid-insertion

---

## Debugging Steps for Each Agent

| Agent | First Thing to Check |
|---|---|
| Disease Analyst | Are PubMed abstracts being fetched? Print first 3 abstracts |
| Target Validator | Is OpenTargets returning data? Log raw GraphQL response |
| Structure Resolver | Is UniProt accession correct format? Is AlphaFold returning `[0]`? |
| Compound Discovery | Are ChEMBL seeds non-empty? Print count before generation |
| ADMET Predictor | Are DeepChem models loaded? Check preload script ran |
| Market Analyst | Is WHO GHO returning data for the ICD-10 code? |
| Competitive Scout | Is ClinicalTrials.gov v2 API endpoint correct? |
| Opportunity Scorer | Are inputs from Agents 6 + 7 populated in state? |

---

## What NOT to Do When Debugging

- Don't delete and recreate the ChromaDB folder — it wipes all cached data
- Don't restart the entire backend to fix one agent — test agents in isolation first
- Don't change the state schema to fix a bug — state schema changes break everything
- Don't edit `graph.py` without running `gitnexus_impact` first
