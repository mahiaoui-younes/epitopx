"""
Solvent Accessible Surface Area (SASA) calculator.

Implements the Shrake & Rupley (1973) algorithm for computing SASA.
Test points are distributed on a sphere of radius (vdW + probe) around
each atom. Points not occluded by neighboring atoms contribute to SASA.

Also provides a simpler residue-level accessibility estimate based on
the Lee & Richards (1971) approach.

References:
    Lee B & Richards FM (1971) The interpretation of protein structures:
    estimation of static accessibility. J Mol Biol 55:379-400.

    Shrake A & Rupley JA (1973) Environment and exposure to solvent of
    protein atoms. Lysozyme and insulin. J Mol Biol 79:351-371.
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
import math

from core.scales import VAN_DER_WAALS_RADII, DEFAULT_VDW_RADIUS


class SASACalculator:
    """
    Computes Solvent Accessible Surface Area using the
    Shrake & Rupley (1973) algorithm.
    """

    def __init__(self, probe_radius: float = 1.4, n_points: int = 100):
        """
        Initialize SASA calculator.

        Args:
            probe_radius: Radius of the solvent probe in Angstroms
                         (default: 1.4 Å for water).
            n_points: Number of test points per sphere (default: 100).
                     Higher values give more accurate results but are slower.
        """
        self.probe_radius = probe_radius
        self.n_points = n_points
        self._sphere_points = self._generate_sphere_points(n_points)

    @staticmethod
    def _generate_sphere_points(n: int) -> np.ndarray:
        """
        Generate approximately uniformly distributed points on a unit sphere
        using the golden spiral method.

        Args:
            n: Number of points to generate.

        Returns:
            (n, 3) array of unit sphere points.
        """
        points = np.zeros((n, 3))
        golden_ratio = (1 + math.sqrt(5)) / 2
        golden_angle = 2 * math.pi / golden_ratio

        for i in range(n):
            # Distribute points along z-axis uniformly
            z = 1 - (2 * i + 1) / n
            radius_xy = math.sqrt(1 - z * z)
            theta = golden_angle * i

            points[i, 0] = radius_xy * math.cos(theta)
            points[i, 1] = radius_xy * math.sin(theta)
            points[i, 2] = z

        return points

    def _get_vdw_radius(self, element: str) -> float:
        """
        Get van der Waals radius for an element.

        Args:
            element: Element symbol (e.g., 'C', 'N', 'O').

        Returns:
            Van der Waals radius in Angstroms.
        """
        element = element.upper().strip()
        return VAN_DER_WAALS_RADII.get(element, DEFAULT_VDW_RADIUS)

    def calculate_atom_sasa(
        self,
        coords: np.ndarray,
        elements: List[str],
        residue_ids: List[int],
    ) -> Tuple[np.ndarray, Dict[int, float]]:
        """
        Calculate SASA for each atom and aggregate by residue.

        Implements Shrake & Rupley (1973):
        For each atom i, place n_points test points on a sphere of radius
        (r_vdw_i + r_probe). A test point is "accessible" if it does not
        fall within (r_vdw_j + r_probe) of any neighboring atom j.
        SASA_i = (4π(r_vdw_i + r_probe)²) × (accessible_points / n_points)

        Args:
            coords: (N, 3) array of atomic coordinates.
            elements: List of element symbols for each atom.
            residue_ids: List of residue index for each atom.

        Returns:
            Tuple of:
                - atom_sasa: Array of SASA per atom
                - residue_sasa: Dict mapping residue_id -> total SASA
        """
        n_atoms = len(coords)
        radii = np.array([
            self._get_vdw_radius(e) + self.probe_radius for e in elements
        ])

        atom_sasa = np.zeros(n_atoms)

        # For efficiency, pre-compute pairwise distances
        # and only check neighbors within max possible overlap distance
        max_radius = np.max(radii) if n_atoms > 0 else 0
        cutoff = 2 * max_radius + 2 * self.probe_radius

        for i in range(n_atoms):
            # Generate test points for atom i
            r_i = radii[i]
            test_points = self._sphere_points * r_i + coords[i]

            # Find neighboring atoms within cutoff
            if n_atoms > 1:
                dists = np.linalg.norm(coords - coords[i], axis=1)
                neighbors = np.where(
                    (dists < cutoff) & (np.arange(n_atoms) != i)
                )[0]
            else:
                neighbors = np.array([], dtype=int)

            if len(neighbors) == 0:
                # All points accessible
                atom_sasa[i] = 4 * math.pi * r_i * r_i
            else:
                # Check each test point against neighbors
                n_accessible = 0
                neighbor_coords = coords[neighbors]
                neighbor_radii = radii[neighbors]

                for p in test_points:
                    dists_to_neighbors = np.linalg.norm(
                        neighbor_coords - p, axis=1
                    )
                    if np.all(dists_to_neighbors >= neighbor_radii):
                        n_accessible += 1

                atom_sasa[i] = (
                    4 * math.pi * r_i * r_i * n_accessible / self.n_points
                )

        # Aggregate by residue
        residue_sasa: Dict[int, float] = {}
        for i in range(n_atoms):
            res_id = residue_ids[i]
            if res_id not in residue_sasa:
                residue_sasa[res_id] = 0.0
            residue_sasa[res_id] += atom_sasa[i]

        return atom_sasa, residue_sasa

    def calculate_relative_sasa(
        self,
        residue_sasa: Dict[int, float],
        residue_names: Dict[int, str],
    ) -> Dict[int, float]:
        """
        Calculate relative SASA (ratio of actual to maximum possible SASA).

        Maximum SASA values are based on Gly-X-Gly tripeptides
        (Tien et al., 2013).

        Args:
            residue_sasa: Dict mapping residue_id -> absolute SASA.
            residue_names: Dict mapping residue_id -> one-letter AA code.

        Returns:
            Dict mapping residue_id -> relative SASA (0.0 to 1.0+).
        """
        # Maximum SASA values (Å²) for amino acids in Gly-X-Gly context
        # From Tien et al. (2013) PLoS ONE 8:e80635
        max_sasa = {
            'A': 129.0, 'R': 274.0, 'N': 195.0, 'D': 193.0, 'C': 167.0,
            'Q': 225.0, 'E': 223.0, 'G': 104.0, 'H': 224.0, 'I': 197.0,
            'L': 201.0, 'K': 236.0, 'M': 224.0, 'F': 240.0, 'P': 159.0,
            'S': 155.0, 'T': 172.0, 'W': 285.0, 'Y': 263.0, 'V': 174.0,
        }

        relative = {}
        for res_id, sasa in residue_sasa.items():
            aa = residue_names.get(res_id, 'A')
            max_val = max_sasa.get(aa, 200.0)
            relative[res_id] = min(sasa / max_val, 2.0) if max_val > 0 else 0.0

        return relative
