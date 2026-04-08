"""
agents/biologics_analyst.py — Agent 9: Biologics Opportunity Analyst.

Assesses whether the validated target is amenable to biologic modalities
(antibodies, peptides, ADCs) in addition to small molecules. Provides
a complementary analysis to the small-molecule compound discovery track.

Runs in parallel with the science track (like market agents).
"""

from __future__ import annotations

import logging
from typing import Any

from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

# Target classes typically amenable to biologics
BIOLOGICS_TARGET_CLASSES = {
    "receptor": {"antibody": 0.9, "peptide": 0.7, "adc": 0.6},
    "kinase": {"antibody": 0.3, "peptide": 0.4, "adc": 0.5},
    "ion_channel": {"antibody": 0.2, "peptide": 0.6, "adc": 0.2},
    "gpcr": {"antibody": 0.4, "peptide": 0.8, "adc": 0.3},
    "enzyme": {"antibody": 0.3, "peptide": 0.5, "adc": 0.4},
    "transporter": {"antibody": 0.5, "peptide": 0.4, "adc": 0.3},
    "cell_surface": {"antibody": 0.95, "peptide": 0.6, "adc": 0.9},
    "secreted": {"antibody": 0.85, "peptide": 0.7, "adc": 0.3},
    "cytokine": {"antibody": 0.9, "peptide": 0.5, "adc": 0.2},
    "unknown": {"antibody": 0.4, "peptide": 0.5, "adc": 0.3},
}

BIOLOGICS_PROMPT = """
You are a biologics drug discovery expert analyzing whether a protein target
is suitable for biologic drug modalities.

TARGET: {target_name} ({uniprot_id})
PROTEIN FUNCTION: {protein_info}
DISEASE: {disease_name}
TARGET LOCALIZATION: {localization}

Assess this target for three biologic modalities:
1. Monoclonal antibody (mAb)
2. Therapeutic peptide
3. Antibody-drug conjugate (ADC)

For each, consider:
- Is the target accessible (extracellular, cell-surface, secreted)?
- Are there known epitopes or binding regions?
- What is the therapeutic hypothesis (blocking, depleting, delivering payload)?
- Are there existing biologics against this target class?

Return JSON:
{{
  "antibody_feasibility": {{"score": 0.0-1.0, "rationale": "1-2 sentences", "therapeutic_approach": "blocking|depleting|agonist"}},
  "peptide_feasibility": {{"score": 0.0-1.0, "rationale": "1-2 sentences", "therapeutic_approach": "inhibitor|mimetic|targeting"}},
  "adc_feasibility": {{"score": 0.0-1.0, "rationale": "1-2 sentences", "payload_class": "cytotoxic|targeted|immunostimulant"}},
  "recommended_modality": "antibody|peptide|adc|none",
  "overall_biologics_score": 0.0-1.0,
  "key_considerations": ["string", "string"]
}}
"""


