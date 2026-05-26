"""
Amino acid property scales used in B linear epitope prediction.

All scales are sourced from peer-reviewed scientific literature.
Values are indexed by single-letter amino acid codes.

References:
    Hopp & Woods (1981) PNAS 78:3824-3828
    Kyte & Doolittle (1982) J Mol Biol 157:105-132
    Karplus & Schulz (1985) Naturwissenschaften 72:212-213
    Emini et al. (1985) J Virol 55:836-839
    Kolaskar & Tongaonkar (1990) FEBS Lett 276:172-174
    Parker et al. (1986) Biochemistry 25:5425-5432
"""

# =============================================================================
# HOPP & WOODS HYDROPHILICITY SCALE (1981)
# Higher values = more hydrophilic = more likely surface-exposed
# =============================================================================
HOPP_WOODS_SCALE = {
    'A': -0.5, 'R':  3.0, 'N':  0.2, 'D':  3.0, 'C': -1.0,
    'Q':  0.2, 'E':  3.0, 'G':  0.0, 'H': -0.5, 'I': -1.8,
    'L': -1.8, 'K':  3.0, 'M': -1.3, 'F': -2.5, 'P':  0.0,
    'S':  0.3, 'T': -0.4, 'W': -3.4, 'Y': -2.3, 'V': -1.5,
}

# =============================================================================
# KYTE & DOOLITTLE HYDROPHOBICITY SCALE (1982)
# Higher values = more hydrophobic = more likely buried
# =============================================================================
KYTE_DOOLITTLE_SCALE = {
    'A':  1.8, 'R': -4.5, 'N': -3.5, 'D': -3.5, 'C':  2.5,
    'Q': -3.5, 'E': -3.5, 'G': -0.4, 'H': -3.2, 'I':  4.5,
    'L':  3.8, 'K': -3.9, 'M':  1.9, 'F':  2.8, 'P': -1.6,
    'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V':  4.2,
}

# =============================================================================
# KARPLUS & SCHULZ FLEXIBILITY SCALE (1985)
# Based on B-factor analysis of known protein structures
# Higher values = more flexible
# =============================================================================
KARPLUS_SCHULZ_SCALE = {
    'A': 0.998, 'R': 1.008, 'N': 1.048, 'D': 1.068, 'C': 0.906,
    'Q': 1.037, 'E': 1.094, 'G': 1.031, 'H': 0.950, 'I': 0.927,
    'L': 0.935, 'K': 1.102, 'M': 0.952, 'F': 0.915, 'P': 1.049,
    'S': 1.046, 'T': 0.997, 'W': 0.904, 'Y': 0.929, 'V': 0.931,
}

# =============================================================================
# EMINI SURFACE ACCESSIBILITY SCALE (1985)
# Fractional surface probability values
# Used multiplicatively in a sliding window
# =============================================================================
EMINI_SCALE = {
    'A': 0.49, 'R': 0.95, 'N': 0.81, 'D': 0.81, 'C': 0.26,
    'Q': 0.81, 'E': 0.84, 'G': 0.48, 'H': 0.66, 'I': 0.34,
    'L': 0.40, 'K': 0.97, 'M': 0.48, 'F': 0.42, 'P': 0.75,
    'S': 0.65, 'T': 0.70, 'W': 0.51, 'Y': 0.76, 'V': 0.36,
}

# =============================================================================
# KOLASKAR & TONGAONKAR ANTIGENICITY SCALE (1990)
# Based on the frequency of amino acids in experimentally determined epitopes
# Higher values = more antigenic
# =============================================================================
KOLASKAR_TONGAONKAR_SCALE = {
    'A': 1.064, 'R': 0.873, 'N': 0.776, 'D': 0.866, 'C': 1.412,
    'Q': 0.761, 'E': 0.851, 'G': 0.874, 'H': 1.105, 'I': 1.152,
    'L': 1.250, 'K': 0.930, 'M': 0.826, 'F': 1.091, 'P': 1.064,
    'S': 0.853, 'T': 0.909, 'W': 0.893, 'Y': 1.161, 'V': 1.383,
}

# =============================================================================
# PARKER HYDROPHILICITY SCALE (1986) — complementary to Hopp & Woods
# =============================================================================
PARKER_SCALE = {
    'A':  2.1, 'R':  4.2, 'N':  7.0, 'D': 10.0, 'C':  1.4,
    'Q':  6.0, 'E':  7.8, 'G':  5.7, 'H':  2.1, 'I': -8.0,
    'L': -9.2, 'K':  5.7, 'M': -4.2, 'F': -9.2, 'P':  2.1,
    'S':  6.5, 'T':  5.2, 'W': -10.0, 'Y': -1.9, 'V': -3.7,
}

# =============================================================================
# VAN DER WAALS RADII (Å) for SASA calculation
# =============================================================================
VAN_DER_WAALS_RADII = {
    'C': 1.70, 'N': 1.55, 'O': 1.52, 'S': 1.80, 'H': 1.20,
    'P': 1.80, 'FE': 1.47, 'ZN': 1.39, 'CA': 1.97, 'MG': 1.73,
    'MN': 1.39, 'CU': 1.40, 'SE': 1.90,
}

# Default radius for unknown atom types
DEFAULT_VDW_RADIUS = 1.70

# =============================================================================
# STANDARD AMINO ACID SET
# =============================================================================
STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")

# Three-letter to one-letter conversion
AA_3TO1 = {
    'ALA': 'A', 'ARG': 'R', 'ASN': 'N', 'ASP': 'D', 'CYS': 'C',
    'GLN': 'Q', 'GLU': 'E', 'GLY': 'G', 'HIS': 'H', 'ILE': 'I',
    'LEU': 'L', 'LYS': 'K', 'MET': 'M', 'PHE': 'F', 'PRO': 'P',
    'SER': 'S', 'THR': 'T', 'TRP': 'W', 'TYR': 'Y', 'VAL': 'V',
    # Non-standard
    'MSE': 'M', 'HSD': 'H', 'HSE': 'H', 'HSP': 'H',
}
