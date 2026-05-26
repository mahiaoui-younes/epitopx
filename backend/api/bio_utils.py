"""
EpitopX AI — Python Bioinformatics Utilities
Mirrors the algorithms from the frontend dna.js / api.js so all heavy
computation runs server-side.

References:
  [1] NCBI Standard Genetic Code (Table 1)
  [2] Gasteiger et al. (2005) ExPASy ProtParam
  [3] Bjellqvist et al. (1993) pI / Lide 1994 pKa values
  [4] Kyte & Doolittle (1982) GRAVY
  [5] Pace et al. (1995) Extinction coefficient
  [6] Guruprasad et al. (1990) Instability index
  [7] Ikai (1980) Aliphatic index
  [8] Needleman & Wunsch (1970) Global alignment
"""

import math
import re

# ─────────────────────────────────────────────────────────────────────────────
# NCBI Standard Genetic Code (Table 1) — [1]
# ─────────────────────────────────────────────────────────────────────────────
CODON_TABLE = {
    'TTT': 'F', 'TTC': 'F', 'TTA': 'L', 'TTG': 'L',
    'CTT': 'L', 'CTC': 'L', 'CTA': 'L', 'CTG': 'L',
    'ATT': 'I', 'ATC': 'I', 'ATA': 'I', 'ATG': 'M',
    'GTT': 'V', 'GTC': 'V', 'GTA': 'V', 'GTG': 'V',
    'TCT': 'S', 'TCC': 'S', 'TCA': 'S', 'TCG': 'S',
    'CCT': 'P', 'CCC': 'P', 'CCA': 'P', 'CCG': 'P',
    'ACT': 'T', 'ACC': 'T', 'ACA': 'T', 'ACG': 'T',
    'GCT': 'A', 'GCC': 'A', 'GCA': 'A', 'GCG': 'A',
    'TAT': 'Y', 'TAC': 'Y', 'TAA': '*', 'TAG': '*',
    'CAT': 'H', 'CAC': 'H', 'CAA': 'Q', 'CAG': 'Q',
    'AAT': 'N', 'AAC': 'N', 'AAA': 'K', 'AAG': 'K',
    'GAT': 'D', 'GAC': 'D', 'GAA': 'E', 'GAG': 'E',
    'TGT': 'C', 'TGC': 'C', 'TGA': '*', 'TGG': 'W',
    'CGT': 'R', 'CGC': 'R', 'CGA': 'R', 'CGG': 'R',
    'AGT': 'S', 'AGC': 'S', 'AGA': 'R', 'AGG': 'R',
    'GGT': 'G', 'GGC': 'G', 'GGA': 'G', 'GGG': 'G',
}

# ─────────────────────────────────────────────────────────────────────────────
# Residue weights (ExPASy ProtParam) — [2]
# ─────────────────────────────────────────────────────────────────────────────
RESIDUE_WEIGHTS = {
    'A': 71.0788,  'R': 156.1875, 'N': 114.1038, 'D': 115.0886,
    'C': 103.1388, 'E': 129.1155, 'Q': 128.1307, 'G': 57.0519,
    'H': 137.1411, 'I': 113.1594, 'L': 113.1594, 'K': 128.1741,
    'M': 131.1926, 'F': 147.1766, 'P': 97.1167,  'S': 87.0782,
    'T': 101.1051, 'W': 186.2132, 'Y': 163.1760, 'V': 99.1326,
}

# ─────────────────────────────────────────────────────────────────────────────
# pKa values (Lide 1994) — [3]
# ─────────────────────────────────────────────────────────────────────────────
PKA = {
    'Nterm': 9.60, 'Cterm': 2.34,
    'D': 3.86, 'E': 4.25, 'H': 6.04,
    'C': 8.33, 'Y': 10.46, 'K': 10.54, 'R': 12.48,
}

