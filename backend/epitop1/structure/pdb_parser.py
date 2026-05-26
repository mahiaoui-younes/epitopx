"""
PDB file parser for structural analysis.

Parses PDB files (standard format and AlphaFold/ColabFold output)
to extract atomic coordinates, residue information, and compute
structural accessibility.

Uses BioPython's PDB module when available, with a fallback
pure-Python parser for basic PDB parsing.

References:
    Berman HM et al. (2000) The Protein Data Bank.
    Nucleic Acids Res 28:235-242.
"""

import os
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from core.scales import AA_3TO1, STANDARD_AA
from structure.sasa import SASACalculator


@dataclass
class Residue:
    """Represents a single amino acid residue from a PDB structure."""
    index: int              # Sequential index (0-based)
    resnum: int             # PDB residue number
    chain: str              # Chain identifier
    name_3: str             # Three-letter code
    name_1: str             # One-letter code
    atoms: List[dict] = field(default_factory=list)
    sasa: float = 0.0       # Absolute SASA
    relative_sasa: float = 0.0  # Relative SASA
    b_factor: float = 0.0   # Average B-factor / pLDDT for AlphaFold
    is_exposed: bool = False


class PDBParser:
    """
    Parses PDB files and extracts structural information for
    epitope prediction.
    """

    def __init__(self, probe_radius: float = 1.4, n_sasa_points: int = 100):
        """
        Initialize PDB parser.

        Args:
            probe_radius: Solvent probe radius for SASA (default: 1.4 Å).
            n_sasa_points: Number of SASA test points (default: 100).
        """
        self.probe_radius = probe_radius
        self.n_sasa_points = n_sasa_points
        self.residues: List[Residue] = []
        self.sequence: str = ""
        self.sasa_calculator = SASACalculator(probe_radius, n_sasa_points)

    def parse(self, pdb_path: str, chain_id: str = None) -> List[Residue]:
        """
        Parse a PDB file and extract residue information.

        Tries BioPython first, falls back to pure Python parser.

        Args:
            pdb_path: Path to PDB file.
            chain_id: Chain to extract (default: first chain).

        Returns:
            List of Residue objects.
        """
        if not os.path.exists(pdb_path):
            raise FileNotFoundError(f"PDB file not found: {pdb_path}")

        try:
            return self._parse_biopython(pdb_path, chain_id)
        except ImportError:
            return self._parse_fallback(pdb_path, chain_id)

    def _parse_biopython(
        self, pdb_path: str, chain_id: str = None
    ) -> List[Residue]:
        """
        Parse PDB using BioPython's PDB module.

        Args:
            pdb_path: Path to PDB file.
            chain_id: Chain to extract.

        Returns:
            List of Residue objects.
        """
        from Bio.PDB import PDBParser as BioPDBParser

        parser = BioPDBParser(QUIET=True)
        structure = parser.get_structure("protein", pdb_path)
        model = structure[0]  # First model

        # Select chain
        chains = list(model.get_chains())
        if chain_id:
            chain = None
            for c in chains:
                if c.get_id() == chain_id:
                    chain = c
                    break
            if chain is None:
                raise ValueError(
                    f"Chain '{chain_id}' not found. "
                    f"Available: {[c.get_id() for c in chains]}"
                )
        else:
            chain = chains[0]

        self.residues = []
        idx = 0

        for residue in chain.get_residues():
            # Skip water and heteroatoms (unless modified AA)
            hetflag = residue.get_id()[0]
            if hetflag == 'W':
                continue
            resname = residue.get_resname().strip()
            if hetflag.startswith('H') and resname not in AA_3TO1:
                continue

            # Convert three-letter to one-letter
            name_1 = AA_3TO1.get(resname, 'X')
            if name_1 not in STANDARD_AA:
                name_1 = 'X'

            resnum = residue.get_id()[1]

            # Extract atoms
            atoms = []
            b_factors = []
            for atom in residue.get_atoms():
                atoms.append({
                    "name": atom.get_name(),
                    "element": atom.element.strip() if atom.element else
                               atom.get_name()[0],
                    "coord": atom.get_vector().get_array().tolist(),
                    "b_factor": atom.get_bfactor(),
                })
                b_factors.append(atom.get_bfactor())

            avg_b = np.mean(b_factors) if b_factors else 0.0

            res = Residue(
                index=idx,
                resnum=resnum,
                chain=chain.get_id(),
                name_3=resname,
                name_1=name_1,
                atoms=atoms,
                b_factor=float(avg_b),
            )
            self.residues.append(res)
            idx += 1

        self.sequence = "".join(r.name_1 for r in self.residues)
        return self.residues

    def _parse_fallback(
        self, pdb_path: str, chain_id: str = None
    ) -> List[Residue]:
        """
        Fallback pure-Python PDB parser for ATOM records.

        Args:
            pdb_path: Path to PDB file.
            chain_id: Chain to extract.

        Returns:
            List of Residue objects.
        """
        residue_dict: Dict[Tuple[str, int], Residue] = {}
        idx = 0

        with open(pdb_path, 'r') as f:
            for line in f:
                if not (line.startswith("ATOM") or line.startswith("HETATM")):
                    continue

                # PDB format: fixed-width columns
                atom_name = line[12:16].strip()
                resname = line[17:20].strip()
                chain = line[21:22].strip()
                try:
                    resnum = int(line[22:26].strip())
                except ValueError:
                    continue

                # Filter chain
                if chain_id and chain != chain_id:
                    continue

                # Skip non-amino acid HETATMs
                if line.startswith("HETATM") and resname not in AA_3TO1:
                    continue

                # Skip water
                if resname in ('HOH', 'WAT', 'H2O'):
                    continue

                name_1 = AA_3TO1.get(resname, 'X')
                if name_1 not in STANDARD_AA:
                    name_1 = 'X'

                try:
                    x = float(line[30:38])
                    y = float(line[38:46])
                    z = float(line[46:54])
                    b_factor = float(line[60:66]) if len(line) >= 66 else 0.0
                except ValueError:
                    continue

                # Determine element
                if len(line) >= 78:
                    element = line[76:78].strip()
                else:
                    element = atom_name[0]

                key = (chain, resnum)
                if key not in residue_dict:
                    res = Residue(
                        index=idx,
                        resnum=resnum,
                        chain=chain if chain else 'A',
                        name_3=resname,
                        name_1=name_1,
                        atoms=[],
                    )
                    residue_dict[key] = res
                    idx += 1

                residue_dict[key].atoms.append({
                    "name": atom_name,
                    "element": element if element else atom_name[0],
                    "coord": [x, y, z],
                    "b_factor": b_factor,
                })

        # Calculate average B-factors
        self.residues = []
        for key in sorted(residue_dict.keys()):
            res = residue_dict[key]
            b_factors = [a["b_factor"] for a in res.atoms]
            res.b_factor = float(np.mean(b_factors)) if b_factors else 0.0
            self.residues.append(res)

        # Re-index
        for i, res in enumerate(self.residues):
            res.index = i

        # Apply chain filter if needed (first chain)
        if not chain_id and self.residues:
            first_chain = self.residues[0].chain
            self.residues = [r for r in self.residues if r.chain == first_chain]
            for i, res in enumerate(self.residues):
                res.index = i

        self.sequence = "".join(r.name_1 for r in self.residues)
        return self.residues

    def compute_sasa(self) -> Dict[int, float]:
        """
        Compute SASA for all residues using the Shrake & Rupley algorithm.

        Returns:
            Dict mapping residue index -> relative SASA.
        """
        if not self.residues:
            return {}

        # Collect all atoms
        all_coords = []
        all_elements = []
        all_residue_ids = []

        for res in self.residues:
            for atom in res.atoms:
                all_coords.append(atom["coord"])
                all_elements.append(atom["element"])
                all_residue_ids.append(res.index)

        if not all_coords:
            return {}

        coords = np.array(all_coords)

        # Calculate SASA
        _, residue_sasa = self.sasa_calculator.calculate_atom_sasa(
            coords, all_elements, all_residue_ids
        )

        # Calculate relative SASA
        residue_names = {res.index: res.name_1 for res in self.residues}
        relative_sasa = self.sasa_calculator.calculate_relative_sasa(
            residue_sasa, residue_names
        )

        # Update residue objects
        for res in self.residues:
            res.sasa = residue_sasa.get(res.index, 0.0)
            res.relative_sasa = relative_sasa.get(res.index, 0.0)
            res.is_exposed = res.relative_sasa >= 0.25

        return relative_sasa

    def get_structural_accessibility(self) -> np.ndarray:
        """
        Get per-residue structural accessibility as a numpy array.

        Returns:
            Array of relative SASA values per residue.
        """
        relative_sasa = self.compute_sasa()
        result = np.zeros(len(self.residues))
        for i, res in enumerate(self.residues):
            result[i] = relative_sasa.get(res.index, 0.0)
        return result

    def get_b_factors(self) -> np.ndarray:
        """
        Get per-residue B-factors (pLDDT for AlphaFold structures).

        Returns:
            Array of average B-factor per residue.
        """
        return np.array([res.b_factor for res in self.residues])

    def get_sequence(self) -> str:
        """Get the protein sequence extracted from the PDB."""
        return self.sequence

    def align_to_sequence(self, target_sequence: str) -> Dict[int, int]:
        """
        Align PDB residues to a target protein sequence.
        Uses simple subsequence matching.

        Args:
            target_sequence: The full protein sequence.

        Returns:
            Dict mapping target_sequence position -> PDB residue index.
        """
        pdb_seq = self.sequence
        alignment = {}

        # Try to find PDB sequence within target
        pos = target_sequence.find(pdb_seq)
        if pos >= 0:
            for i in range(len(pdb_seq)):
                alignment[pos + i] = i
            return alignment

        # Simple gapless alignment (find best match)
        best_pos = 0
        best_score = 0
        for start in range(len(target_sequence) - len(pdb_seq) + 1):
            score = sum(
                1 for i in range(len(pdb_seq))
                if target_sequence[start + i] == pdb_seq[i]
            )
            if score > best_score:
                best_score = score
                best_pos = start

        for i in range(len(pdb_seq)):
            alignment[best_pos + i] = i

        return alignment
