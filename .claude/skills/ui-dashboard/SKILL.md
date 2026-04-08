# /ui-dashboard — Frontend UI Skill

> Auto-invoked when building or modifying any React component,
> the agent activity panel, results dashboard, or molecule cards.
> Read brand tokens from CLAUDE.md before writing any CSS or Tailwind class.

---

## Brand Tokens Quick Reference

```
Dark bg:          bg-slate-950      (#020617)
Card bg:          bg-slate-900      (#0F172A)
Card hover:       bg-slate-800      (#1E293B)
Input bg:         bg-slate-800
Border:           border-slate-700
Text primary:     text-slate-50
Text secondary:   text-slate-400
Text muted:       text-slate-500
Accent teal:      text-teal-500     bg-teal-600
Accent violet:    text-violet-400   bg-violet-600
```

---

## Component Patterns

### Agent Activity Panel — WebSocket Stream

```jsx
// AgentActivityPanel.jsx
import { useEffect, useRef } from "react";

export function AgentActivityPanel({ jobId }) {
  const logRef = useRef(null);
  const [updates, setUpdates] = useState([]);

  useEffect(() => {
    if (!jobId) return;
    const ws = new WebSocket(`${import.meta.env.VITE_WS_BASE_URL}/ws/${jobId}`);

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      setUpdates(prev => [...prev, msg]);
    };

    // Auto-scroll to bottom
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }

    return () => ws.close(); // ALWAYS clean up
  }, [jobId]);

  return (
    <div
      ref={logRef}
      className="bg-slate-900 border border-slate-700 rounded-xl p-4
                 h-64 overflow-y-auto font-mono text-sm"
    >
      {updates.map((msg, i) => (
        <AgentLogLine key={i} message={msg} />
      ))}
    </div>
  );
}
```

### Score Badge — GO / INVESTIGATE / NO-GO

```jsx
const VERDICT_STYLES = {
  GO: "bg-teal-500/15 text-teal-400 border border-teal-500/30",
  INVESTIGATE: "bg-amber-500/15 text-amber-300 border border-amber-500/30",
  "NO-GO": "bg-red-500/15 text-red-400 border border-red-500/30",
};

export function ScoreBadge({ verdict }) {
  return (
    <span className={`px-3 py-1 rounded-full text-xs font-medium ${VERDICT_STYLES[verdict]}`}>
      {verdict}
    </span>
  );
}
```

### ADMET Property Row

```jsx
const ADMET_COLORS = {
  PASS: "text-teal-400",
  WARN: "text-amber-300",
  FAIL: "text-red-400",
};

export function AdmetRow({ label, value, status }) {
  return (
    <div className="flex justify-between items-center py-1 border-b border-slate-800">
      <span className="text-slate-400 text-sm">{label}</span>
      <span className={`text-sm font-medium font-mono ${ADMET_COLORS[status]}`}>
        {value}
      </span>
    </div>
  );
}
```

### Molecule Card

```jsx
export function MoleculeCard({ candidate, rank }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-slate-900 border border-slate-700 rounded-xl overflow-hidden
                    hover:border-slate-600 transition-colors duration-150">
      {/* Header — always visible */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-slate-500 text-sm font-mono">#{rank}</span>
          <span className="text-slate-50 font-medium">Candidate {rank}</span>
          <ScoreBadge verdict={candidate.verdict} />
        </div>
        <div className="flex items-center gap-4">
          <span className="text-teal-400 font-mono text-sm">
            {(candidate.composite_score * 100).toFixed(0)}%
          </span>
          <ChevronDown
            className={`text-slate-400 w-4 h-4 transition-transform ${expanded ? "rotate-180" : ""}`}
          />
        </div>
      </div>

      {/* Body — expanded only */}
      {expanded && (
        <div className="px-4 pb-4 border-t border-slate-800">
          {/* 2D molecule structure from backend SVG */}
          <img
            src={candidate.svg_url}
            alt="Molecule structure"
            className="w-full max-w-xs mx-auto my-4 invert"
          />
          {/* SMILES in monospace */}
          <p className="text-slate-500 text-xs font-mono break-all mb-4">
            {candidate.smiles}
          </p>
          {/* ADMET scores */}
          <AdmetRadar data={candidate.admet_detail} />
        </div>
      )}
    </div>
  );
}
```

---

## Anti-Patterns to Avoid

- **Never show raw SMILES as the primary output** — always show 2D structure image alongside
- **Never display all ADMET properties in a flat list** — use the radar chart for overview, list for detail
- **Never block UI while pipeline runs** — show agent activity panel, not a spinner
- **Never hardcode job IDs or disease names** — always from state/props
- **Molecule SVG from backend** — use `<img src={svg_url}>` with `className="invert"` for dark mode (RDKit renders white bg by default)
- **WebSocket cleanup** — always return `ws.close()` from useEffect, or you'll leak connections

---

## Loading States

Three states to handle for every data-fetching component:

```jsx
if (isLoading) return <PipelineRunning />;    // agent activity panel
if (error) return <ErrorCard message={error} />;
if (!data || data.length === 0) return <EmptyState />;
return <ResultsDashboard data={data} />;
```
