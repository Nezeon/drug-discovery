"""
agents/structure_resolver.py — Agent 3: Structure Resolver

OWNS:       state["protein_structure"]
READS:      state["validated_target"] (needs uniprot_id)
WRITES:     state["protein_structure"] — {pdb_file_path, source, plddt_avg, confidence_note, uniprot_id}

LOGIC:
  1. Try AlphaFold DB first using uniprot_id
  2. Fallback: if AlphaFold fails, try RCSB PDB
  3. Download PDB file and save to backend/jobs/{job_id}/target.pdb
  4. Parse with BioPython to verify it loaded correctly
  5. Extract pLDDT from B-factor column (AlphaFold) or note resolution (PDB)
  6. If AlphaFold pLDDT < 70 on majority of residues, add warning flag
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

from agents.base_agent import BaseAgent
from orchestrator.state import MolForgeState
from tools import alphafold_client, pdb_client

logger = logging.getLogger(__name__)

# Jobs directory for saving PDB files
JOBS_DIR = Path(__file__).parent.parent / "jobs"


def _compute_plddt_from_bfactors(pdb_text: str) -> float | None:
    """
    Parse PDB text and compute average pLDDT from B-factor column.
    AlphaFold stores per-residue pLDDT in the B-factor field of ATOM records.
    Returns average pLDDT or None if parsing fails.
    """
    try:
        import io
        from Bio.PDB import PDBParser

        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("target", io.StringIO(pdb_text))

        bfactors = []
        seen_residues = set()
        for model in structure:
            for chain in model:
                for residue in chain:
                    res_id = (chain.id, residue.get_id())
                    if res_id in seen_residues:
                        continue
                    seen_residues.add(res_id)
                    # Take B-factor from the CA atom (alpha carbon)
                    if "CA" in residue:
                        bfactors.append(residue["CA"].get_bfactor())

        if not bfactors:
            return None

        return sum(bfactors) / len(bfactors)
    except Exception as exc:
        logger.warning("Failed to parse B-factors from PDB: %s", exc)
        return None


def _verify_pdb_loads(pdb_text: str) -> bool:
    """Verify the PDB file can be parsed by BioPython."""
    try:
        import io
        from Bio.PDB import PDBParser

        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("verify", io.StringIO(pdb_text))
        # Check we have at least one model with atoms
        atom_count = sum(1 for _ in structure.get_atoms())
        return atom_count > 0
    except Exception as exc:
        logger.warning("PDB verification failed: %s", exc)
        return False


class StructureResolver(BaseAgent):
    name = "structure_resolver"

    async def run(self, state: MolForgeState) -> MolForgeState:
        self.emit(state, "Structure Resolver: starting — fetching protein structure...")

        target = state.get("validated_target", {})
        uniprot_id = target.get("uniprot_id")
        job_id = state["job_id"]

        if not uniprot_id:
            msg = "Structure Resolver: ERROR — no uniprot_id in validated_target"
            state["errors"].append(msg)
            self.emit(state, msg)
            return state

        # Ensure job directory exists
        job_dir = JOBS_DIR / job_id
        os.makedirs(job_dir, exist_ok=True)
        pdb_path = job_dir / "target.pdb"

        pdb_text = None
        source = None
        plddt_avg = None
        confidence_note = "ok"

        # --- Primary: AlphaFold DB ---
        self.emit(state, f"Structure Resolver: trying AlphaFold DB for {uniprot_id}...")
        af_result = await alphafold_client.fetch_structure(uniprot_id)

        if af_result and af_result.get("pdb_url"):
            pdb_text = await alphafold_client.download_pdb(af_result["pdb_url"])
            if pdb_text and _verify_pdb_loads(pdb_text):
                source = "alphafold_db"
                # Compute pLDDT from B-factors
                plddt_avg = _compute_plddt_from_bfactors(pdb_text)
                # Fallback to API-reported value
                if plddt_avg is None:
                    plddt_avg = af_result.get("plddt_avg")

                if plddt_avg is not None:
                    self.emit(state, f"Structure Resolver: AlphaFold pLDDT = {plddt_avg:.1f}")
                    if plddt_avg < 70:
                        confidence_note = (
                            f"WARNING: average pLDDT = {plddt_avg:.1f} (< 70). "
                            "Binding site may be disordered — interpret docking with caution."
                        )
                else:
                    confidence_note = "pLDDT could not be determined"
                    self.emit(state, "Structure Resolver: pLDDT could not be computed, proceeding with structure")
            else:
                logger.warning("AlphaFold PDB download/verification failed for %s", uniprot_id)
                pdb_text = None

        # --- Fallback: RCSB PDB ---
        if pdb_text is None:
            self.emit(state, f"Structure Resolver: AlphaFold unavailable, trying RCSB PDB for {uniprot_id}...")
            pdb_result = await pdb_client.fetch_structure(uniprot_id)

            if pdb_result and pdb_result.get("pdb_id"):
                pdb_text = await pdb_client.download_pdb(pdb_result["pdb_id"])
                if pdb_text and _verify_pdb_loads(pdb_text):
                    source = "rcsb_pdb"
                    resolution = pdb_result.get("resolution")
                    confidence_note = (
                        f"Experimental structure {pdb_result['pdb_id']} "
                        f"(resolution: {resolution:.2f}A)" if resolution else
                        f"Experimental structure {pdb_result['pdb_id']}"
                    )
                    self.emit(state, f"Structure Resolver: PDB {pdb_result['pdb_id']} fetched ({confidence_note})")
                else:
                    pdb_text = None

        # --- No structure found ---
        if pdb_text is None:
            msg = f"Structure Resolver: ERROR — no structure found for {uniprot_id} from any source"
            state["errors"].append(msg)
            self.emit(state, msg)
            return state

        # --- Save PDB to disk ---
        pdb_path.write_text(pdb_text, encoding="utf-8")
        logger.info("Saved PDB to %s (%d bytes)", pdb_path, len(pdb_text))

        # --- Write to state ---
        state["protein_structure"] = {
            "pdb_file_path": str(pdb_path),
            "source": source,
            "plddt_avg": round(plddt_avg, 2) if plddt_avg is not None else None,
            "confidence_note": confidence_note,
            "uniprot_id": uniprot_id,
        }

        self.emit(
            state,
            f"Structure Resolver: done — {source} structure saved "
            f"(pLDDT={plddt_avg:.1f})" if plddt_avg else
            f"Structure Resolver: done — {source} structure saved"
        )
        return state
