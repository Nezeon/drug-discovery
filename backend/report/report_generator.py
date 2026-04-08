"""
report/report_generator.py — PDF report generator for MolForge AI.

Generates a downloadable PDF report for a completed drug discovery job.
Uses ReportLab for PDF generation.

Sections:
  Page 1 — Title Page
  Page 2 — Target Profile
  Page 3-N — Candidate Molecule Cards (GO/INVESTIGATE only)
  Last Page — Market Brief

Saved to: backend/jobs/{job_id}/report.pdf
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    HRFlowable,
)

logger = logging.getLogger(__name__)

JOBS_DIR = Path(__file__).parent.parent / "jobs"

# --- Brand Colors ---
TEAL = colors.HexColor("#0D9488")
TEAL_LIGHT = colors.HexColor("#14B8A6")
VIOLET = colors.HexColor("#7C3AED")
SLATE_950 = colors.HexColor("#020617")
SLATE_900 = colors.HexColor("#0F172A")
SLATE_800 = colors.HexColor("#1E293B")
SLATE_700 = colors.HexColor("#334155")
SLATE_400 = colors.HexColor("#94A3B8")
SLATE_50 = colors.HexColor("#F8FAFC")
WHITE = colors.white
RED_400 = colors.HexColor("#F87171")
AMBER_300 = colors.HexColor("#FCD34D")
TEAL_400 = colors.HexColor("#2DD4BF")

# --- Verdict colors ---
VERDICT_COLORS = {
    "GO": TEAL,
    "INVESTIGATE": colors.HexColor("#F59E0B"),
    "NO-GO": colors.HexColor("#EF4444"),
}


def _build_styles() -> dict[str, ParagraphStyle]:
    """Create custom paragraph styles for the report."""
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "MFTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=28,
            textColor=TEAL,
            spaceAfter=6 * mm,
        ),
        "subtitle": ParagraphStyle(
            "MFSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=14,
            textColor=SLATE_400,
            spaceAfter=4 * mm,
        ),
        "heading": ParagraphStyle(
            "MFHeading",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            textColor=TEAL,
            spaceAfter=4 * mm,
            spaceBefore=6 * mm,
        ),
        "heading2": ParagraphStyle(
            "MFHeading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            textColor=VIOLET,
            spaceAfter=3 * mm,
            spaceBefore=4 * mm,
        ),
        "body": ParagraphStyle(
            "MFBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            textColor=SLATE_950,
            spaceAfter=2 * mm,
            leading=14,
        ),
        "mono": ParagraphStyle(
            "MFMono",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=9,
            textColor=SLATE_700,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "MFSmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            textColor=SLATE_400,
        ),
        "verdict_go": ParagraphStyle(
            "VerdictGO",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=TEAL,
        ),
        "verdict_inv": ParagraphStyle(
            "VerdictINV",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#F59E0B"),
        ),
        "verdict_nogo": ParagraphStyle(
            "VerdictNOGO",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=colors.HexColor("#EF4444"),
        ),
    }


def _score_table(candidate: dict, styles: dict) -> Table:
    """Build a score breakdown table for a candidate."""
    data = [
        ["Dimension", "Score", "Weight", "Weighted"],
        [
            "Binding",
            f"{candidate.get('binding_score', 0):.2f}",
            "0.30",
            f"{candidate.get('binding_score', 0) * 0.30:.3f}",
        ],
        [
            "ADMET",
            f"{candidate.get('admet_score', 0):.2f}",
            "0.30",
            f"{candidate.get('admet_score', 0) * 0.30:.3f}",
        ],
        [
            "Literature",
            f"{candidate.get('literature_score', 0):.2f}",
            "0.15",
            f"{candidate.get('literature_score', 0) * 0.15:.3f}",
        ],
        [
            "Market",
            f"{candidate.get('market_score', 0):.2f}",
            "0.25",
            f"{candidate.get('market_score', 0) * 0.25:.3f}",
        ],
        [
            "COMPOSITE",
            f"{candidate.get('composite_score', 0):.4f}",
            "1.00",
            f"{candidate.get('composite_score', 0):.4f}",
        ],
    ]

    table = Table(data, colWidths=[3 * cm, 2.5 * cm, 2 * cm, 2.5 * cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), TEAL),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, SLATE_700),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


def generate_report(job_id: str, state: dict[str, Any]) -> str:
    """
    Generate a PDF report for a completed discovery job.

    Args:
        job_id: The job identifier.
        state:  The final MolForgeState dict.

    Returns:
        Path to the generated PDF file.
    """
    styles = _build_styles()

    # Ensure job directory exists
    job_dir = JOBS_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = job_dir / "report.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
    )

    elements: list = []

    # Extract data from state
    disease = state.get("disease_name", "Unknown Disease")
    target = state.get("validated_target", {})
    candidates = state.get("final_candidates", [])
    market = state.get("market_data", {})
    competitive = state.get("competitive_data", {})
    opportunity = state.get("opportunity_score", {})

    go_candidates = [c for c in candidates if c.get("verdict") in ("GO", "INVESTIGATE")]
    go_count = sum(1 for c in candidates if c.get("verdict") == "GO")

    # ==================================================================
    # PAGE 1 — Title Page
    # ==================================================================
    elements.append(Spacer(1, 3 * cm))
    elements.append(Paragraph("MolForge AI", styles["title"]))
    elements.append(Paragraph("Drug Discovery Report", styles["subtitle"]))
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="80%", thickness=2, color=TEAL))
    elements.append(Spacer(1, 1 * cm))

    # Disease + metadata
    meta_data = [
        ["Disease:", disease],
        ["Date:", datetime.now().strftime("%Y-%m-%d %H:%M UTC")],
        ["Job ID:", job_id],
        ["Target:", f"{target.get('gene_symbol') or target.get('name', 'N/A')} "
                    f"(druggability: {target.get('druggability_score', 'N/A')})"],
        ["Candidates Analysed:", str(len(candidates))],
        ["GO Verdicts:", str(go_count)],
    ]

    meta_table = Table(meta_data, colWidths=[5 * cm, 10 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
        ("TEXTCOLOR", (0, 0), (0, -1), TEAL),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(meta_table)

    elements.append(Spacer(1, 2 * cm))
    elements.append(Paragraph(
        "Generated by MolForge AI — From Disease to Drug Candidate, Autonomously",
        styles["small"],
    ))
    elements.append(Paragraph(
        "Author: Ayushmaan Singh Naruka | Cognizant Technoverse Hackathon 2026",
        styles["small"],
    ))

    elements.append(PageBreak())

    # ==================================================================
    # PAGE 2 — Target Profile
    # ==================================================================
    elements.append(Paragraph("Validated Target Profile", styles["heading"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    elements.append(Spacer(1, 4 * mm))

    target_name = target.get("gene_symbol") or target.get("name", "N/A")
    uniprot = target.get("uniprot_id", "N/A")
    druggability = target.get("druggability_score", "N/A")
    evidence = target.get("evidence_summary") or target.get("function_description", "N/A")

    target_data = [
        ["Target Name:", target_name],
        ["UniProt ID:", uniprot],
        ["Protein Name:", target.get("protein_name", "N/A")],
        ["Druggability Score:", f"{druggability}" if isinstance(druggability, (int, float)) else str(druggability)],
        ["OpenTargets Score:", str(target.get("opentargets_score", "N/A"))],
        ["Binding Site:", "Yes" if target.get("has_binding_site") else "No / Unknown"],
        ["Hub Protein:", "Yes" if target.get("is_hub_protein") else "No"],
    ]

    target_table = Table(target_data, colWidths=[4.5 * cm, 11 * cm])
    target_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (0, -1), VIOLET),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    elements.append(target_table)

    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("Evidence Summary", styles["heading2"]))
    # Safely handle evidence text
    safe_evidence = str(evidence).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    elements.append(Paragraph(safe_evidence, styles["body"]))

    # Data sources
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph("Data Sources", styles["heading2"]))
    sources = ["OpenTargets", "UniProt", "STRING", "Human Protein Atlas"]
    if target.get("source"):
        sources.append(target["source"])
    elements.append(Paragraph(", ".join(sources), styles["body"]))

    elements.append(PageBreak())

    # ==================================================================
    # PAGES 3-N — Candidate Molecule Cards
    # ==================================================================
    elements.append(Paragraph("Candidate Molecules", styles["heading"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    elements.append(Spacer(1, 4 * mm))

    if not go_candidates:
        elements.append(Paragraph(
            "No GO or INVESTIGATE candidates were found in this analysis.",
            styles["body"],
        ))
    else:
        for rank, cand in enumerate(go_candidates, 1):
            verdict = cand.get("verdict", "INVESTIGATE")
            verdict_style = {
                "GO": styles["verdict_go"],
                "INVESTIGATE": styles["verdict_inv"],
                "NO-GO": styles["verdict_nogo"],
            }.get(verdict, styles["body"])

            # Candidate header
            elements.append(Paragraph(
                f"Rank #{rank} &mdash; {verdict}",
                verdict_style,
            ))
            elements.append(Paragraph(
                f"Composite Score: {cand.get('composite_score', 0):.4f}",
                styles["body"],
            ))

            # Score breakdown table
            elements.append(_score_table(cand, styles))
            elements.append(Spacer(1, 3 * mm))

            # ADMET flags
            flags = cand.get("flags", [])
            if flags:
                safe_flags = ", ".join(str(f).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;") for f in flags)
                elements.append(Paragraph(f"ADMET Flags: {safe_flags}", styles["body"]))

            # Molecular properties
            props_data = [
                ["MW", "LogP", "TPSA", "SA Score", "Novelty"],
                [
                    str(cand.get("mw", "N/A")),
                    str(cand.get("logp", "N/A")),
                    str(cand.get("tpsa", "N/A")),
                    str(cand.get("sa_score", "N/A")),
                    f"{cand.get('novelty_score', 0):.2f}" if cand.get("novelty_score") else "N/A",
                ],
            ]
            props_table = Table(props_data, colWidths=[3 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
            props_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), SLATE_800),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, SLATE_700),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]))
            elements.append(props_table)
            elements.append(Spacer(1, 2 * mm))

            # SMILES
            smiles = cand.get("smiles", "N/A")
            safe_smiles = smiles.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            elements.append(Paragraph(f"SMILES: {safe_smiles}", styles["mono"]))

            # Note about visualization
            elements.append(Paragraph(
                "Note: 2D structure rendering available in web dashboard",
                styles["small"],
            ))

            elements.append(Spacer(1, 4 * mm))
            elements.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_700))
            elements.append(Spacer(1, 4 * mm))

            # Page break every 2 candidates
            if rank % 2 == 0 and rank < len(go_candidates):
                elements.append(PageBreak())

    elements.append(PageBreak())

    # ==================================================================
    # LAST PAGE — Market Brief
    # ==================================================================
    elements.append(Paragraph("Market Analysis", styles["heading"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    elements.append(Spacer(1, 4 * mm))

    # Opportunity rating
    rating = opportunity.get("rating", "N/A")
    opp_score = opportunity.get("score", 0)
    elements.append(Paragraph(
        f"Opportunity Rating: {rating} ({opp_score:.2f})",
        styles["heading2"],
    ))

    # Market overview table
    market_data = [
        ["Metric", "Value"],
        ["Patient Population", str(market.get("patient_population", "N/A"))],
        ["Market Size Estimate", str(market.get("market_size_usd_estimate", "N/A"))],
        ["DALYs (Global)", f"{market.get('daly_total', 0):,}"],
        ["Orphan Drug Eligible", "Yes" if market.get("orphan_flag") else "No"],
        ["Competitive Density", str(competitive.get("density_label", "N/A"))],
        ["Active Trials", str(competitive.get("active_trials", 0))],
        ["Approved Drugs", str(competitive.get("approved_drug_count", 0))],
        ["Curative Treatments Exist", "Yes" if competitive.get("existing_drugs_are_curative") else "No"],
    ]

    market_table = Table(market_data, colWidths=[5.5 * cm, 10 * cm])
    market_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), VIOLET),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("GRID", (0, 0), (-1, -1), 0.5, SLATE_700),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(market_table)
    elements.append(Spacer(1, 6 * mm))

    # Commercial brief
    brief = opportunity.get("commercial_brief", "")
    if brief:
        elements.append(Paragraph("Commercial Brief", styles["heading2"]))
        safe_brief = brief.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        elements.append(Paragraph(safe_brief, styles["body"]))

    # Key flags
    flags = opportunity.get("key_flags", [])
    if flags:
        elements.append(Spacer(1, 4 * mm))
        elements.append(Paragraph("Key Opportunity Flags", styles["heading2"]))
        for flag in flags:
            safe_flag = str(flag).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            elements.append(Paragraph(f"&bull; {safe_flag}", styles["body"]))

    # Data sources
    elements.append(Spacer(1, 6 * mm))
    elements.append(Paragraph("Data Sources", styles["heading2"]))
    all_sources = set()
    all_sources.update(market.get("data_sources", []))
    all_sources.add("ClinicalTrials.gov")
    all_sources.add("OpenFDA")
    if competitive.get("top_sponsors"):
        all_sources.add("ClinicalTrials.gov (sponsor data)")
    elements.append(Paragraph(", ".join(sorted(all_sources)), styles["body"]))

    # Footer
    elements.append(Spacer(1, 1 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=TEAL))
    elements.append(Spacer(1, 4 * mm))
    elements.append(Paragraph(
        "MolForge AI -- Cognizant Technoverse Hackathon 2026 -- Ayushmaan Singh Naruka",
        styles["small"],
    ))

    # Build PDF
    doc.build(elements)
    logger.info("Report generated: %s", pdf_path)

    return str(pdf_path)


async def run_report_generator(state: dict[str, Any]) -> dict[str, Any]:
    """
    LangGraph node function — generates the PDF report.
    Called after the scorer has ranked all candidates.
    """
    job_id = state.get("job_id", "unknown")
    state["status_updates"].append("Report Generator: generating PDF report...")

    try:
        report_path = generate_report(job_id, state)
        state["report_path"] = report_path
        state["status_updates"].append(f"Report Generator: done — saved to {report_path}")
    except Exception as exc:
        logger.error("Report generation failed for job %s: %s", job_id, exc)
        state["errors"].append(f"Report Generator: {exc}")
        state["status_updates"].append("Report Generator: failed — PDF could not be generated")

    return state