# ─────────────────────────────────────────────────────────────────────────────
# Kyte-Doolittle hydrophobicity scale — [4]
# ─────────────────────────────────────────────────────────────────────────────
HYDROPHOBICITY = {
    'A': 1.8,  'R': -4.5, 'N': -3.5, 'D': -3.5, 'C': 2.5,
    'E': -3.5, 'Q': -3.5, 'G': -0.4, 'H': -3.2, 'I': 4.5,
    'L': 3.8,  'K': -3.9, 'M': 1.9,  'F': 2.8,  'P': -1.6,
    'S': -0.8, 'T': -0.7, 'W': -0.9, 'Y': -1.3, 'V': 4.2,
}

# ─────────────────────────────────────────────────────────────────────────────
# Guruprasad instability DIWV matrix — [6]
# ─────────────────────────────────────────────────────────────────────────────
INSTABILITY_MATRIX = {
    'AA': 1.0,  'AC': 44.94, 'AD': -7.49, 'AE': 1.0,   'AF': 1.0,   'AG': 1.0,   'AH': -7.49,
    'AI': 1.0,  'AK': 1.0,   'AL': 1.0,   'AM': 1.0,   'AN': 1.0,   'AP': 20.26, 'AQ': 1.0,
    'AR': 1.0,  'AS': 1.0,   'AT': 1.0,   'AV': 1.0,   'AW': 1.0,   'AY': 1.0,
    'CA': 1.0,  'CC': 1.0,   'CD': 20.26, 'CE': 1.0,   'CF': 1.0,   'CG': 1.0,   'CH': 33.60,
    'CI': 1.0,  'CK': 1.0,   'CL': 20.26, 'CM': 33.60, 'CN': 1.0,   'CP': 20.26, 'CQ': -6.54,
    'CR': 1.0,  'CS': 1.0,   'CT': 33.60, 'CV': -6.54, 'CW': 24.68, 'CY': 1.0,
    'DA': 1.0,  'DC': 1.0,   'DD': 1.0,   'DE': 1.0,   'DF': -6.54, 'DG': 1.0,   'DH': 1.0,
    'DI': 1.0,  'DK': -7.49, 'DL': 1.0,   'DM': 1.0,   'DN': 1.0,   'DP': 1.0,   'DQ': 1.0,
    'DR': -6.54,'DS': 20.26, 'DT': -14.03,'DV': 1.0,   'DW': 1.0,   'DY': 1.0,
    'EA': 1.0,  'EC': 44.94, 'ED': 20.26, 'EE': 33.60, 'EF': 1.0,   'EG': 1.0,   'EH': -6.54,
    'EI': 20.26,'EK': 1.0,   'EL': 1.0,   'EM': 1.0,   'EN': 1.0,   'EP': 20.26, 'EQ': 20.26,
    'ER': 1.0,  'ES': 20.26, 'ET': 1.0,   'EV': 1.0,   'EW': -14.03,'EY': 1.0,
    'FA': 1.0,  'FC': 1.0,   'FD': 13.34, 'FE': 1.0,   'FF': 1.0,   'FG': 1.0,   'FH': 1.0,
    'FI': 1.0,  'FK': -14.03,'FL': 1.0,   'FM': 1.0,   'FN': 1.0,   'FP': 20.26, 'FQ': 1.0,
    'FR': 1.0,  'FS': 1.0,   'FT': 1.0,   'FV': 1.0,   'FW': 1.0,   'FY': 33.60,
    'GA': -7.49,'GC': 1.0,   'GD': 1.0,   'GE': 1.0,   'GF': 1.0,   'GG': 13.34, 'GH': 1.0,
    'GI': -7.49,'GK': 1.0,   'GL': 1.0,   'GM': 1.0,   'GN': -7.49, 'GP': 1.0,   'GQ': 1.0,
    'GR': 1.0,  'GS': 1.0,   'GT': -7.49, 'GV': 1.0,   'GW': 13.34, 'GY': -7.49,
    'HA': 1.0,  'HC': 1.0,   'HD': 1.0,   'HE': 1.0,   'HF': -9.37, 'HG': -9.37, 'HH': 1.0,
    'HI': 44.94,'HK': 24.68, 'HL': 1.0,   'HM': 1.0,   'HN': 24.68, 'HP': -1.88, 'HQ': 1.0,
    'HR': 1.0,  'HS': 1.0,   'HT': -6.54, 'HV': 1.0,   'HW': -1.88, 'HY': 44.94,
    'IA': 1.0,  'IC': 1.0,   'ID': 1.0,   'IE': 44.94, 'IF': 1.0,   'IG': 1.0,   'IH': 13.34,
    'II': 1.0,  'IK': -7.49, 'IL': 20.26, 'IM': 1.0,   'IN': 1.0,   'IP': -1.88, 'IQ': 1.0,
    'IR': 1.0,  'IS': 1.0,   'IT': 1.0,   'IV': -7.49, 'IW': 1.0,   'IY': 1.0,
    'KA': 1.0,  'KC': 1.0,   'KD': 1.0,   'KE': 1.0,   'KF': 1.0,   'KG': -7.49, 'KH': 1.0,
    'KI': -7.49,'KK': 1.0,   'KL': -7.49, 'KM': 33.60, 'KN': 1.0,   'KP': -6.54, 'KQ': 24.68,
    'KR': 33.60,'KS': 1.0,   'KT': 1.0,   'KV': -7.49, 'KW': 1.0,   'KY': 1.0,
    'LA': 1.0,  'LC': 1.0,   'LD': 1.0,   'LE': 1.0,   'LF': 1.0,   'LG': 1.0,   'LH': 1.0,
    'LI': 1.0,  'LK': -7.49, 'LL': 1.0,   'LM': 1.0,   'LN': 1.0,   'LP': 20.26, 'LQ': 33.60,
    'LR': 20.26,'LS': 1.0,   'LT': 1.0,   'LV': 1.0,   'LW': 24.68, 'LY': 1.0,
    'MA': 13.34,'MC': 1.0,   'MD': 1.0,   'ME': 1.0,   'MF': 1.0,   'MG': 1.0,   'MH': 58.28,
    'MI': 1.0,  'MK': 1.0,   'ML': 1.0,   'MM': -1.88, 'MN': 1.0,   'MP': 44.94, 'MQ': -6.54,
    'MR': -6.54,'MS': 44.94, 'MT': -1.88, 'MV': 1.0,   'MW': 1.0,   'MY': 24.68,
    'NA': 1.0,  'NC': -1.88, 'ND': 1.0,   'NE': 1.0,   'NF': -14.03,'NG': -14.03,'NH': 1.0,
    'NI': 44.94,'NK': 24.68, 'NL': 1.0,   'NM': 1.0,   'NN': 1.0,   'NP': -1.88, 'NQ': -6.54,
    'NR': 1.0,  'NS': 1.0,   'NT': -7.49, 'NV': 1.0,   'NW': -9.37, 'NY': 1.0,
    'PA': 20.26,'PC': -6.54, 'PD': -6.54, 'PE': 18.38, 'PF': 20.26, 'PG': 1.0,   'PH': 1.0,
    'PI': 1.0,  'PK': 1.0,   'PL': 1.0,   'PM': -6.54, 'PN': 1.0,   'PP': 20.26, 'PQ': 20.26,
    'PR': -6.54,'PS': 20.26, 'PT': 1.0,   'PV': 20.26, 'PW': -1.88, 'PY': 1.0,
    'QA': 1.0,  'QC': -6.54, 'QD': 20.26, 'QE': 20.26, 'QF': -6.54, 'QG': 1.0,   'QH': 1.0,
    'QI': 1.0,  'QK': 1.0,   'QL': 1.0,   'QM': 1.0,   'QN': 1.0,   'QP': 20.26, 'QQ': 20.26,
    'QR': 1.0,  'QS': 44.94, 'QT': 1.0,   'QV': -6.54, 'QW': 1.0,   'QY': -6.54,
    'RA': 1.0,  'RC': 1.0,   'RD': 1.0,   'RE': 1.0,   'RF': 1.0,   'RG': -7.49, 'RH': 20.26,
    'RI': 1.0,  'RK': 1.0,   'RL': 1.0,   'RM': 1.0,   'RN': 13.34, 'RP': 20.26, 'RQ': 20.26,
    'RR': 1.0,  'RS': 44.94, 'RT': 1.0,   'RV': 1.0,   'RW': 58.28, 'RY': -6.54,
    'SA': 1.0,  'SC': 33.60, 'SD': 1.0,   'SE': 20.26, 'SF': 1.0,   'SG': 1.0,   'SH': 1.0,
    'SI': 1.0,  'SK': 1.0,   'SL': 1.0,   'SM': 1.0,   'SN': 1.0,   'SP': 44.94, 'SQ': 20.26,
    'SR': 20.26,'SS': 20.26, 'ST': 1.0,   'SV': 1.0,   'SW': 1.0,   'SY': 1.0,
    'TA': 1.0,  'TC': 1.0,   'TD': 1.0,   'TE': 20.26, 'TF': 13.34, 'TG': -7.49, 'TH': 1.0,
    'TI': 1.0,  'TK': 1.0,   'TL': 1.0,   'TM': 1.0,   'TN': -14.03,'TP': 1.0,   'TQ': -6.54,
    'TR': 1.0,  'TS': 1.0,   'TT': 1.0,   'TV': 1.0,   'TW': -14.03,'TY': 1.0,
    'VA': 1.0,  'VC': 1.0,   'VD': -14.03,'VE': 1.0,   'VF': 1.0,   'VG': -7.49, 'VH': 1.0,
    'VI': 1.0,  'VK': -1.88, 'VL': 1.0,   'VM': 1.0,   'VN': 1.0,   'VP': 20.26, 'VQ': 1.0,
    'VR': 1.0,  'VS': 1.0,   'VT': -7.49, 'VV': 1.0,   'VW': 1.0,   'VY': 1.0,
    'WA': -14.03,'WC': 1.0,  'WD': 1.0,   'WE': 1.0,   'WF': 1.0,   'WG': -9.37, 'WH': 24.68,
    'WI': 1.0,  'WK': 1.0,   'WL': 13.34, 'WM': 24.68, 'WN': -9.37, 'WP': 1.0,   'WQ': 1.0,
    'WR': 1.0,  'WS': 1.0,   'WT': -14.03,'WV': -7.49, 'WW': 1.0,   'WY': 1.0,
    'YA': 24.68,'YC': 1.0,   'YD': 24.68, 'YE': 1.0,   'YF': 1.0,   'YG': -7.49, 'YH': 13.34,
    'YI': 1.0,  'YK': 1.0,   'YL': 1.0,   'YM': 44.94, 'YN': 1.0,   'YP': 13.34, 'YQ': 1.0,
    'YR': -15.91,'YS': 1.0,  'YT': -7.49, 'YV': 1.0,   'YW': -9.37, 'YY': 13.34,
}

