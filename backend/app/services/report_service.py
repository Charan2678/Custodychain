import io
import uuid
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from sqlalchemy.orm import Session

from app.models.evidence import Evidence
from app.models.case import Case
from app.models.custody_event import CustodyEvent
from app.models.artifact import Artifact
from app.models.tool import Tool
from app.models.verification_run import VerificationRun
from app.services.verifier_service import run_independent_verification


def generate_forensic_certificate_pdf(db: Session, evidence_id: uuid.UUID, system_user_id: uuid.UUID) -> bytes:
    """
    Renders a court-admissible Digital Evidence Chain of Custody Certificate.
    Includes case exhibit details, cryptographic hash checks, tool & actor signatures,
    and authoritative first-break detection outcome.
    """
    evidence = db.query(Evidence).filter(Evidence.id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence {evidence_id} not found")

    case = db.query(Case).filter(Case.id == evidence.case_id).first()
    latest_run = (db.query(VerificationRun)
                  .filter(VerificationRun.evidence_id == evidence_id, VerificationRun.status == "COMPLETED")
                  .order_by(VerificationRun.completed_at.desc(), VerificationRun.id.desc())
                  .first())
    if latest_run and latest_run.metadata_json:
        verification = latest_run.metadata_json
    else:
        verification = run_independent_verification(db, evidence_id, requested_by_user_id=system_user_id)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
    )

    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        "CertHeader",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
    )
    sub_header = ParagraphStyle(
        "CertSubHeader",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#475569"),
        fontName="Helvetica",
    )
    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
        spaceAfter=4,
    )
    meta_label = ParagraphStyle("MetaLabel", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#64748b"), fontName="Helvetica-Bold")
    meta_val = ParagraphStyle("MetaVal", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor("#0f172a"), fontName="Helvetica")
    code_style = ParagraphStyle("CodeStyle", parent=styles["Normal"], fontSize=7, leading=9, fontName="Courier", textColor=colors.HexColor("#334155"))

    elements = []

    # Title Banner
    elements.append(Paragraph("COURT-ADMISSIBLE FORENSIC VERIFICATION CERTIFICATE", header_style))
    elements.append(Paragraph("CustodyChain Cryptographic Chain-of-Custody Authority", sub_header))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3b82f6"), spaceAfter=12))

    # Case & Exhibit Metadata Table
    case_meta = [
        [
            Paragraph("CASE NUMBER:", meta_label), Paragraph(case.case_number if case else "N/A", meta_val),
            Paragraph("EXHIBIT ID:", meta_label), Paragraph(evidence.evidence_number, meta_val),
        ],
        [
            Paragraph("CASE TITLE:", meta_label), Paragraph(case.title if case else "N/A", meta_val),
            Paragraph("EVIDENCE NAME:", meta_label), Paragraph(evidence.name, meta_val),
        ],
        [
            Paragraph("VERIFICATION ID:", meta_label), Paragraph(verification["verification_id"][:18] + "...", code_style),
            Paragraph("GENERATED AT:", meta_label), Paragraph(datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"), meta_val),
        ],
    ]
    t_meta = Table(case_meta, colWidths=[90, 180, 90, 180])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 14))

    # Verdict Box
    is_intact = verification["verdict"] == "CHAIN_INTACT"
    verdict_color = colors.HexColor("#166534") if is_intact else colors.HexColor("#991b1b")
    verdict_bg = colors.HexColor("#f0fdf4") if is_intact else colors.HexColor("#fef2f2")
    verdict_border = colors.HexColor("#22c55e") if is_intact else colors.HexColor("#ef4444")

    verdict_text = "VERIFIED INTACT & LAWFULLY UNCOMPROMISED" if is_intact else "FORENSIC INTEGRITY DIVERGENCE DETECTED"
    sub_verdict = (
        "All cryptographic vectors verified: Ed25519 signatures, ledger hashes, storage bits, and non-mutation."
        if is_intact
        else f"🚨 FIRST BREAK LOCATED AT STEP {verification['first_break']['sequence_number']} ({verification['first_break']['tool_name']}): {verification['first_break']['reason']}"
    )

    verdict_data = [
        [Paragraph(f"<b>FINAL VERDICT: {verdict_text}</b>", ParagraphStyle("V", parent=styles["Heading2"], fontSize=12, leading=16, textColor=verdict_color, alignment=TA_CENTER))],
        [Paragraph(sub_verdict, ParagraphStyle("SubV", parent=styles["Normal"], fontSize=8, leading=11, textColor=verdict_color, alignment=TA_CENTER))],
    ]
    t_verdict = Table(verdict_data, colWidths=[540])
    t_verdict.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), verdict_bg),
        ("BOX", (0, 0), (-1, -1), 1.5, verdict_border),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(t_verdict)
    elements.append(Spacer(1, 14))

    # Custody Timeline Table
    elements.append(Paragraph("Cryptographic Custody Timeline & Provenance Audit", section_title))

    headers = [
        Paragraph("<b>Step</b>", meta_label),
        Paragraph("<b>Tool / Operation</b>", meta_label),
        Paragraph("<b>Declared SHA-256</b>", meta_label),
        Paragraph("<b>Status</b>", meta_label),
    ]
    rows = [headers]

    for s in verification["steps"]:
        color = "#166534" if s["status"] == "VERIFIED" else ("#991b1b" if s["status"] == "BROKEN" else "#b45309")
        rows.append([
            Paragraph(str(s["sequence_number"]), meta_val),
            Paragraph(f"{s['tool_name'] or 'N/A'}<br/><i>{s['operation']}</i>", meta_val),
            Paragraph((s.get("declared_sha256")[:24] + "...") if s.get("declared_sha256") else "N/A", code_style),
            Paragraph(f"<b>{s['status']}</b>", ParagraphStyle("St", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.HexColor(color))),
        ])

    t_timeline = Table(rows, colWidths=[36, 180, 224, 100])
    t_timeline.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t_timeline)

    doc.build(elements)
    return buffer.getvalue()
