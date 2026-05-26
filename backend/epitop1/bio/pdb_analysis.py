"""
PDB structure analysis for epitope prediction.

Provides optional structural support: when a PDB file is available the
module computes an approximate per-residue solvent-accessible surface
area (SASA) using BioPython and the Shrake & Rupley algorithm, then
returns a boolean surface-exposure mask.

If BioPython is not installed, a lightweight pure-Python fallback
extracts CA coordinates and approximates exposure from packing density.

When no PDB is provided the caller should simply omit the structural
SASA and the scoring engine will fall back to sequence-only prediction.

References
----------
Shrake A & Rupley JA (1973) J Mol Biol 79:351-371.
Berman HM et al. (2000) Nucleic Acids Res 28:235-242.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

# Three-letter → one-letter amino acid code
_AA3TO1: dict[str, str] = {
    "ALA": "A", "ARG": "R", "ASN": "N", "ASP": "D", "CYS": "C",
    "GLN": "Q", "GLU": "E", "GLY": "G", "HIS": "H", "ILE": "I",
    "LEU": "L", "LYS": "K", "MET": "M", "PHE": "F", "PRO": "P",
    "SER": "S", "THR": "T", "TRP": "W", "TYR": "Y", "VAL": "V",
    "MSE": "M", "HSD": "H", "HSE": "H", "HSP": "H",
}

# MaxASA values (Å²) per residue for relative SASA –
# Tien et al. (2013) PLoS ONE 8:e80635
_MAX_ASA: dict[str, float] = {
    "A": 129.0, "R": 274.0, "N": 195.0, "D": 193.0, "C": 167.0,
    "Q": 225.0, "E": 223.0, "G": 104.0, "H": 224.0, "I": 197.0,
    "L": 201.0, "K": 236.0, "M": 224.0, "F": 240.0, "P": 159.0,
    "S": 155.0, "T": 172.0, "W": 285.0, "Y": 263.0, "V": 174.0,
}


@dataclass
class PDBResidue:
    """Minimal representation of a PDB residue."""
    index: int
    resnum: int
    chain: str
    name3: str
    name1: str
    relative_sasa: float = 0.0
    is_exposed: bool = False


def parse_pdb_sasa(
    pdb_path: str,
    chain_id: str | None = None,
    exposure_threshold: float = 0.25,
) -> tuple[str, np.ndarray, list[PDBResidue]]:
    """Parse a PDB file and compute per-residue relative SASA.

    Parameters
    ----------
    pdb_path : str
        Path to the PDB file.
    chain_id : str | None
        Chain identifier.  ``None`` → first chain.
    exposure_threshold : float
        Relative SASA above which a residue is considered exposed.

    Returns
    -------
    sequence : str
        One-letter amino acid sequence extracted from the structure.
    relative_sasa : np.ndarray
        Per-residue relative SASA (0–1+).
    residues : list[PDBResidue]
        Structured residue information.

    Raises
    ------
    FileNotFoundError
        If *pdb_path* does not exist.
    ImportError
        If BioPython is not installed (caller should catch and
        fall back to sequence-only mode).
    """
    if not os.path.isfile(pdb_path):
        raise FileNotFoundError(f"PDB file not found: {pdb_path}")

    # ---- BioPython path (preferred) ----
    from Bio.PDB import PDBParser as BioPDBParser
    from Bio.PDB.DSSP import dssp_dict_from_pdb_file  # type: ignore

    parser = BioPDBParser(QUIET=True)
    structure = parser.get_structure("protein", pdb_path)
    model = structure[0]

    chains = list(model.get_chains())
    if chain_id:
        chain = next(
            (c for c in chains if c.get_id() == chain_id), None
        )
        if chain is None:
            avail = [c.get_id() for c in chains]
            raise ValueError(
                f"Chain '{chain_id}' not found. Available: {avail}"
            )
    else:
        chain = chains[0]

    residues: list[PDBResidue] = []
    idx = 0
    for res in chain.get_residues():
        hetflag = res.get_id()[0]
        if hetflag.strip() and hetflag != " ":
            resname = res.get_resname().strip()
            if resname not in _AA3TO1:
                continue
        resname = res.get_resname().strip()
        aa1 = _AA3TO1.get(resname)
        if aa1 is None:
            continue
        residues.append(
            PDBResidue(
                index=idx,
                resnum=res.get_id()[1],
                chain=chain.get_id(),
                name3=resname,
                name1=aa1,
            )
        )
        idx += 1

    # Compute SASA using BioPython's built-in ShrakeRupley
    try:
        from Bio.PDB.SASA import ShrakeRupley
        sr = ShrakeRupley()
        sr.compute(model, level="R")
        for pdb_res, bio_res in zip(
            residues, (r for r in chain.get_residues()
                       if _AA3TO1.get(r.get_resname().strip()))
        ):
            abs_sasa = bio_res.sasa  # type: ignore[attr-defined]
            max_asa = _MAX_ASA.get(pdb_res.name1, 200.0)
            pdb_res.relative_sasa = abs_sasa / max_asa if max_asa > 0 else 0.0
            pdb_res.is_exposed = pdb_res.relative_sasa >= exposure_threshold
    except Exception:
        # Fallback: estimate exposure from CA packing density
        _estimate_exposure_from_ca(residues, chain, exposure_threshold)

    sequence = "".join(r.name1 for r in residues)
    rel_sasa = np.array([r.relative_sasa for r in residues], dtype=np.float64)

    return sequence, rel_sasa, residues


def _estimate_exposure_from_ca(
    residues: list[PDBResidue],
    chain,  # Bio.PDB.Chain
    threshold: float,
) -> None:
    """Rough exposure estimate from CA packing density (fallback).

    Counts number of CA atoms within 10 Å of each CA.  Fewer
    neighbours → more exposed.
    """
    ca_coords: list[np.ndarray | None] = []
    for pdb_res, bio_res in zip(
        residues,
        (r for r in chain.get_residues()
         if _AA3TO1.get(r.get_resname().strip())),
    ):
        if "CA" in bio_res:
            ca_coords.append(np.array(bio_res["CA"].get_vector().get_array()))
        else:
            ca_coords.append(None)

    n = len(ca_coords)
    for i, coord_i in enumerate(ca_coords):
        if coord_i is None:
            residues[i].relative_sasa = 0.0
            continue
        neighbours = 0
        for j, coord_j in enumerate(ca_coords):
            if i == j or coord_j is None:
                continue
            if np.linalg.norm(coord_i - coord_j) < 10.0:
                neighbours += 1
        # Heuristic: fewer neighbours → higher exposure
        residues[i].relative_sasa = max(0.0, 1.0 - neighbours / 25.0)
        residues[i].is_exposed = residues[i].relative_sasa >= threshold


def align_structure_to_sequence(
    pdb_sequence: str,
    target_sequence: str,
    residues: list[PDBResidue],
) -> np.ndarray:
    """Align PDB-derived SASA to the target sequence.

    Returns an array of length ``len(target_sequence)`` where each
    entry is the relative SASA of the aligned PDB residue, or 0.0
    for unmatched positions.

    A simple substring / identity alignment is attempted first;
    if that fails, a gapless sliding-window best-match is used.
    """
    target = target_sequence.upper()
    pdb_seq = pdb_sequence.upper()
    n_target = len(target)

    sasa_out = np.zeros(n_target, dtype=np.float64)

    # Try direct substring match
    idx = target.find(pdb_seq)
    if idx >= 0:
        for k, res in enumerate(residues):
            pos = idx + k
            if pos < n_target:
                sasa_out[pos] = res.relative_sasa
        return sasa_out

    # Fall back: best sliding alignment by identity
    best_score = -1
    best_offset = 0
    min_len = min(len(pdb_seq), n_target)
    for offset in range(n_target - min_len + 1):
        score = sum(
            1 for a, b in zip(pdb_seq, target[offset:]) if a == b
        )
        if score > best_score:
            best_score = score
            best_offset = offset

    for k, res in enumerate(residues):
        pos = best_offset + k
        if pos < n_target:
            sasa_out[pos] = res.relative_sasa

    return sasa_out