VALID_DNA = set('ATGC')
VALID_AA  = set('ACDEFGHIKLMNPQRSTVWY*')


# ─────────────────────────────────────────────────────────────────────────────
# Sequence utilities
# ─────────────────────────────────────────────────────────────────────────────

def clean_sequence(raw: str) -> str:
    """Remove FASTA header lines, whitespace, digits, and uppercase."""
    lines = raw.strip().splitlines()
    parts = [l for l in lines if not l.startswith('>')]
    return re.sub(r'[\s\d\-\.]', '', ''.join(parts)).upper()


def reverse_complement(dna: str) -> str:
    comp = {'A': 'T', 'T': 'A', 'G': 'C', 'C': 'G'}
    return ''.join(comp.get(b, 'N') for b in reversed(dna))


def compute_gc(dna: str) -> float:
    if not dna:
        return 0.0
    gc = sum(1 for b in dna if b in ('G', 'C'))
    return round(gc / len(dna) * 100, 1)


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def validate_dna(seq: str) -> dict:
    errors = []
    if not seq:
        return {'valid': False, 'errors': ['The DNA sequence is empty.']}
    bad = sorted({c for c in seq if c not in VALID_DNA})
    if bad:
        errors.append(
            f"Invalid nucleotide(s): {', '.join(bad)}. Only A, T, G, C accepted."
        )
    if len(seq) < 3:
        errors.append('Sequence must contain at least 3 nucleotides.')
    if len(seq) % 3 != 0:
        errors.append(
            f"Sequence length ({len(seq)} nt) is not a multiple of 3 — "
            f"{len(seq) % 3} trailing nucleotide(s) will be ignored."
        )
    return {'valid': len(errors) == 0, 'errors': errors}


