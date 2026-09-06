import io
from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from sqlalchemy.orm import Session

import models
from services.verifier_service import verify_evidence_integrity


def generate_forensic_certificate_pdf(db: Session, evidence_id: int) -> bytes:
    """
    Renders a court-admissible Digital Evidence Chain of Custody Certificate.
    Includes case exhibit details, cryptographic hash checks, handler signatures,
    and the authoritative independent verification verdict.
    """
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        raise ValueError(f"Evidence {evidence_id} not found")

    case = None
    if evidence.case_id:
        case = db.query(models.Case).filter(models.Case.id == evidence.case_id).first()

    verification = verify_evidence_integrity(db, evidence_id, auditor_name="Report Generator")

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
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        fontName="Helvetica-Bold",
        spaceAfter=6,
    )
    meta_label = ParagraphStyle(
        "MetaLabel",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        fontName="Helvetica-Bold",
        textColor=colors.HexColor("#334155"),
    )
    meta_value = ParagraphStyle(
        "MetaValue",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        fontName="Helvetica",
        textColor=colors.HexColor("#0f172a"),
    )
    table_text = ParagraphStyle(
        "TableText",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica",
    )
    table_text_bold = ParagraphStyle(
        "TableTextBold",
        parent=styles["Normal"],
        fontSize=8,
        leading=10,
        fontName="Helvetica-Bold",
    )

    elements = []

    # Title & Certification Header
    elements.append(Paragraph("EVIDENCE INTEGRITY REPORT", header_style))
    elements.append(Paragraph("Chain of Custody Verification &middot; Automated Cryptographic Attestation", sub_header))
    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=15))

    # Case & Exhibit Metadata
    case_num = case.case_number if case else "UNASSIGNED"
    case_title = case.title if case else "Independent Evidence Ingestion"
    exhibit_id = evidence.exhibit_id or f"EXHIBIT-{evidence.id}"

    meta_data = [
        [
            Paragraph("Case Number:", meta_label),
            Paragraph(case_num, meta_value),
            Paragraph("Exhibit Identifier:", meta_label),
            Paragraph(exhibit_id, meta_value),
        ],
        [
            Paragraph("Case Title:", meta_label),
            Paragraph(case_title, meta_value),
            Paragraph("Evidence Item:", meta_label),
            Paragraph(evidence.name, meta_value),
        ],
        [
            Paragraph("Date of Ingestion:", meta_label),
            Paragraph(evidence.created_at.strftime("%Y-%m-%d %H:%M:%S UTC") if evidence.created_at else "N/A", meta_value),
            Paragraph("Investigator / Custodian:", meta_label),
            Paragraph(evidence.created_by or "Forensic Examiner", meta_value),
        ],
        [
            Paragraph("Original SHA-256:", meta_label),
            Paragraph(f"<font face='Courier' size='7.5'>{evidence.original_hash}</font>", meta_value),
            Paragraph("Evidence Size:", meta_label),
            Paragraph(f"{evidence.size_bytes} bytes", meta_value),
        ],
    ]

    meta_table = Table(meta_data, colWidths=[90, 180, 110, 160])
    meta_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 15))

    # Verdict Callout Box
    is_intact = verification["final_verdict"] == "CHAIN_INTACT"
    verdict_bg = colors.HexColor("#f0fdf4") if is_intact else colors.HexColor("#fef2f2")
    verdict_border = colors.HexColor("#22c55e") if is_intact else colors.HexColor("#ef4444")
    verdict_text_color = "#15803d" if is_intact else "#b91c1c"
    verdict_label = "VERIFIED &middot; CHAIN INTACT" if is_intact else f"INTEGRITY ALERT &middot; {verification['final_verdict']}"

    verdict_html = f"""
    <font size='11' color='{verdict_text_color}'><b>AUTHORITATIVE VERIFICATION VERDICT:</b> {verdict_label}</font><br/>
    <font size='8.5' color='#334155'>Independent multi-vector verification evaluated physical artifact storage, Ed25519 digital signatures, and hash-linked sequence continuity.</font>
    """
    verdict_table = Table([[Paragraph(verdict_html, styles["Normal"])]], colWidths=[540])
    verdict_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), verdict_bg),
        ("BOX", (0, 0), (-1, -1), 1, verdict_border),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))
    elements.append(verdict_table)
    elements.append(Spacer(1, 15))

    # Detailed Custody Ledger Table
    elements.append(Paragraph("Cryptographic Custody Ledger", section_title))

    ledger_rows = [
        [
            Paragraph("Seq", table_text_bold),
            Paragraph("Handler", table_text_bold),
            Paragraph("Action", table_text_bold),
            Paragraph("Recomputed SHA-256", table_text_bold),
            Paragraph("Signature", table_text_bold),
            Paragraph("Status", table_text_bold),
        ]
    ]

    for step in verification["steps"]:
        status_color = "#16a34a" if step["verified"] else "#dc2626"
        status_badge = f"<font color='{status_color}'><b>{'VERIFIED' if step['verified'] else 'ALTERED'}</b></font>"
        sig_color = "#16a34a" if step.get("signature_valid") else "#dc2626"
        sig_badge = f"<font color='{sig_color}'>{'Valid Ed25519' if step.get('signature_valid') else 'Invalid'}</font>"

        short_hash = f"<font face='Courier' size='7'>{step['actual_hash'][:12]}...{step['actual_hash'][-6:]}</font>"

        ledger_rows.append([
            Paragraph(str(step["step_order"]), table_text),
            Paragraph(step["handler_name"], table_text),
            Paragraph(step["action"], table_text),
            Paragraph(short_hash, table_text),
            Paragraph(sig_badge, table_text),
            Paragraph(status_badge, table_text),
        ])

    ledger_table = Table(ledger_rows, colWidths=[25, 90, 115, 170, 75, 65])
    ledger_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
    ]))
    # Color header text
    for i in range(len(ledger_rows[0])):
        ledger_rows[0][i].style.textColor = colors.white

    elements.append(ledger_table)
    elements.append(Spacer(1, 20))

    # Legal Attestation & Signature Footer
    cert_text = """
    <b>FORENSIC ATTESTATION:</b> I hereby certify that the digital evidence exhibit described herein has been processed,
    cryptographically verified, and sealed in accordance with recognized computer forensic principles and chain-of-custody standards.
    The findings reported reflect independent recomputation of artifact hashes and digital signature validation.
    """
    elements.append(Paragraph(cert_text, ParagraphStyle("Attest", parent=styles["Normal"], fontSize=8, leading=11, textColor=colors.HexColor("#475569"))))
    elements.append(Spacer(1, 25))

    sig_line_data = [
        [
            Paragraph("________________________________________<br/><b>Lead Forensic Examiner</b><br/>Charan &middot; System Administrator", meta_value),
            Paragraph(f"________________________________________<br/><b>Date / Timestamp Generated</b><br/>{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}", meta_value),
        ]
    ]
    sig_table = Table(sig_line_data, colWidths=[270, 270])
    sig_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    elements.append(sig_table)

    doc.build(elements)
    buffer.seek(0)
    return buffer.getvalue()
