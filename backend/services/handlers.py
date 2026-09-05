from utils.hashing import compute_hash


def collector_handle(content: str, simulate_tamper: bool = False) -> tuple[str, str]:
    """
    Step 1: Collector — initial acquisition of evidence from the scene.
    Baseline origin point. Never tampered.
    """
    return content, "success"


def analyst_tool_handle(content: str, simulate_tamper: bool = False) -> tuple[str, str]:
    """
    Step 2: Analyst Tool — performs read-only analysis of the evidence.
    When simulate_tamper=True: secretly injects unauthorized metadata tag into evidence
    while still falsely reporting status='success'.
    """
    if simulate_tamper:
        tampered_content = content + "\n[METADATA_INJECTED_BY_ANALYST: UNTRACKED_TAG_88]"
        return tampered_content, "success"
    return content, "success"


def export_tool_handle(content: str, simulate_tamper: bool = False) -> tuple[str, str]:
    """
    Step 3: Export Tool — format conversion / export stage.
    When simulate_tamper=True: silently changes line-ending encoding (\n -> \r\n),
    altering the byte stream while falsely reporting status='success'.
    """
    if simulate_tamper:
        tampered_content = content.replace("\n", "\r\n")
        return tampered_content, "success"
    return content, "success"


def reviewer_handle(content: str, simulate_tamper: bool = False) -> tuple[str, str]:
    """
    Step 4: Reviewer — human verification and legal review.
    When simulate_tamper=True: reviewer silently redacts or adds unlogged notes
    while declaring status='success'.
    """
    if simulate_tamper:
        tampered_content = content + "\n[LEGAL_REDACTION_APPLIED_WITHOUT_REHASH]"
        return tampered_content, "success"
    return content, "success"


def archive_handle(content: str, simulate_tamper: bool = False) -> tuple[str, str]:
    """
    Step 5: Archive — long-term storage in forensic vault.
    When simulate_tamper=True: simulates silent storage bit-flip / storage corruption
    while declaring status='success'.
    """
    if simulate_tamper:
        tampered_content = content + "\n[BIT_ROT_ARCHIVE_STORAGE_DEGRADATION: 0x00]"
        return tampered_content, "success"
    return content, "success"


# Ordered pipeline: (step_order, handler_name, handler_function)
HANDLER_PIPELINE = [
    (1, "Collector", collector_handle),
    (2, "Analyst Tool", analyst_tool_handle),
    (3, "Export Tool", export_tool_handle),
    (4, "Reviewer", reviewer_handle),
    (5, "Archive", archive_handle),
]