# ─────────────────────────────────────────────────────────────────────────────
# ORF detection & translation  — [1]
# ─────────────────────────────────────────────────────────────────────────────

def _translate_from(dna: str, start: int) -> dict:
    aas = []
    stop_codon = None
    i = start
    while i + 2 < len(dna):
        codon = dna[i:i + 3]
        aa = CODON_TABLE.get(codon)
        if aa is None:
            aas.append('X')
        elif aa == '*':
            stop_codon = codon
            i += 3
            break
        else:
            aas.append(aa)
        i += 3
    return {'protein': ''.join(aas), 'stop_codon': stop_codon, 'end_pos': i}


def find_best_orf(dna: str) -> dict:
    orfs = []
    rc = reverse_complement(dna)

    for strand, seq in (('+', dna), ('-', rc)):
        for frame in range(3):
            i = frame
            while i + 2 < len(seq):
                if seq[i:i + 3] == 'ATG':
                    r = _translate_from(seq, i)
                    if r['protein']:
                        orfs.append({
                            'frame': (frame + 1) if strand == '+' else -(frame + 1),
                            'strand': strand,
                            'start_pos': i,
                            'end_pos': r['end_pos'],
                            'protein': r['protein'],
                            'stop_codon': r['stop_codon'],
                            'has_stop': r['stop_codon'] is not None,
                        })
                i += 3

    if not orfs:
        r = _translate_from(dna, 0)
        return {
            'frame': 1, 'strand': '+', 'start_pos': 0, 'end_pos': len(dna),
            'protein': r['protein'], 'stop_codon': r['stop_codon'],
            'has_stop': r['stop_codon'] is not None,
            'no_atg': True, 'all_orfs': [],
        }

    complete = [o for o in orfs if o['has_stop']]
    pool = complete or orfs
    best = max(pool, key=lambda o: len(o['protein']))
    best['all_orfs'] = orfs
    best['no_atg'] = False
    return best


