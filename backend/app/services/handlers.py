from typing import Tuple, Callable, List

# Handler signature: (input_bytes: bytes, simulate_tamper: bool) -> (output_bytes: bytes, declared_status: str)


def collector_handler(data: bytes, simulate_tamper: bool = False) -> Tuple[bytes, str]:
    """
    Step 1: Evidence Collector Tool.
    Initial forensic intake and raw bitstream extraction.
    Non-mutating: preserves original raw evidence exactly.
    """
    return data, "SUCCESS"


def normalizer_handler(data: bytes, simulate_tamper: bool = False) -> Tuple[bytes, str]:
    """
    Step 2: Forensic Normalizer Tool.
    Validates formatting and prepares normalized evidence stream.
    Non-mutating in standard intake.
    """
    return data, "SUCCESS"


def exporter_handler(data: bytes, simulate_tamper: bool = False) -> Tuple[bytes, str]:
    """
    Step 3: Evidence Exporter Tool.
    Generates packaged court-admissible forensic export container.
    CONTRACT: Must preserve raw artifact integrity.
    
    If simulate_tamper=True:
    Silently alters artifact bytes (e.g. injects altered record)
    YET claims declared_status = "SUCCESS"!
    This models a rogue insider or compromised export pipeline.
    """
    if simulate_tamper:
        # Silently corrupt bytes by appending or replacing content
        corrupted = data + b"\n[UNAUTHORIZED_MODIFICATION: EXPORT_TOOL_SILENT_TAMPER]"
        return corrupted, "SUCCESS"
    return data, "SUCCESS"


def archiver_handler(data: bytes, simulate_tamper: bool = False) -> Tuple[bytes, str]:
    """
    Step 4: Long-Term Forensic Vault Archiver.
    Seals artifact with cryptographic preservation timestamp.
    Non-mutating.
    """
    return data, "SUCCESS"


HANDLER_PIPELINE: List[Tuple[int, str, str, str, Callable[[bytes, bool], Tuple[bytes, str]]]] = [
    # (step_number, tool_name, tool_version, tool_type, handler_function)
    (1, "Evidence Collector", "1.0.0", "COLLECTOR", collector_handler),
    (2, "Forensic Normalizer", "2.1.0", "NORMALIZER", normalizer_handler),
    (3, "Evidence Exporter", "3.4.0", "EXPORTER", exporter_handler),
    (4, "Secure Vault Archiver", "1.5.0", "ARCHIVER", archiver_handler),
]
