"""
FASTA sequence parser and raw sequence input handler.

Supports:
- Standard FASTA format (single and multi-sequence)
- Raw amino acid sequence (plain text)
- Automatic validation of amino acid characters
"""

import re
from typing import List, Tuple, Optional

from core.scales import STANDARD_AA


def parse_fasta(text: str) -> List[Tuple[str, str]]:
    """
    Parse FASTA-formatted text into (header, sequence) pairs.

    Handles:
    - Single and multi-sequence FASTA
    - Wrapped sequences (multiple lines per entry)
    - Comment lines starting with ';'

    Args:
        text: FASTA-formatted text.

    Returns:
        List of (header, sequence) tuples.

    Raises:
        ValueError: If no valid sequences found.
    """
    sequences = []
    current_header = None
    current_seq = []

    for line in text.strip().splitlines():
        line = line.strip()
        if not line or line.startswith(';'):
            continue

        if line.startswith('>'):
            # Save previous sequence
            if current_header is not None and current_seq:
                seq = ''.join(current_seq).upper()
                sequences.append((current_header, seq))

            current_header = line[1:].strip()
            current_seq = []
        else:
            # Sequence continuation
            current_seq.append(line)

    # Save last sequence
    if current_header is not None and current_seq:
        seq = ''.join(current_seq).upper()
        sequences.append((current_header, seq))

    if not sequences:
        raise ValueError(
            "No valid FASTA sequences found. "
            "Ensure the input starts with '>' followed by the header."
        )

    return sequences


def parse_sequence_input(text: str) -> Tuple[str, str]:
    """
    Parse user input that can be either FASTA or raw sequence.

    If the input starts with '>', it's treated as FASTA.
    Otherwise, it's treated as a raw amino acid sequence.

    Args:
        text: User input text.

    Returns:
        Tuple of (header, cleaned_sequence).

    Raises:
        ValueError: If no valid amino acid sequence detected.
    """
    text = text.strip()

    if not text:
        raise ValueError("Input is empty.")

    # Try FASTA format first
    if text.startswith('>'):
        sequences = parse_fasta(text)
        header, sequence = sequences[0]  # Use first sequence
        sequence = validate_sequence(sequence)
        return header, sequence

    # Raw sequence: remove whitespace, numbers, and non-AA characters
    sequence = re.sub(r'[\s\d\-\.\*]', '', text).upper()
    sequence = validate_sequence(sequence)
    return "User_Input_Sequence", sequence


def validate_sequence(sequence: str) -> str:
    """
    Validate and clean a protein sequence.

    Args:
        sequence: Raw protein sequence.

    Returns:
        Cleaned sequence containing only standard amino acids.

    Raises:
        ValueError: If sequence is too short or contains too many
                    invalid characters.
    """
    sequence = sequence.upper().strip()

    # Remove common non-AA characters
    sequence = re.sub(r'[\s\d\-\.\*\n\r]', '', sequence)

    if len(sequence) == 0:
        raise ValueError("Sequence is empty after cleaning.")

    # Check for invalid characters
    invalid_chars = set(sequence) - STANDARD_AA - {'X', 'B', 'Z', 'J'}
    if invalid_chars:
        # Remove invalid characters
        cleaned = ''.join(c for c in sequence if c in STANDARD_AA or c == 'X')
        if len(cleaned) < 10:
            raise ValueError(
                f"Sequence contains too many invalid characters: "
                f"{invalid_chars}. Only {len(cleaned)} valid residues found."
            )
        sequence = cleaned

    # Replace ambiguous codes with common residues
    sequence = sequence.replace('B', 'N')  # B = D or N
    sequence = sequence.replace('Z', 'Q')  # Z = E or Q
    sequence = sequence.replace('J', 'L')  # J = I or L

    if len(sequence) < 12:
        raise ValueError(
            f"Sequence too short ({len(sequence)} aa). "
            f"Minimum 12 residues required for epitope prediction."
        )

    return sequence