def translate_dna(raw: str) -> dict:
    """
    Translate a DNA sequence (FASTA or raw) to protein.
    Returns translation result + protein physicochemical stats.
    """
    clean = clean_sequence(raw)
    val = validate_dna(clean)

    hard_errors = [e for e in val['errors']
                   if 'trailing' not in e and 'multiple' not in e]
    if hard_errors and len(clean) < 3:
        return {
            'protein': '', 'length': 0, 'dna_length': len(clean),
            'codons': 0, 'warnings': val['errors'],
            'error': hard_errors[0],
        }

    gc_content = compute_gc(clean)
    orf = find_best_orf(clean)
    protein = orf['protein']

    all_frames = [
        {
            'frame': o['frame'],
            'start': o['start_pos'] + 1,
            'length': len(o['protein']),
            'has_stop': o['has_stop'],
            'preview': o['protein'][:20] + ('…' if len(o['protein']) > 20 else ''),
        }
        for o in orf.get('all_orfs', [])
    ]

    warnings = []
    if orf.get('no_atg'):
        warnings.append('No ATG start codon found — raw frame-1 translation shown.')
    if not orf['has_stop']:
        warnings.append('No stop codon encountered before the end of the sequence.')
    if len(clean) < 100:
        warnings.append('Sequence is shorter than 100 nt — likely a fragment.')
    warnings += [e for e in val['errors'] if 'trailing' in e]

    orf_codons = len(protein) + (1 if orf['has_stop'] else 0)
    orf_nt     = orf_codons * 3
    orf_end    = orf['start_pos'] + orf_nt

    gc_orf = (compute_gc(clean[orf['start_pos']:orf_end])
              if not orf.get('no_atg') and orf_nt > 0 and orf_end <= len(clean)
              else gc_content)

    result = {
        'protein':    protein,
        'length':     len(protein),
        'dna_length': len(clean),
        'orf_codons': orf_codons,
        'orf_nt':     orf_nt,
        'codons':     orf_codons,
        'orf_start':  orf['start_pos'] + 1,
        'orf_end':    orf_end,
        'orf_frame':  orf['frame'],
        'has_stop':   orf['has_stop'],
        'stop_codon': orf['stop_codon'],
        'gc_content': gc_content,
        'gc_orf':     gc_orf,
        'is_fragment': len(clean) < 100,
        'all_frames': all_frames,
        'warnings':   warnings,
    }

    if protein:
        result['stats'] = protein_stats(protein)

    return result


