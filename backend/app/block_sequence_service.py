"""Block sequence validation — pure logic, no I/O.

Validates a submitted color against the required predefined sequence
(safety_config.REQUIRED_BLOCK_SEQUENCE). It NEVER reorders, skips, or silently
fixes a wrong submission: a wrong color is rejected and the submitted sequence
is left unchanged so the operator must submit the correct next color.
"""
from .safety_config import ALL_BLOCK_COLORS, REQUIRED_BLOCK_SEQUENCE, normalize_color


def expected_next_color(submitted: list):
    """The color the sequence expects next, or None if already complete."""
    n = len(submitted)
    if n >= len(REQUIRED_BLOCK_SEQUENCE):
        return None
    return REQUIRED_BLOCK_SEQUENCE[n]


def validate_submission(submitted: list, color: str) -> dict:
    """Validate one color submission against the required sequence.

    Returns a dict describing the outcome. On success the new color is appended;
    on failure `submitted_sequence` is the UNCHANGED prior list.
    """
    submitted = list(submitted or [])
    received = normalize_color(color)
    expected = expected_next_color(submitted)

    # The sequence is already complete — nothing more should be submitted.
    if expected is None:
        return {
            "accepted": False,
            "error_detected": True,
            "error_type": "sequence_already_complete",
            "expected_color": None,
            "received_color": received,
            "submitted_sequence": submitted,
            "expected_next_color": None,
            "sequence_passed": True,
            "message": "Block sequence already complete.",
        }

    # Unknown color (not part of the palette) — distinct from a wrong order.
    if received not in ALL_BLOCK_COLORS:
        return {
            "accepted": False,
            "error_detected": True,
            "error_type": "invalid_color",
            "expected_color": expected,
            "received_color": received,
            "submitted_sequence": submitted,
            "expected_next_color": expected,
            "sequence_passed": False,
            "message": f"Unknown block color '{received}'. Work Order remains locked.",
        }

    # Wrong order — DO NOT fix, reorder, or skip. Reject and keep the WO locked.
    if received != expected:
        return {
            "accepted": False,
            "error_detected": True,
            "error_type": "wrong_block_order",
            "expected_color": expected,
            "received_color": received,
            "submitted_sequence": submitted,
            "expected_next_color": expected,
            "sequence_passed": False,
            "message": "Wrong block order detected. Work Order remains locked.",
        }

    # Correct — append and recompute.
    new_seq = submitted + [received]
    nxt = expected_next_color(new_seq)
    passed = nxt is None
    return {
        "accepted": True,
        "error_detected": False,
        "error_type": None,
        "expected_color": expected,
        "received_color": received,
        "submitted_sequence": new_seq,
        "expected_next_color": nxt,
        "sequence_passed": passed,
        "message": (
            "Block sequence complete." if passed
            else f"Accepted {received}. Next expected: {nxt}."
        ),
    }
