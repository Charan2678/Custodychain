import os
import json
from typing import Dict, Any, Optional
from app.core.config import settings


def explain_verification_with_gemini(facts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesizes court-admissible forensic explanation from deterministic verification facts.
    Uses Google GenAI SDK (google-genai) with GEMINI_API_KEY from settings/env.
    Crucial Architectural Invariant: Deterministic Cryptography Decides; Gemini AI Explains.
    """
    evidence_id = facts.get("evidence_id", "")
    evidence_name = facts.get("evidence_name", "Exhibit")
    verdict = facts.get("verdict", "CHAIN_INTACT")
    first_break = facts.get("first_break")
    steps = facts.get("steps", [])
    completed_at = facts.get("completed_at", "")

    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY", "")

    # Base title and breakdown
    if verdict == "CHAIN_INTACT":
        title = "Forensic Integrity Certified: Complete Chain Intact"
        summary = (
            f"Independent verification confirmed unbroken custody integrity for '{evidence_name}'. "
            f"All {len(steps)} digital artifacts retrieved directly from physical storage matched their declared SHA-256 hashes byte-for-byte. "
            f"All custodian transitions were authenticated with valid Ed25519 digital signatures, and previous-event ledger links remained continuous."
        )
        technical_breakdown = [
            "Physical Storage Parity: 100% SHA-256 checksum match across all custody artifacts.",
            "Cryptographic Authentication: Valid Ed25519 signatures on all transition events.",
            "Ledger Linkage: Unbroken previous-event hash chain with zero omissions.",
        ]
        court_admissibility = (
            "FRE 902(14) COMPLIANT: Self-authenticating digital evidence certified intact. "
            "All physical bytes and digital records satisfy judicial standards for courtroom admissibility."
        )
    else:
        fb_step = first_break.get("step_order") if first_break else "?"
        fb_tool = first_break.get("tool_name") if first_break else "Unknown Tool"
        fb_reason = first_break.get("reason") if first_break else "MUTATION_DETECTED"
        expected_h = first_break.get("expected_value") if first_break else ""
        observed_h = first_break.get("observed_value") if first_break else ""
        downstream = first_break.get("affected_downstream_steps", [])
        downstream_str = f"Step {', Step '.join(str(s) for s in downstream)}" if downstream else "subsequent stages"

        title = f"Forensic Divergence Assessment: Compromise Localized at Step {fb_step} ({fb_tool})"
        summary = (
            f"The custody chain for '{evidence_name}' first diverged during the {fb_tool} transition (Step {fb_step}). "
            f"CustodyChain recomputed the artifact SHA-256 directly from physical storage bytes and obtained {observed_h[:16]}..., "
            f"whereas the authenticated input hash was {expected_h[:16]}.... "
            f"The handler reported 'SUCCESS', but independent verification revealed an unauthorized mutation. "
            f"All downstream handlers ({downstream_str}) operated on compromised bytes."
        )
        technical_breakdown = [
            f"Root Compromise (Step {fb_step} — {fb_tool}): Expected SHA-256: {expected_h} | Observed: {observed_h} | Fault: {fb_reason}",
            f"Downstream Contamination ({downstream_str}): Compromised bytes propagated downstream; output cannot be authenticated.",
        ]
        court_admissibility = (
            f"EVIDENTIARY WARNING: Exhibits derived after Step {fb_step} ({fb_tool}) fail integrity verification under FRE 902(14). "
            f"Preceding steps remain valid; downstream stages ({downstream_str}) must be excluded."
        )

    # Invoke Gemini AI if key is present
    gemini_narrative = None
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            prompt = f"""
You are a digital forensics expert witness testifying in a United States Federal Court regarding evidence integrity under Federal Rule of Evidence 902(14).

CRITICAL INSTRUCTIONS:
- You must NOT calculate hashes or decide guilt/authenticity. The deterministic verifier has already completed mathematical verification.
- Only explain the verified forensic facts provided below.
- Use objective, authoritative, legal forensic language.
- Do NOT invent facts or cite hypothetical tools not mentioned.

VERIFICATION FACTS:
- Exhibit Name: {evidence_name}
- Final Cryptographic Verdict: {verdict}
- First Break Details: {json.dumps(first_break, default=str)}
- Total Steps in Custody: {len(steps)}

Draft a concise 2-paragraph judicial summary:
Paragraph 1: Executive forensic explanation of what occurred and where the first break was localized.
Paragraph 2: Evidence admissibility directive under FRE 902(14).
"""
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
            )
            if response and response.text:
                gemini_narrative = response.text.strip()
                summary = gemini_narrative
        except Exception as e:
            # Safe fallback if API quota or connection issue
            pass

    return {
        "evidence_id": evidence_id,
        "verdict": verdict,
        "first_break_step": first_break.get("step_order") if first_break else None,
        "first_break_handler": first_break.get("tool_name") if first_break else None,
        "title": title,
        "summary": summary,
        "technical_breakdown": technical_breakdown,
        "court_admissibility": court_admissibility,
        "generated_at": completed_at,
        "ai_engine": f"Google Gemini ({settings.GEMINI_MODEL})" if gemini_narrative else "Deterministic Cryptographic Verifier",
        "architecture_note": "Deterministic Cryptography Decides. Gemini Explains.",
    }
