# /agent-engine — Agent Development Skill

> Auto-invoked when building or modifying any agent, changing agent prompts,
> or modifying the orchestrator logic.

---

## The Golden Rule of Agent Development

**Every agent has one job. It reads from state, does exactly that job, writes its output to state, and returns state. Nothing more.**

If an agent is doing two things, it should be two agents.
If an agent is reading from another agent's output field to do its own work, that's fine — that's the pipeline.
If an agent is *writing* to another agent's output field, that's a bug.

---

## Agent Output Field Ownership

| Agent | Owns This State Field | Reads These Fields |
|---|---|---|
| Disease Analyst | `candidate_targets` | `disease_name` |
| Target Validator | `validated_target` | `candidate_targets` |
| Structure Resolver | `protein_structure` | `validated_target` |
| Compound Discovery | `candidate_compounds` | `protein_structure`, `validated_target` |
| ADMET Predictor | `admet_results` | `candidate_compounds` |
| Market Analyst | `market_data` | `disease_name` |
| Competitive Scout | `competitive_data` | `disease_name`, `validated_target` |
| Opportunity Scorer | `opportunity_score` | `market_data`, `competitive_data` |
| 4D Scorer | `final_candidates` | `admet_results`, `opportunity_score`, `validated_target` |

**Violation of field ownership = bug. Always cross-check before writing.**

---

## Prompt Engineering Rules

When writing or editing any Gemini prompt for an agent:

1. **Always specify the exact output format** — JSON schema with field names and types
2. **Always say "Return ONLY valid JSON. No markdown. No explanation."** at the end
3. **Always include a fallback instruction** — "If no results found, return []" or "return null"
4. **Never ask Gemini to generate SMILES directly** — Gemini hallucinates molecules. Use RDKit/DeepChem for chemistry, Gemini for language tasks only
5. **Be specific about units** — say "IC50 in nanomolar" not just "IC50"
6. **Include a few-shot example in the prompt** for structured extraction tasks

## Gemini JSON Parsing (always use this pattern)

```python
import json
import re

def parse_gemini_json(response_text: str) -> dict | list:
    """Safe Gemini JSON parser — handles markdown fences."""
    text = response_text.strip()
    # Strip markdown code fences
    text = re.sub(r'^```(?:json)?\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    text = text.strip()
    return json.loads(text)
```

## Retry Pattern (use for every external API call)

```python
import asyncio
import httpx

async def fetch_with_retry(url: str, params: dict = None, max_retries: int = 3) -> dict:
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                return response.json()
        except (httpx.HTTPError, httpx.TimeoutException) as e:
            if attempt == max_retries - 1:
                raise
            wait = 2 ** attempt  # exponential backoff: 1s, 2s, 4s
            await asyncio.sleep(wait)
```

## Status Update Pattern (every agent must emit these)

```python
async def run(self, state: MolForgeState) -> MolForgeState:
    # Start signal
    state["status_updates"].append(
        f"🔬 Disease Analyst: scanning literature for {state['disease_name']}..."
    )

    # ... do work ...

    # Done signal — always include a count or summary
    state["status_updates"].append(
        f"✅ Disease Analyst: found {len(targets)} candidate targets"
    )
    return state
```

## How to Test an Agent in Isolation

Each agent can be tested without running the full pipeline:

```python
# test_agent_isolation.py
import asyncio
from agents.structure_resolver import StructureResolver
from orchestrator.state import MolForgeState

async def test():
    state = MolForgeState(
        disease_name="Parkinson's Disease",
        job_id="test_001",
        candidate_targets=[],
        validated_target={
            "name": "LRRK2",
            "uniprot_id": "Q5S007",
            "druggability_score": 0.87
        },
        # ... fill required fields with mock data
    )
    agent = StructureResolver()
    result = await agent.run(state)
    print(result["protein_structure"])

asyncio.run(test())
```

Always test each agent in isolation before running the full graph.

## Non-Negotiable Agent Rules

- SMILES must be validated with `Chem.MolFromSmiles()` before writing to state — null = skip
- All Gemini calls must have JSON parsing wrapped in try/except
- All external API calls must have retry logic
- Never hardcode API endpoints — use constants from `config.py`
- Agents must not crash the pipeline — catch exceptions, log to `state["errors"]`, continue
- The Novelty filter in Agent 4 is sacred: Tanimoto > 0.85 = deprioritise, never remove this check
