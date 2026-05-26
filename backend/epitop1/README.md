# EpiTop1 — B Linear Epitope Predictor

A professional standalone bioinformatics tool for predicting B linear epitopes from protein sequences and PDB structures. Based exclusively on validated scientific algorithms — no external API calls.

---

## Scientific Methods

| Method | Reference | Purpose |
|--------|-----------|---------|
| **Hopp & Woods (1981)** | PNAS 78:3824-3828 | Hydrophilicity prediction |
| **Kyte & Doolittle (1982)** | J Mol Biol 157:105-132 | Hydrophobicity scale |
| **Karplus & Schulz (1985)** | Naturwissenschaften 72:212-213 | Backbone flexibility |
| **Emini et al. (1985)** | J Virol 55:836-839 | Surface accessibility |
| **Kolaskar & Tongaonkar (1990)** | FEBS Lett 276:172-174 | Antigenicity prediction |
| **Shrake & Rupley (1973)** | J Mol Biol 79:351-371 | SASA calculation (PDB) |

Additional filters from:
- Pellequer & Westhof (1993) — Empirical epitope comparison
- Saha & Raghava (2006) — B-cell epitope composition rules
- Jespersen et al. (2017) — BepiPred-2.0 methodology

## Installation

```bash
pip install -r requirements.txt
```

Requirements: Python 3.8+, NumPy, BioPython (optional, for PDB parsing).

## Usage

### GUI Mode
```bash
python main.py
```

### CLI Mode
```bash
# Direct sequence
python main.py --cli "MFVFLVLLPLVSS..." -o results/

# FASTA file
python main.py --cli sequence.fasta -o results/

# With PDB structure
python main.py --cli sequence.fasta --pdb structure.pdb -o results/

# Custom parameters
python main.py --cli sequence.fasta --min-length 15 --max-length 20 --min-score 0.6 --top-n 10 -o results/
```

## Project Structure

```
epitop1/
├── main.py                  # Entry point (GUI + CLI)
├── config.py                # All configurable parameters
├── requirements.txt
├── core/                    # Bioinformatics algorithms
│   ├── scales.py            # Amino acid property scales
│   ├── hydrophilicity.py    # Hopp & Woods (1981)
│   ├── hydrophobicity.py    # Kyte & Doolittle (1982)
│   ├── flexibility.py       # Karplus & Schulz (1985)
│   ├── accessibility.py     # Emini et al. (1985)
│   ├── antigenicity.py      # Kolaskar & Tongaonkar (1990)
│   ├── scoring.py           # Global scoring engine
│   └── epitope_selector.py  # Epitope selection & filtering
├── structure/               # PDB structural analysis
│   ├── pdb_parser.py        # PDB file parser
│   └── sasa.py              # SASA calculator (Shrake & Rupley)
├── io_utils/                # File I/O
│   ├── fasta_parser.py      # FASTA/sequence parser
│   └── exporter.py          # CSV/JSON export
└── gui/                     # Tkinter GUI
    └── app.py               # Main application window
```

## Scoring Formula

```
GLOBAL_SCORE = w1 × hydrophilicity + w2 × surface_accessibility
             + w3 × flexibility + w4 × antigenicity
             − w5 × hydrophobicity
```

All scores are min-max normalized to [0,1] before combination. Weights are configurable in `config.py`.

## Epitope Selection Criteria

1. **Length**: 12–25 amino acids
2. **Hydrophilicity**: Positive Hopp & Woods score
3. **Surface exposure**: Emini score > 1.0 and/or SASA > 0.25
4. **Residue composition**: Rich in E, D, K, R, Q, N, S; poor in L, I, V, F, W
5. **Exclusion**: Transmembrane domains, signal peptides, buried regions

## Output

- **Per-residue score table** (CSV): All bioinformatics scores for each amino acid
- **Epitope candidate list** (CSV): Ranked candidates with position, sequence, scores
- **Full report** (JSON): Complete analysis with metadata and parameters

## License

Academic and research use.
