from utils.hashing import compute_hash


def collector_handle(content: str) -> tuple[str, str]:
    """
    Step 1: Collector — initial acquisition of evidence from the 'scene'.
    This is the origin point. No transformation is applied.
    Returns the content unchanged and reports success.
    """
    return content, "success"


def analyst_tool_handle(content: str) -> tuple[str, str]:
    """
    Step 2: Analyst Tool — performs read-only analysis of the evidence.
    Must NOT alter the evidence in any way. Content passes through unchanged.
    """
    return content, "success"


def export_tool_handle(content: str) -> tuple[str, str]:
    """
    Step 3: Export Tool — THE TAMPER INJECTION POINT.

    This handler silently alters the evidence content by converting Unix line
    endings (\\n) to Windows-style CRLF line endings (\\r\\n). This simulates
    what a real-world lossy export tool might do — a subtle, plausible encoding
    change that is invisible to a casual human reviewer.

    Despite this unauthorized alteration, the handler still logs status='success'
    as if everything completed normally. This is the deception the Verifier is
    designed to catch — the Verifier never trusts this self-reported status; it
    independently recomputes the hash from the actual stored content snapshot.
    """
    tampered_content = content.replace("\n", "\r\n")
    return tampered_content, "success"  # declares success despite altering content


def reviewer_handle(content: str) -> tuple[str, str]:
    """
    Step 4: Reviewer — human review of the (already silently tampered) evidence.
    The reviewer sees no obvious error on the surface; the file looks fine visually.
    Content passes through unchanged from this handler's perspective.
    """
    return content, "success"


def archive_handle(content: str) -> tuple[str, str]:
    """
    Step 5: Archive — final long-term storage of the evidence.
    No transformation applied. Stores the final (tampered) state.
    """
    return content, "success"


# Ordered pipeline: (step_order, handler_name, handler_function)
# Keep this in sync with the `handlers` table seed data.
HANDLER_PIPELINE = [
    (1, "Collector", collector_handle),
    (2, "Analyst Tool", analyst_tool_handle),
    (3, "Export Tool", export_tool_handle),
    (4, "Reviewer", reviewer_handle),
    (5, "Archive", archive_handle),
]
