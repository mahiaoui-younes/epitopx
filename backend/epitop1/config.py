"""
Configuration module for EpiTop1 - B Linear Epitope Prediction Software.

Contains all configurable parameters including scoring weights,
sliding window sizes, epitope selection criteria, and export settings.

References:
    - Hopp & Woods (1981) PNAS 78:3824-3828
    - Kyte & Doolittle (1982) J Mol Biol 157:105-132
    - Karplus & Schulz (1985) Naturwissenschaften 72:212-213
    - Emini et al. (1985) J Virol 55:836-839
    - Kolaskar & Tongaonkar (1990) FEBS Lett 276:172-174
    - Pellequer & Westhof (1993) Methods Enzymol 237:1-11
    - Saha & Raghava (2006) Proteins 65:40-48
    - Jespersen et al. (2017) Nucleic Acids Res 45:W265-W270
"""

# =============================================================================
# SCORING WEIGHTS
# =============================================================================
# Global score = w1*hydrophilicity + w2*accessibility + w3*flexibility
#              + w4*antigenicity - w5*hydrophobicity

SCORING_WEIGHTS = {
    "w1_hydrophilicity": 0.22,      # Hopp & Woods — slightly reduced
    "w2_surface_accessibility": 0.22, # Emini et al. — slightly reduced
    "w3_flexibility": 0.19,          # Karplus & Schulz — increased more
    "w4_antigenicity": 0.24,         # Kolaskar & Tongaonkar — increased more
    "w5_hydrophobicity": 0.13,       # Kyte & Doolittle (penalty) — kept low
}

# =============================================================================
# SLIDING WINDOW PARAMETERS
# =============================================================================
WINDOW_SIZES = {
    "hydrophilicity": 7,    # Hopp & Woods recommended window
    "hydrophobicity": 9,    # Kyte & Doolittle recommended window
    "flexibility": 7,       # Karplus & Schulz recommended window
    "accessibility": 6,     # Emini et al. recommended window
    "antigenicity": 7,      # Kolaskar & Tongaonkar recommended window
    "global_smoothing": 9,  # Final score smoothing window
}

# =============================================================================
# EPITOPE SELECTION CRITERIA
# =============================================================================
EPITOPE_CRITERIA = {
    "min_length": 9,            # Minimum epitope length (aa) — reduced from 10
    "max_length": 35,           # Maximum epitope length (aa)
    "min_global_score": 0.25,   # Minimum normalized global score threshold — reduced more
    "min_hydrophilicity": -1.0, # Minimum hydrophilicity score (more relaxed)
    "min_accessibility": 0.7,   # Minimum Emini surface accessibility — more relaxed
    "max_hydrophobicity": 1.3,  # Maximum hydrophobicity (exclude buried) — more relaxed
    "top_n_epitopes": 35,       # Maximum number of epitopes to report — increased
    "merge_gap": 4,             # Max gap (aa) for merging adjacent regions
    "adaptive_threshold": True, # Use adaptive score threshold
}

# =============================================================================
# SASA PARAMETERS (Shrake & Rupley, 1973)
# =============================================================================
SASA_PARAMS = {
    "probe_radius": 1.4,       # Water probe radius in Angstroms
    "n_points": 100,            # Number of test points per sphere
    "sasa_threshold": 0.25,     # Relative SASA threshold for exposed residues
}

# =============================================================================
# HYDROPHILIC / HYDROPHOBIC RESIDUE SETS
# (for filtering per Pellequer & Westhof 1993)
# =============================================================================
HYDROPHILIC_RESIDUES = set("EDKRQNS")
HYDROPHOBIC_RESIDUES = set("LIVFW")

# =============================================================================
# TRANSMEMBRANE / SIGNAL PEPTIDE EXCLUSION
# =============================================================================
EXCLUSION_PARAMS = {
    "tm_hydrophobicity_threshold": 1.6,  # Kyte-Doolittle window avg threshold
    "tm_min_length": 15,                  # Min consecutive hydrophobic stretch
    "signal_peptide_max_pos": 0,          # Signal peptide region (0 = disabled)
    "buried_sasa_threshold": 0.10,        # SASA below this = buried
}

# =============================================================================
# CONSERVATION FILTER (placeholder for multi-sequence alignment)
# =============================================================================
CONSERVATION_PARAMS = {
    "min_identity": 0.90,       # ≥ 90% identity between isolates
    "max_gap_fraction": 0.05,   # No major insertions/deletions
}

