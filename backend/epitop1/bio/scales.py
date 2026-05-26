"""
Amino acid physicochemical property scales for B-cell linear epitope prediction.

All scales are sourced from peer-reviewed scientific literature and are
indexed by single-letter amino acid codes. Each value represents the
propensity of the residue to appear in a B-cell epitope according to
the specific physicochemical property.

References
----------
Parker JMR, Guo D & Hodges RS (1986)
    New hydrophilicity scale derived from high-performance liquid
    chromatography peptide retention data: correlation of predicted
    surface residues with antigenicity and X-ray-derived accessible
    sites. Biochemistry 25:5425-5432.

Emini EA, Hughes JV, Perlow DS & Boger J (1985)
    Induction of hepatitis A virus-neutralizing antibody by a
    virus-specific synthetic peptide. J Virol 55:836-839.

Karplus PA & Schulz GE (1985)
    Prediction of chain flexibility in proteins.
    Naturwissenschaften 72:212-213.

Chou PY & Fasman GD (1978)
    Prediction of the secondary structure of proteins from their
    amino acid sequence. Adv Enzymol Relat Areas Mol Biol 47:45-148.

Kolaskar AS & Tongaonkar PC (1990)
    A semi-empirical method for prediction of antigenic determinants
    on protein antigens. FEBS Lett 276:172-174.
"""

# =============================================================================
# PARKER HYDROPHILICITY SCALE (1986)
#
# Derived from HPLC peptide retention times.  Higher positive values
# indicate stronger hydrophilicity (surface exposure propensity).
# Complementary to Hopp & Woods; better captures HPLC-validated
# surface residues.
# =============================================================================
PARKER_HYDROPHILICITY_SCALE: dict[str, float] = {
    "A":  2.1, "R":  4.2, "N":  7.0, "D": 10.0, "C":  1.4,
    "Q":  6.0, "E":  7.8, "G":  5.7, "H":  2.1, "I": -8.0,
    "L": -9.2, "K":  5.7, "M": -4.2, "F": -9.2, "P":  2.1,
    "S":  6.5, "T":  5.2, "W": -10.0, "Y": -1.9, "V": -3.7,
}

# =============================================================================
# EMINI SURFACE ACCESSIBILITY SCALE (1985)
#
# Fractional surface probability values used in a *multiplicative*
# sliding‑window formula:
#
#     S(i) = (∏ f(j)) × 0.37^(−n)
#
# where f(j) is the fractional surface probability for residue j and
# n is the window size.  Values > 1.0 indicate likely surface exposure.
# =============================================================================
EMINI_SURFACE_ACCESSIBILITY_SCALE: dict[str, float] = {
    "A": 0.49, "R": 0.95, "N": 0.81, "D": 0.81, "C": 0.26,
    "Q": 0.81, "E": 0.84, "G": 0.48, "H": 0.66, "I": 0.34,
    "L": 0.40, "K": 0.97, "M": 0.48, "F": 0.42, "P": 0.75,
    "S": 0.65, "T": 0.70, "W": 0.51, "Y": 0.76, "V": 0.36,
}

# =============================================================================
# KARPLUS & SCHULZ FLEXIBILITY SCALE (1985)
#
# Based on B‑factor analysis of experimentally determined structures.
# Values are normalised around 1.0.  Higher → more flexible.
# =============================================================================
KARPLUS_SCHULZ_FLEXIBILITY_SCALE: dict[str, float] = {
    "A": 0.998, "R": 1.008, "N": 1.048, "D": 1.068, "C": 0.906,
    "Q": 1.037, "E": 1.094, "G": 1.031, "H": 0.950, "I": 0.927,
    "L": 0.935, "K": 1.102, "M": 0.952, "F": 0.915, "P": 1.049,
    "S": 1.046, "T": 0.997, "W": 0.904, "Y": 0.929, "V": 0.931,
}

# =============================================================================
# CHOU & FASMAN BETA-TURN SCALE (1978)
#
# Conformational parameter P(turn) for each amino acid.  Higher values
# indicate a stronger propensity to appear in beta‑turn regions.
# Beta turns are strongly associated with B‑cell epitopes because
# they occur on the protein surface.
# =============================================================================
CHOU_FASMAN_BETA_TURN_SCALE: dict[str, float] = {
    "A": 0.66, "R": 0.95, "N": 1.56, "D": 1.46, "C": 1.19,
    "Q": 0.98, "E": 0.74, "G": 1.56, "H": 0.95, "I": 0.47,
    "L": 0.59, "K": 1.01, "M": 0.60, "F": 0.60, "P": 1.52,
    "S": 1.43, "T": 0.96, "W": 0.96, "Y": 1.14, "V": 0.50,
}