def translate_all_six_frames(raw: str) -> list:
    """Return translation in all 6 reading frames (for display)."""
    clean = clean_sequence(raw)
    rc    = reverse_complement(clean)
    frames = []
    for strand, seq in (('+', clean), ('-', rc)):
        for frame in range(3):
            r = _translate_from(seq, frame)
            label = f"{'+' if strand == '+' else '-'}{frame + 1}"
            frames.append({
                'label':      label,
                'frame':      (frame + 1) if strand == '+' else -(frame + 1),
                'strand':     strand,
                'protein':    r['protein'],
                'length':     len(r['protein']),
                'has_stop':   r['stop_codon'] is not None,
                'stop_codon': r['stop_codon'],
            })
    return frames


# ─────────────────────────────────────────────────────────────────────────────
# Protein physicochemical properties — [2–7]
# ─────────────────────────────────────────────────────────────────────────────

def compute_mw(seq: str) -> float:
    mw = 18.02
    for aa in seq:
        mw += RESIDUE_WEIGHTS.get(aa, 111.1)
    return mw


def compute_pi(seq: str) -> float | None:
    if not seq:
        return None

    def count(aa):
        return seq.count(aa)

    nD, nE, nH = count('D'), count('E'), count('H')
    nC, nY, nK, nR = count('C'), count('Y'), count('K'), count('R')

    def charge(pH):
        def f(pK, n, sign):
            return sign * n / (1 + 10 ** (sign * (pH - pK)))
        return (
            f(PKA['Nterm'], 1, 1) +
            f(PKA['K'], nK, 1) +
            f(PKA['R'], nR, 1) +
            f(PKA['H'], nH, 1) +
            f(PKA['D'], nD, -1) +
            f(PKA['E'], nE, -1) +
            f(PKA['C'], nC, -1) +
            f(PKA['Y'], nY, -1) +
            f(PKA['Cterm'], 1, -1)
        )

    lo, hi = 0.0, 14.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if charge(mid) > 0:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 2)


def compute_gravy(seq: str) -> float | None:
    if not seq:
        return None
    total = sum(HYDROPHOBICITY.get(aa, 0) for aa in seq)
    return round(total / len(seq), 3)


def compute_extinction(seq: str) -> int:
    nW = seq.count('W')
    nY = seq.count('Y')
    nC = seq.count('C')
    return nW * 5500 + nY * 1490 + nC * 125


def compute_instability(seq: str) -> float | None:
    if not seq or len(seq) < 2:
        return None
    total = sum(INSTABILITY_MATRIX.get(seq[i] + seq[i + 1], 0)
                for i in range(len(seq) - 1))
    return round((10 / len(seq)) * total, 2)


def compute_aliphatic(seq: str) -> float | None:
    if not seq:
        return None
    n = len(seq)
    nA = seq.count('A') / n * 100
    nV = seq.count('V') / n * 100
    nI = seq.count('I') / n * 100
    nL = seq.count('L') / n * 100
    return round(nA + 2.9 * nV + 3.9 * (nI + nL), 2)


