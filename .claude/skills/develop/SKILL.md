# /develop — Feature Development Skill

> Auto-invoked when building new features, agents, endpoints, or components.
> Read this before writing any code.

---

## Pre-Flight Checklist (run in order)

1. **Read CLAUDE.md** if not already read this session
2. **Context7** — fetch docs for every external library you will touch
3. **GitNexus impact** — if editing a shared file (`graph.py`, `state.py`, `scorer.py`, `base_agent.py`, `config.py`), run `gitnexus_impact` first
4. **Read the target file(s)** before editing — never speculate about existing code

---

## New Agent Checklist

When building any of the 8 agents:

```python
# Every agent must follow this structure
class AgentName(BaseAgent):
    async def run(self, state: MolForgeState) -> MolForgeState:
        # 1. Emit agent_start status update
        state["status_updates"].append("AgentName: starting...")

        # 2. Do the work (API calls, computation)
        # 3. Validate outputs before writing to state
        # 4. Emit agent_done status update
        state["status_updates"].append("AgentName: done — <summary>")

        return state
```

Rules:

- All agents are `async` — every HTTP call must use `httpx.AsyncClient`, not `requests`
- All agents inherit from `BaseAgent` — never build standalone functions
- All agents write ONLY to their designated state fields — never touch another agent's fields
- All external API calls must have try/except with retry logic (3 attempts, exponential backoff)
- SMILES strings must be validated with `Chem.MolFromSmiles()` before passing downstream — null check always

## New API Endpoint Checklist

```python
# Every endpoint must follow this pattern
@router.post("/api/endpoint")
async def endpoint_name(request: RequestModel) -> ResponseModel:
    # 1. Validate input with Pydantic model
    # 2. Do work
    # 3. Return typed response
    # 4. Handle errors with HTTPException + structured detail
```

Rules:

- All request/response shapes must have a Pydantic model in `models.py`
- All errors return `{"error": "...", "detail": "...", "agent": "..."}` — never raw strings
- New endpoints must be added to `API_REFERENCE` section in CLAUDE.md

## New React Component Checklist

- Use only Tailwind utility classes — no inline styles, no hardcoded hex
- Use only lucide-react for icons — no emojis
- Use brand tokens from CLAUDE.md — slate-950 bg, teal-500 accent, violet-500 secondary
- Every component that fetches data must handle: loading state, error state, empty state
- WebSocket components: always clean up connection in `useEffect` return function

## What "Done" Means

A feature is done when:

- [ ] It works end-to-end (not just isolated)
- [ ] Errors are handled and return structured responses
- [ ] No hardcoded values — everything from config or env
- [ ] The state schema in `state.py` matches what the agent actually writes
- [ ] Frontend displays the output correctly (even if unstyled)