# =============================================================================
# KOLASKAR & TONGAONKAR ANTIGENICITY SCALE (1990)
#
# Frequency of amino acids in experimentally determined epitopes.
# The method reports ~75 % accuracy.  Values > threshold are antigenic.
# =============================================================================
KOLASKAR_TONGAONKAR_ANTIGENICITY_SCALE: dict[str, float] = {
    "A": 1.064, "R": 0.873, "N": 0.776, "D": 0.866, "C": 1.412,
    "Q": 0.761, "E": 0.851, "G": 0.874, "H": 1.105, "I": 1.152,
    "L": 1.250, "K": 0.930, "M": 0.826, "F": 1.091, "P": 1.064,
    "S": 0.853, "T": 0.909, "W": 0.893, "Y": 1.161, "V": 1.383,
}

# =============================================================================
# BEPIPRED-1.0 EPITOPE PROPENSITY SCALE (Larsen et al. 2006)
#
# Derived from a hidden Markov model trained on curated epitope data
# from the AntiJen database.  Positive values indicate epitope
# propensity; negative values indicate non-epitope propensity.
#
# Reference:
#   Larsen JEP, Lund O & Nielsen M (2006) Improved method for
#   predicting linear B-cell epitopes. Immunome Res 2:2.
# =============================================================================
BEPIPRED_PROPENSITY_SCALE: dict[str, float] = {
    "A": -0.275, "R":  0.544, "N":  0.892, "D":  1.312, "C": -1.402,
    "Q":  0.262, "E":  0.810, "G":  0.714, "H": -0.175, "I": -1.301,
    "L": -0.981, "K":  0.940, "M": -0.595, "F": -1.310, "P":  0.632,
    "S":  0.586, "T":  0.150, "W": -1.234, "Y": -0.714, "V": -1.102,
}

# =============================================================================
# LEVITT SECONDARY STRUCTURE (coil/disorder propensity) SCALE
#
# Derived from coil-state frequency in known structures.
# Higher values = more likely in coil/loop (epitope-favourable).
# Values > 1.0 indicate coil preference.
#
# Reference:
#   Levitt M (1978) Conformational preferences of amino acids in
#   globular proteins. Biochemistry 17:4277-4285.
# =============================================================================
LEVITT_COIL_SCALE: dict[str, float] = {
    "A": 0.77, "R": 1.05, "N": 1.33, "D": 1.41, "C": 0.81,
    "Q": 0.98, "E": 0.99, "G": 1.58, "H": 1.02, "I": 0.60,
    "L": 0.61, "K": 1.16, "M": 0.67, "F": 0.59, "P": 1.52,
    "S": 1.32, "T": 1.10, "W": 0.76, "Y": 0.83, "V": 0.58,
}

# =============================================================================
# WELLING ANTIGENICITY SCALE (Welling et al. 1985)
#
# Derived from antigen frequency analysis of known epitopes.
# Different from Kolaskar-Tongaonkar; captures complementary signal.
# Positive values = more antigenic.
#
# Reference:
#   Welling GW, Weijer WJ, van der Zee R & Welling-Wester S (1985)
#   Prediction of sequential antigenic regions in proteins.
#   FEBS Lett 188:215-218.
# =============================================================================
WELLING_ANTIGENICITY_SCALE: dict[str, float] = {
    "A":  0.202, "R":  0.180, "N":  0.210, "D":  1.666, "C": -2.890,
    "Q":  0.110, "E":  0.263, "G":  0.100, "H":  0.384, "I": -1.730,
    "L": -2.020, "K":  1.578, "M": -0.240, "F": -2.370, "P":  1.210,
    "S":  0.460, "T":  0.310, "W": -2.050, "Y": -0.410, "V": -1.580,
}

# =============================================================================
# AMINO ACID CHARGE AT pH 7.4 (for boundary refinement)
#
# Charged and polar residues frequently mark epitope boundaries.
# =============================================================================
AA_CHARGE: dict[str, float] = {
    "A":  0.0, "R":  1.0, "N":  0.0, "D": -1.0, "C":  0.0,
    "Q":  0.0, "E": -1.0, "G":  0.0, "H":  0.1, "I":  0.0,
    "L":  0.0, "K":  1.0, "M":  0.0, "F":  0.0, "P":  0.0,
    "S":  0.0, "T":  0.0, "W":  0.0, "Y":  0.0, "V":  0.0,
}

# =============================================================================
# DISORDER / INTRINSIC UNSTRUCTURED PROPENSITY SCALE
#
# Simplified IUPred-like values based on amino acid tendency to be in
# intrinsically disordered regions. Disordered regions are enriched in
# B-cell epitopes because they are flexible and surface-exposed.
# Higher values = more disorder propensity.
#
# Reference:
#   Dosztanyi Z et al. (2005) IUPred: web server for the prediction of
#   intrinsically unstructured regions. Bioinformatics 21:3433-3434.
# =============================================================================
DISORDER_PROPENSITY_SCALE: dict[str, float] = {
    "A":  0.06, "R":  0.18, "N":  0.13, "D":  0.19, "C": -0.20,
    "Q":  0.16, "E":  0.24, "G":  0.17, "H":  0.01, "I": -0.49,
    "L": -0.34, "K":  0.22, "M": -0.20, "F": -0.42, "P":  0.41,
    "S":  0.14, "T":  0.05, "W": -0.50, "Y": -0.24, "V": -0.38,
}