def protein_stats(seq: str) -> dict:
    """Comprehensive physicochemical properties of an amino-acid sequence."""
    if not seq:
        return {}

    composition = {}
    for aa in seq:
        composition[aa] = composition.get(aa, 0) + 1

    aa_class = {
        'A': 'nonpolar', 'V': 'nonpolar', 'I': 'nonpolar', 'L': 'nonpolar',
        'M': 'nonpolar', 'F': 'nonpolar', 'W': 'nonpolar', 'P': 'nonpolar',
        'G': 'nonpolar',
        'S': 'polar', 'T': 'polar', 'C': 'polar', 'Y': 'polar',
        'N': 'polar', 'Q': 'polar',
        'D': 'negative', 'E': 'negative',
        'K': 'positive', 'R': 'positive', 'H': 'positive',
    }
    class_count = {'nonpolar': 0, 'polar': 0, 'positive': 0, 'negative': 0}
    for aa in seq:
        cls = aa_class.get(aa)
        if cls:
            class_count[cls] += 1

    mw         = compute_mw(seq)
    pi         = compute_pi(seq)
    gravy      = compute_gravy(seq)
    extinction = compute_extinction(seq)
    instability = compute_instability(seq)
    aliphatic  = compute_aliphatic(seq)
    abs_01     = round(extinction / mw, 3) if extinction and mw else None

    return {
        'length':                  len(seq),
        'molecular_weight':        round(mw, 4),
        'molecular_weight_kda':    round(mw / 1000, 2),
        'pI':                      pi,
        'gravy':                   gravy,
        'extinction_coefficient':  extinction,
        'abs_01pct':               abs_01,
        'instability_index':       instability,
        'is_stable':               (instability < 40) if instability is not None else None,
        'aliphatic_index':         aliphatic,
        'composition':             composition,
        'class_composition':       class_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Needleman-Wunsch global alignment — [8]
# ─────────────────────────────────────────────────────────────────────────────

def nw_align(seq_a: str, seq_b: str,
             match: int = 1, mismatch: int = -1, gap: int = -2) -> dict:
    m, n = len(seq_a), len(seq_b)

    # Build DP matrix
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1):
        dp[i][0] = i * gap
    for j in range(n + 1):
        dp[0][j] = j * gap

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            diag = dp[i - 1][j - 1] + (match if seq_a[i - 1] == seq_b[j - 1] else mismatch)
            up   = dp[i - 1][j] + gap
            left = dp[i][j - 1] + gap
            dp[i][j] = max(diag, up, left)

    # Traceback
    align_a, align_b = [], []
    i, j = m, n
    while i > 0 and j > 0:
        s = dp[i][j]
        if s == dp[i - 1][j - 1] + (match if seq_a[i - 1] == seq_b[j - 1] else mismatch):
            align_a.append(seq_a[i - 1])
            align_b.append(seq_b[j - 1])
            i -= 1; j -= 1
        elif s == dp[i - 1][j] + gap:
            align_a.append(seq_a[i - 1])
            align_b.append('-')
            i -= 1
        else:
            align_a.append('-')
            align_b.append(seq_b[j - 1])
            j -= 1
    while i > 0:
        align_a.append(seq_a[i - 1]); align_b.append('-'); i -= 1
    while j > 0:
        align_a.append('-'); align_b.append(seq_b[j - 1]); j -= 1

    align_a = ''.join(reversed(align_a))
    align_b = ''.join(reversed(align_b))

    return {'align_a': align_a, 'align_b': align_b, 'score': dp[m][n]}


def compute_similarity(seq1: str, seq2: str) -> dict:
    """
    Needleman-Wunsch-based pairwise similarity.
    Returns identity %, matches, gaps, estimated RMSD, and per-column alignment.
    """
    r = nw_align(seq1, seq2)
    align_a, align_b = r['align_a'], r['align_b']
    align_len = len(align_a)

    matches = gaps = 0
    alignment = []
    for pos, (a, b) in enumerate(zip(align_a, align_b), 1):
        is_gap   = (a == '-' or b == '-')
        is_match = not is_gap and a == b
        if is_match: matches += 1
        if is_gap:   gaps    += 1
        alignment.append({'position': pos, 'aa1': a, 'aa2': b, 'match': is_match})

    identity = (matches / align_len * 100) if align_len else 0.0
    id_frac  = identity / 100
    estimated_rmsd = (max(0.3, 1.5 * math.exp(-1.87 * id_frac))
                      if id_frac > 0 else 10.0)

    return {
        'identity':      round(identity, 1),
        'matches':       matches,
        'total':         align_len,
        'rmsd':          round(estimated_rmsd, 2),
        'rmsd_estimated': True,
        'alignment':     alignment,
        'gaps':          gaps,
        'score':         r['score'],
    }