class BiologicsAnalyst(BaseAgent):
    """
    Evaluates the validated target for biologic drug modalities.
    Provides complementary analysis to the small-molecule pipeline.
    """

    async def run(self, state: dict[str, Any]) -> dict[str, Any]:
        self.emit(state, "Biologics Analyst: Evaluating biologic modalities...")

        validated_target = state.get("validated_target", {})
        disease_name = state.get("disease_name", "")

        if not validated_target:
            self.emit(state, "Biologics Analyst: No validated target — skipping biologics analysis")
            state["biologics_data"] = self._empty_result()
            return state

        target_name = validated_target.get("name") or validated_target.get("gene_symbol", "Unknown")
        uniprot_id = validated_target.get("uniprot_id", "")

        # Determine target class and localization
        target_class, localization = await self._classify_target(validated_target)
        self.emit(state, f"Biologics Analyst: Target classified as {target_class} ({localization})")

        # Get modality scores from knowledge base
        class_scores = BIOLOGICS_TARGET_CLASSES.get(target_class, BIOLOGICS_TARGET_CLASSES["unknown"])

        # Try Gemini assessment for detailed analysis
        protein_info = validated_target.get("evidence", "")
        gemini_result = None
        try:
            prompt = BIOLOGICS_PROMPT.format(
                target_name=target_name,
                uniprot_id=uniprot_id,
                protein_info=protein_info,
                disease_name=disease_name,
                localization=localization,
            )
            gemini_result = await self._call_gemini(state, prompt)
        except Exception as e:
            logger.warning("Gemini biologics assessment failed: %s", e)

        # Build result — use Gemini if available, fall back to heuristic
        if gemini_result and isinstance(gemini_result, dict):
            biologics_data = {
                "target": target_name,
                "target_class": target_class,
                "localization": localization,
                "antibody": gemini_result.get("antibody_feasibility", {"score": class_scores["antibody"], "rationale": "Estimated from target class"}),
                "peptide": gemini_result.get("peptide_feasibility", {"score": class_scores["peptide"], "rationale": "Estimated from target class"}),
                "adc": gemini_result.get("adc_feasibility", {"score": class_scores["adc"], "rationale": "Estimated from target class"}),
                "recommended_modality": gemini_result.get("recommended_modality", self._recommend_modality(class_scores)),
                "overall_score": gemini_result.get("overall_biologics_score", max(class_scores.values())),
                "key_considerations": gemini_result.get("key_considerations", []),
            }
        else:
            # Heuristic fallback
            biologics_data = {
                "target": target_name,
                "target_class": target_class,
                "localization": localization,
                "antibody": {"score": class_scores["antibody"], "rationale": f"Estimated from {target_class} target class"},
                "peptide": {"score": class_scores["peptide"], "rationale": f"Estimated from {target_class} target class"},
                "adc": {"score": class_scores["adc"], "rationale": f"Estimated from {target_class} target class"},
                "recommended_modality": self._recommend_modality(class_scores),
                "overall_score": max(class_scores.values()),
                "key_considerations": [
                    f"Target classified as {target_class}",
                    f"Localization: {localization}",
                ],
            }

        self.emit(state, f"Biologics Analyst: Recommended modality → {biologics_data['recommended_modality']} (score: {biologics_data['overall_score']:.2f})")

        state["biologics_data"] = biologics_data
        return state

    async def _classify_target(self, target: dict) -> tuple[str, str]:
        """Classify target type and localization from available data."""
        evidence = (target.get("evidence") or "").lower()
        name = (target.get("name") or "").lower()

        # Simple keyword classification
        if any(k in evidence for k in ["receptor", "cell surface", "membrane"]):
            return ("cell_surface" if "surface" in evidence else "receptor"), "extracellular"
        if any(k in evidence for k in ["kinase", "phosphorylat"]):
            return "kinase", "intracellular"
        if any(k in evidence for k in ["channel", "ion"]):
            return "ion_channel", "transmembrane"
        if any(k in evidence for k in ["gpcr", "g-protein", "g protein"]):
            return "gpcr", "transmembrane"
        if any(k in evidence for k in ["enzyme", "protease", "catalytic"]):
            return "enzyme", "intracellular"
        if any(k in evidence for k in ["cytokine", "interleukin", "chemokine"]):
            return "cytokine", "secreted"
        if any(k in evidence for k in ["secreted", "plasma", "serum"]):
            return "secreted", "extracellular"

        return "unknown", "unknown"

    async def _call_gemini(self, state, prompt):
        """Call Gemini for biologics assessment."""
        from config import GEMINI_API_KEY
        if not GEMINI_API_KEY:
            return None

        import httpx
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
            return self.parse_gemini_json(text)

    def _recommend_modality(self, scores: dict) -> str:
        best = max(scores, key=scores.get)
        if scores[best] < 0.4:
            return "none"
        return best

    def _empty_result(self) -> dict:
        return {
            "target": "Unknown",
            "target_class": "unknown",
            "localization": "unknown",
            "antibody": {"score": 0, "rationale": "No target available"},
            "peptide": {"score": 0, "rationale": "No target available"},
            "adc": {"score": 0, "rationale": "No target available"},
            "recommended_modality": "none",
            "overall_score": 0,
            "key_considerations": [],
        }