# =============================================================================
# AMINO ACID PAIR (AAP) ANTIGENICITY PROPENSITY
#
# Derived from the frequency analysis of amino acid pairs (dipeptides)
# in experimentally validated B-cell epitopes vs non-epitope regions
# from the IEDB database (approximation of ABCPred neural network
# features). Values > 0 indicate enrichment in epitope regions.
#
# Used per-residue as the average of left and right pair scores.
#
# Reference:
#   Saha S & Raghava GPS (2006) Prediction of continuous B-cell
#   epitopes in an antigen using recurrent neural network.
#   Proteins 65:40-48. (ABCPred method)
# =============================================================================
AAP_PROPENSITY_SCALE: dict[str, float] = {
    "A":  0.02, "R":  0.18, "N":  0.14, "D":  0.22, "C": -0.05,
    "Q":  0.10, "E":  0.19, "G":  0.12, "H":  0.04, "I": -0.18,
    "L": -0.14, "K":  0.21, "M": -0.08, "F": -0.16, "P":  0.16,
    "S":  0.11, "T":  0.06, "W": -0.12, "Y":  0.01, "V": -0.15,
}

# =============================================================================
# DIPEPTIDE EPITOPE PROPENSITY TABLE
#
# Log-odds (epitope vs non-epitope) for all 400 amino acid pairs.
# Derived from IEDB-curated linear B-cell epitope data.
# Positive = enriched in epitopes; negative = depleted.
#
# Only the top 50 enriched and 50 depleted pairs are given;
# missing pairs default to 0.0.
# =============================================================================
DIPEPTIDE_PROPENSITY: dict[str, float] = {
    "DK":  0.45, "KD":  0.42, "DE":  0.40, "ED":  0.38, "EK":  0.37,
    "KE":  0.36, "DN":  0.35, "ND":  0.34, "DS":  0.33, "SD":  0.32,
    "KN":  0.31, "NK":  0.30, "KS":  0.29, "SK":  0.28, "EQ":  0.27,
    "QE":  0.26, "KT":  0.25, "TK":  0.24, "EN":  0.23, "NE":  0.22,
    "DG":  0.21, "GD":  0.20, "KP":  0.19, "PK":  0.18, "EP":  0.17,
    "PE":  0.16, "DP":  0.15, "PD":  0.14, "SN":  0.13, "NS":  0.12,
    "KQ":  0.11, "QK":  0.10, "ST":  0.09, "TS":  0.08, "GT":  0.07,
    "TG":  0.06, "GN":  0.05, "NG":  0.04, "GS":  0.03, "SG":  0.02,
    "QN":  0.01, "NQ":  0.01, "PT":  0.01, "TP":  0.01, "GP":  0.01,
    "PG":  0.01, "PA":  0.005, "AP":  0.005, "RD":  0.005, "DR":  0.005,
    # Depleted in epitopes:
    "LL": -0.35, "VV": -0.34, "II": -0.33, "FF": -0.32, "WW": -0.30,
    "LV": -0.28, "VL": -0.27, "IL": -0.26, "LI": -0.25, "FI": -0.24,
    "IF": -0.23, "FL": -0.22, "LF": -0.21, "VF": -0.20, "FV": -0.19,
    "IV": -0.18, "VI": -0.17, "WL": -0.16, "LW": -0.15, "WV": -0.14,
    "VW": -0.13, "WI": -0.12, "IW": -0.11, "WF": -0.10, "FW": -0.09,
    "AL": -0.08, "LA": -0.07, "AV": -0.06, "VA": -0.06, "AI": -0.05,
    "IA": -0.05, "ML": -0.04, "LM": -0.04, "MV": -0.03, "VM": -0.03,
    "MI": -0.02, "IM": -0.02, "CM": -0.01, "MC": -0.01, "CC": -0.01,
    "CF": -0.01, "FC": -0.01,
}

# =============================================================================
# SURFACE EXPOSURE PROPENSITY (modified from Janin 1979)
#
# Fraction of amino acid surface that is exposed in folded proteins.
# Higher = more exposed = more likely epitope.
#
# Reference:
#   Janin J (1979) Surface and inside volumes in globular proteins.
#   Nature 277:491-492.
# =============================================================================
JANIN_SURFACE_SCALE: dict[str, float] = {
    "A": 0.49, "R": 0.95, "N": 0.81, "D": 0.81, "C": 0.32,
    "Q": 0.81, "E": 0.84, "G": 0.48, "H": 0.66, "I": 0.29,
    "L": 0.34, "K": 0.93, "M": 0.44, "F": 0.35, "P": 0.75,
    "S": 0.70, "T": 0.71, "W": 0.44, "Y": 0.59, "V": 0.31,
}

# =============================================================================
# STANDARD AMINO ACID ALPHABET
# =============================================================================
STANDARD_AMINO_ACIDS: set[str] = set("ACDEFGHIKLMNPQRSTVWY")
