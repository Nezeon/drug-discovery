# /write-docs — Documentation Skill

> Auto-invoked when writing docstrings, updating the README, writing
> the demo script, or documenting an endpoint or agent.

---

## Docstring Standard (all Python functions)

```python
async def run(self, state: MolForgeState) -> MolForgeState:
    """
    Queries PubMed and Europe PMC for recent literature on the disease,
    extracts candidate protein targets using Gemini, and scores them
    by novelty (low existing drug coverage) and disease relevance.

    Writes to: state["candidate_targets"]
    Reads from: state["disease_name"]
    """
```

One line summary → blank line → what it reads/writes from state.
No novels. No "this function does X by doing Y and then Z".

---

## README Structure

The project README must contain exactly these sections in this order:

1. **One-liner** — "MolForge AI: From Disease to Drug Candidate — Autonomously"
2. **What it does** — 3 sentences max
3. **Demo** — GIF or screenshot of the running dashboard
4. **Quick Start** — copy-pasteable setup commands (backend + frontend)
5. **Architecture** — the SVG diagram from the project document
6. **Agent Overview** — one-line per agent in a table
7. **Tech Stack** — table format
8. **Hackathon** — Cognizant Technoverse 2026, team name, members

## Demo Script (for live hackathon presentation)

Structure:
1. **Hook (30s)** — "Drug discovery costs $2.6B and takes 15 years. We do it in 90 seconds."
2. **Input (10s)** — Type "Parkinson's Disease" into the input bar
3. **Pipeline live (60s)** — Walk through each agent as it lights up in the activity panel
   - Agent 1: "It's scanning 3 years of PubMed right now"
   - Agent 3: "It just pulled the 3D protein structure from AlphaFold — 200 million structures available free"
   - Agent 4: "Now generating novel molecular analogues — these are molecules that don't exist yet"
   - Agent 5: "ADMET filter — automatically eliminating anything that would be toxic or insoluble"
   - Market track: "In parallel, it's sizing the market from WHO data"
4. **Results (30s)** — Show the GO candidates, open one molecule card, show ADMET radar
5. **Market brief (20s)** — Show commercial opportunity score
6. **PDF (10s)** — Download the report
7. **Closing (20s)** — "Every molecule you just saw is novel. Every score is grounded in real data. No hallucinations."

Total: ~3 minutes

## Agent Documentation Template

When documenting any agent for judges or teammates:

```
## Agent N — [Name]

**One-line role:** [what it does in plain English]

**Input:** [what state field(s) it reads]
**Output:** [what state field it writes]

**Data sources:** [list APIs used]
**Tools:** [list libraries used]

**Key logic:** [2-3 bullet points on the most important decisions/filters]

**Why it matters:** [1 sentence on what fails if this agent is wrong]
```