# =============================================================================
# EXPORT SETTINGS
# =============================================================================
EXPORT_SETTINGS = {
    "csv_delimiter": ",",
    "float_precision": 4,
    "json_indent": 2,
}

# =============================================================================
# GUI SETTINGS
# =============================================================================
# =============================================================================
# ADVANCED BIO MODULE PARAMETERS (bio/ package)
# =============================================================================
# Combined score: w1*Hydrophilicity + w2*Accessibility + w3*Flexibility
#               + w4*BetaTurn + w5*Antigenicity

BIO_SCORING_WEIGHTS = {
    # ── 11 local channels (total ≈ 0.65) ──
    "hydrophilicity": 0.06,       # Parker (1986)
    "accessibility": 0.07,        # Emini (1985)
    "flexibility": 0.06,          # Karplus & Schulz (1985)
    "beta_turn": 0.06,            # Chou & Fasman (1978)
    "antigenicity": 0.08,         # Kolaskar & Tongaonkar (1990)
    "bepipred": 0.08,             # BepiPred-1.0 (Larsen 2006)
    "coil": 0.05,                 # Levitt coil/disorder (1978)
    "welling": 0.07,              # Welling et al. (1985)
    "disorder": 0.05,             # Disorder propensity
    "aapair": 0.04,               # AA pair propensity
    "janin": 0.03,                # Janin surface exposure
    # ── 7 IEDB API channels (total ≈ 0.35) ──
    "iedb_bepipred2": 0.10,       # IEDB BepiPred-2.0 (Jespersen 2017) — strongest signal
    "iedb_bepipred1": 0.05,       # IEDB BepiPred 1.0 (HMM-based)
    "iedb_emini": 0.04,           # IEDB Emini surface accessibility
    "iedb_kolaskar": 0.04,        # IEDB Kolaskar-Tongaonkar antigenicity
    "iedb_parker": 0.04,          # IEDB Parker hydrophilicity
    "iedb_choufasman": 0.04,      # IEDB Chou-Fasman beta-turn
    "iedb_karplus": 0.04,         # IEDB Karplus-Schulz flexibility
}

BIO_WINDOW_SIZES = {
    "hydrophilicity": 7,
    "accessibility": 6,
    "flexibility": 7,
    "beta_turn": 7,
    "antigenicity": 7,
    "bepipred": 9,
    "coil": 7,
    "welling": 7,
    "smoothing": 7,
}

BIO_DETECTION_PARAMS = {
    "min_length": 7,              # Reduced: some validated epitopes are 7-8 aa
    "max_length": 30,             # Increased: some validated epitopes extend longer
    "min_score": 0.22,            # Lowered to capture more candidates before ranking
    "merge_gap": 4,               # Increased: bridge larger gaps in high-scoring regions
    "top_n": 75,                  # Increased: more candidates = better coverage
    "adaptive_threshold": True,
    "overlap_fraction": 0.75,     # Higher: allows more overlapping candidates for diversity
    "min_consensus": 0.10,        # Reduced: some real epitopes score high on fewer methods
}

# =============================================================================
# IEDB API CONFIGURATION
# =============================================================================
# The IEDB Tools API (http://tools-api.iedb.org) provides free B-cell
# epitope prediction.  BepiPred-2.0 is the state-of-the-art method.
# Set "enabled" to True and pass --iedb to the CLI to use it.

IEDB_PARAMS = {
    "enabled": False,             # Off by default; enable via --iedb flag
    "methods": [                  # All 7 free IEDB B-cell prediction methods
        "Bepipred-2.0",           # Random-forest model (strongest)
        "Bepipred",               # HMM-based (BepiPred 1.0)
        "Emini",                  # Surface accessibility
        "Kolaskar-Tongaonkar",    # Antigenicity
        "Parker",                 # Hydrophilicity
        "Chou-Fasman",            # Beta-turn propensity
        "Karplus-Schulz",         # Backbone flexibility
    ],
    "timeout": 120,               # HTTP timeout per request (seconds)
}

GUI_SETTINGS = {
    "window_title": "EpiTop1 — B Linear Epitope Predictor",
    "window_width": 1200,
    "window_height": 800,
    "bg_color": "#F5F7FA",
    "accent_color": "#2E86AB",
    "success_color": "#28A745",
    "warning_color": "#FFC107",
    "danger_color": "#DC3545",
    "font_family": "Segoe UI",
    "font_size": 10,
}
