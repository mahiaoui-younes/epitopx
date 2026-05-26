#!/usr/bin/env python3
"""
Comprehensive protein epitope prediction benchmark.

Tests the EpiTop1 prediction pipeline (both core and bio modules)
against a panel of well-characterised proteins with experimentally
validated B-cell linear epitopes sourced from IEDB and the literature.

Proteins tested
---------------
 1. Theileria annulata TaSP (CAC87893.1)
 2. SARS-CoV-2 Spike receptor-binding domain (RBD)
 3. HIV-1 gp41 ectodomain (MPER region)
 4. Influenza A H3N2 Hemagglutinin (HA1 fragment)
 5. Plasmodium falciparum CSP (repeat region)
 6. Hepatitis B Surface Antigen (major hydrophilic region)
 7. Dengue-2 Envelope protein (domain III)
 8. Mycobacterium tuberculosis ESAT-6
 9. Human beta-2 microglobulin
10. Tetanus toxin C-fragment

Each entry supplies the full protein sequence and one or more
experimentally validated epitope peptides.  The test measures:
  • Whether the known epitope region is detected (≥50 % overlap)
  • In which rank position it appears (top-5, top-10, top-20)
  • Overall sensitivity across the full panel

Usage:
    python test_proteins.py
"""

from __future__ import annotations

import sys
import os
import textwrap
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

# Ensure project root is importable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from core.scoring import GlobalScorer
from core.epitope_selector import EpitopeSelector
from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector


# ─────────────────────────────────────────────────────────────────────────────
# Test protein database
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TestProtein:
    """A protein with known epitopes for benchmarking."""
    name: str
    accession: str
    sequence: str
    known_epitopes: List[str]   # peptide sequences
    description: str = ""


PROTEINS: list[TestProtein] = [
    # ── 1. Theileria annulata TaSP ──────────────────────────────────
    TestProtein(
        name="Theileria annulata TaSP",
        accession="CAC87893.1",
        description="Theileria annulata surface protein — experimentally "
                    "validated epitope in the hydrophilic repeat region.",
        sequence=(
            "MANKVISFLLAFIFSQSAADNCSEENQDSQESLVTSVENNHSEEMQEESRVVSETEHNKTP"
            "TSVHQEEDHNEESIHQPEELQPETVTVEVPEPVTSEEPKESDQTEEQKHEEPEASPAPEPV"
            "DEPAVHAQEDEGEDDEVTPEFEDDMKPADLLKKTNDQTESQPVSEENHTKEEKPEKGPKDE"
            "NKASHTATKVEEEENVEETEKPVQGDDDENKDEETKEEIDQADTSIHGETKPEDQGDNEKPV"
            "KAEEETPEEFQGSVIAILLAFTIGFLITKKRKVFVK"
        ),
        known_epitopes=[
            "SEEPKESDQTEEQKHEEPEASPAPEPVDEPAVHA",
        ],
    ),

    # ── 2. SARS-CoV-2 Spike RBD ────────────────────────────────────
    TestProtein(
        name="SARS-CoV-2 Spike RBD",
        accession="P0DTC2 (319-541)",
        description="Receptor-binding domain of SARS-CoV-2 Spike protein. "
                    "Epitopes from convalescent sera mapping (IEDB).",
        sequence=(
            "RVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKC"
            "YGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNN"
            "LDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTN"
            "GVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNF"
        ),
        known_epitopes=[
            "YAWNRKRISNCVADY",       # IEDB epitope ID 1309634
            "GDEVRQIAPGQTGKI",       # IEDB epitope ID 1310019
            "LFRKSNLKPFERDIS",       # IEDB epitope ID 1309875
            "SYGFQPTNGVGYQPY",       # IEDB epitope ID 1310133
        ],
    ),

    # ── 3. HIV-1 gp41 ectodomain (MPER) ────────────────────────────
    TestProtein(
        name="HIV-1 gp41 MPER",
        accession="P04578 (fragment)",
        description="Membrane-proximal external region of HIV-1 gp41. "
                    "Contains the 2F5 and 4E10 broadly neutralising Ab epitopes.",
        sequence=(
            "AVGIGALFLGFLGAAGSTMGAASMTLTVQARQLLSGIVQQQNNLLRAIEAQQHLLQLTVW"
            "GIKQLQARILAVERYLKDQQLLGIWGCSGKLICTTAVPWNASWSNKSLEQIWNHTTWMEW"
            "DREINNYTSLIHSLIEESQNQQEKNEQELLELDKWASLWNWFNITNWLWYIK"
        ),
        known_epitopes=[
            "ELDKWASLWNWF",          # 2F5 epitope
            "NWFNITNWLWYIK",         # 4E10 epitope
            "NEQELLELDKWASLW",       # extended 2F5 region
        ],
    ),

    # ── 4. Influenza A H3N2 HA1 ────────────────────────────────────
    TestProtein(
        name="Influenza H3N2 HA1",
        accession="P03435 (HA1 domain)",
        description="Hemagglutinin HA1 subunit from Influenza A/Aichi. "
                    "Antigenic sites A-E are well characterised.",
        sequence=(
            "QDLPGNDNSTATLCLGHHAVPNGTLVKTITDDQIEVTNATELVQSSSTGKICNNPHRILD"
            "GIDCTLIDALLGDPHCDVFQNETWDLFVERSKAFSNCYPYDVPDYASLRSLVASSGTLEFI"
            "TEGFTWTGVTQNGGSNACKRGPGSGFFSRLNWLTKSGSTYPVLNVTMPNNDNFDKLYING"
            "NLIAPWYAFALSRGFGSGIITSNAPMDECDAKCQTPQGAINSSLPFQNVHPVTIGECPKYV"
            "RSTKLRMVTGLRNIPSIQSRGLFGAIAGFIEGGWTGMIDGWYGYHHQNEQGSGYAADLKST"
            "QNAIDEITNKVNSVIEKMNTQFTAVGKEF"
        ),
        known_epitopes=[
            "SKAFSNCYPYDVPDY",       # Antigenic site B
            "KSGSTYPVLNVTMPN",       # Antigenic site A
            "SLPFQNVHPVTIGEC",       # Antigenic site D
            "TQNGGSNACKRGPGS",       # Antigenic site C
        ],
    ),

    # ── 5. P. falciparum CSP ───────────────────────────────────────
    TestProtein(
        name="P. falciparum CSP",
        accession="P04925 (fragment)",
        description="Circumsporozoite protein repeat + C-term region. "
                    "Contains the (NANP)n repeat and Th2R/Th3R T-cell epitopes.",
        sequence=(
            "MMRKLAILSVSSFLFVEALFQEYQCYGSSSNTRVLNELNYDNAGTNLYNELEMNYYGKQE"
            "NWYSLKKNSRSLGENDDGNNEDNEKLRKPKHKKLKQPADGNPDPNANPNVDPNANPNVDP"
            "NANPNVDPNANPNVDPNANPNVDPNANPNVDPNANPNVDPNANPNVDPNANPNVDPNANP"
            "NVDPNANPNVDPNANPNVDPNANPNVDPNANPNVDPNANPNVDPNANPNVDPNANPNVDP"
            "NANPNVDPNANPNVDPNANPNANPNANPNANPNANPNANPNKNNQGNGQGHNMPNDPNRNV"
            "DENANANSAVKNNNNEEPSDKHIKEYLNKIQNSLSTEWSPCSVTCGNGIQVRIKPGSANKP"
            "KDELDYANDIEKKICKMEKCSSVFNVVNS"
        ),
        known_epitopes=[
            "NANPNVDPNANPNVD",       # (NANP)n repeat — major B-cell epitope
            "NKNNQGNGQGHNMPN",       # Minor repeat junction
            "EWSPCSVTCGNGIQV",       # Th2R region
        ],
    ),

    # ── 6. Hepatitis B Surface Antigen ─────────────────────────────
    TestProtein(
        name="HBV Surface Antigen",
        accession="P03138",
        description="Hepatitis B virus S antigen. The 'a' determinant "
                    "(aa 124-147) is the major neutralising epitope.",
        sequence=(
            "MENITSGFLGPLLVLQAGFFLLTRILTIPQSLDSWWTSLNFLGGTTVCLGQNSQSPTSNHS"
            "PTSCPPTCPGYRWMCLRRFIIFLFILLLCLIFLLVLLDYQGMLPVCPLIPGSSTTSTGPCRT"
            "CMTTAQGTSMYPSCCCTKPSDGNCTCIPIPSSWAFGKFLWEWASARFSWLSLLVPFVQWFVG"
            "LSPTVWLSAIWMMWYWGPSLYNILSPFLPLLPIFFCLWVYI"
        ),
        known_epitopes=[
            "CRTCMTTAQGTSMYP",       # 'a' determinant core
            "STTSTGPCRTCMTTA",       # extended 'a' determinant
            "PSCCCTKPSDGNCTC",       # downstream neutralising region
        ],
    ),

    # ── 7. Dengue-2 Envelope Domain III ────────────────────────────
    TestProtein(
        name="Dengue-2 E-DIII",
        accession="P04724 (domain III)",
        description="Envelope protein domain III from Dengue virus serotype 2. "
                    "Contains the AB loop and FG loop neutralising epitopes.",
        sequence=(
            "MRCIGMSNRDFVEGVSGGSWVDIVLEHGSCVTTMAKNKPTLDFELIKTEAKQPATLRKYCIEAKL"
            "TNTTTESRCPTQGEPSLNEEQDKRFVCKHSMVDRGWGNGCGLFGKGGIVTCAMFRCKKNMEGKV"
            "VQPENLEYTIVITPHSGEEHAVGNDTGKHGKEIKITPQSSITEAELTGYGTVTMECSPRTGLDF"
            "NEMVLLQMENKAWLVHRQWFLDLPLPWLPGADTQ"
        ),
        known_epitopes=[
            "GSWVDIVLEHGSCVT",       # AB loop epitope
            "KGGIVTCAMFRCKK",        # BC loop linear epitope
            "EIKITPQSSITEAEL",       # lateral ridge epitope
        ],
    ),

    # ── 8. M. tuberculosis ESAT-6 ─────────────────────────────────
    TestProtein(
        name="M. tuberculosis ESAT-6",
        accession="P0A564",
        description="Early secreted antigenic target 6 — major TB diagnostic "
                    "antigen. Multiple linear B-cell epitopes mapped.",
        sequence=(
            "MTEQQWNFAGIEAAASAIQGNVTSIHSLLDEGKQSLTKLAAAWGGSGSEAYQGVQQKWDATA"
            "TELNNALQNLARTISEAGQAMASTEGNVTGMFA"
        ),
        known_epitopes=[
            "EAAASAIQGNVTSI",        # ESAT-6 aa 4-17 (IEDB)
            "QWNFAGIEAAASAI",        # ESAT-6 aa 1-14
            "NNALQNLARTISEA",        # ESAT-6 aa 72-85 (C-terminal)
        ],
    ),

    # ── 9. Human Beta-2 Microglobulin ──────────────────────────────
    TestProtein(
        name="Human B2M",
        accession="P61769",
        description="Beta-2 microglobulin — light chain of MHC class I. "
                    "An auto-antigen with mapped B-cell epitopes.",
        sequence=(
            "MSRSVALAVLALLSLSGLEAIQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLK"
            "NGERIEKDEHLLLEDLKTVPFSKRIVQCTWQHQRGPMRDEFIIQGLQPFR"
        ),
        known_epitopes=[
            "IQVYSRHPAENGKSN",       # Loop 1 epitope
            "SGFHPSDIEVDLLKN",       # Beta-strand epitope
        ],
    ),

    # ── 10. Tetanus Toxin C-fragment ───────────────────────────────
    TestProtein(
        name="Tetanus Toxin C-frag",
        accession="P04958 (fragment)",
        description="C-terminal fragment of tetanus toxin heavy chain. "
                    "Contains well-studied B-cell epitopes.",
        sequence=(
            "DVDNALNEILEQNKAIIEQEIENLNNEIESEIYPYIGALKYIDKESKDKEIIPNIKDLKE"
            "LDQNKENIYLEIYNKEFTLNIDKKSASMYEQALNHIKDIKNDGINAGSYSKLTSKDKEL"
            "KPDINPYLSFTDRFDFIDPLNIIEYKMSNKYKNIDQIFEVKQFYDQNINKISAFENNKLY"
            "PNFDAYNAKMIGLYVKKINQEKLENMKFQIEINKINNYKFKNEDNPIDHTTSLILHGQKDL"
            "STFNLIDY"
        ),
        known_epitopes=[
            "QNKAIIEQEIENLN",        # TT 947-960 (IEDB 54391)
            "KEFTLNIDKKSASM",        # TT 1064-1077
            "NAKMIGLYVKKINQ",        # TT 1151-1164
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_epitope_in_sequence(
    sequence: str, epitope: str,
) -> Tuple[int, int]:
    """Return 1-indexed (start, end) of epitope in sequence, or (0, 0)."""
    seq = sequence.upper()
    epi = epitope.upper()
    pos = seq.find(epi)
    if pos < 0:
        return (0, 0)
    return (pos + 1, pos + len(epi))


def overlap_fraction(
    pred_start: int, pred_end: int,
    known_start: int, known_end: int,
) -> float:
    """Fraction of known epitope covered by prediction."""
    if known_start == 0 or known_end == 0:
        return 0.0
    known_set = set(range(known_start, known_end + 1))
    pred_set = set(range(pred_start, pred_end + 1))
    if not known_set:
        return 0.0
    return len(known_set & pred_set) / len(known_set)


# ─────────────────────────────────────────────────────────────────────────────
# Run benchmarks
# ─────────────────────────────────────────────────────────────────────────────

def run_benchmark():
    """Run all protein benchmarks and print summary."""
    print("=" * 100)
    print("  EpiTop1 — COMPREHENSIVE PROTEIN EPITOPE PREDICTION BENCHMARK")
    print("=" * 100)
    print()

    # Track global stats
    total_known = 0
    core_detected = 0
    bio_detected = 0
    core_top5 = 0
    bio_top5 = 0
    core_top10 = 0
    bio_top10 = 0

    protein_results = []

    for prot in PROTEINS:
        seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
        print("-" * 100)
        print(f"  {prot.name} ({prot.accession})")
        print(f"  {prot.description}")
        print(f"  Sequence length: {len(seq)} aa")
        print(f"  Known epitopes: {len(prot.known_epitopes)}")
        print()

        # ── Core module ──
        core_scorer = GlobalScorer()
        core_residues = core_scorer.get_residue_scores(seq)
        core_selector = EpitopeSelector()
        core_epitopes = core_selector.find_epitopes(seq, core_residues)

        # ── Bio module ──
        bio_scorer = CombinedScorer()
        bio_results = bio_scorer.get_residue_results(seq)
        bio_detector = EpitopeDetector({"min_length": 8, "max_length": 25, "top_n": 20})
        bio_hits = bio_detector.detect(seq, bio_results)

        prot_core_detected = 0
        prot_bio_detected = 0
        prot_core_top5 = 0
        prot_bio_top5 = 0
        prot_core_top10 = 0
        prot_bio_top10 = 0

        for epi_seq in prot.known_epitopes:
            total_known += 1
            k_start, k_end = find_epitope_in_sequence(seq, epi_seq)

            if k_start == 0:
                print(f"  WARNING: epitope '{epi_seq}' not found in sequence!")
                continue

            # Check core predictions
            best_core_overlap = 0.0
            best_core_rank = 999
            for ep in core_epitopes:
                ov = overlap_fraction(ep.start, ep.end, k_start, k_end)
                if ov > best_core_overlap:
                    best_core_overlap = ov
                    best_core_rank = ep.rank

            core_hit = best_core_overlap >= 0.50
            if core_hit:
                core_detected += 1
                prot_core_detected += 1
                if best_core_rank <= 5:
                    core_top5 += 1
                    prot_core_top5 += 1
                if best_core_rank <= 10:
                    core_top10 += 1
                    prot_core_top10 += 1

            # Check bio predictions
            best_bio_overlap = 0.0
            best_bio_rank = 999
            for h in bio_hits:
                ov = overlap_fraction(h.start, h.end, k_start, k_end)
                if ov > best_bio_overlap:
                    best_bio_overlap = ov
                    best_bio_rank = h.rank

            bio_hit = best_bio_overlap >= 0.50
            if bio_hit:
                bio_detected += 1
                prot_bio_detected += 1
                if best_bio_rank <= 5:
                    bio_top5 += 1
                    prot_bio_top5 += 1
                if best_bio_rank <= 10:
                    bio_top10 += 1
                    prot_bio_top10 += 1

            status_core = (
                f"DETECTED (rank {best_core_rank}, {best_core_overlap:.0%})"
                if core_hit else f"missed ({best_core_overlap:.0%})"
            )
            status_bio = (
                f"DETECTED (rank {best_bio_rank}, {best_bio_overlap:.0%})"
                if bio_hit else f"missed ({best_bio_overlap:.0%})"
            )

            print(f"  Epitope: {epi_seq[:40]:<40s} pos {k_start}-{k_end}")
            print(f"    Core: {status_core}")
            print(f"    Bio:  {status_bio}")

        # Print predictions for this protein
        print()
        if core_epitopes:
            print(f"  Core predictions (top 5 of {len(core_epitopes)}):")
            for ep in core_epitopes[:5]:
                print(f"    #{ep.rank:>2}: pos {ep.start:>3}-{ep.end:<3} "
                      f"score={ep.global_score:.4f} {ep.sequence[:35]}")
        if bio_hits:
            print(f"  Bio predictions (top 5 of {len(bio_hits)}):")
            for h in bio_hits[:5]:
                print(f"    #{h.rank:>2}: pos {h.start:>3}-{h.end:<3} "
                      f"score={h.combined_score:.4f} "
                      f"consensus={h.consensus_score:.2f} {h.sequence[:35]}")

        protein_results.append({
            "name": prot.name,
            "n_known": len(prot.known_epitopes),
            "core_detected": prot_core_detected,
            "bio_detected": prot_bio_detected,
            "core_top5": prot_core_top5,
            "bio_top5": prot_bio_top5,
        })
        print()

    # ── Summary ──
    print("=" * 100)
    print("  BENCHMARK SUMMARY")
    print("=" * 100)
    print()
    print(f"  {'Protein':<30s} {'Known':>6} {'Core Det':>10} {'Bio Det':>10} "
          f"{'Core Top5':>10} {'Bio Top5':>10}")
    print("  " + "-" * 90)
    for r in protein_results:
        print(f"  {r['name']:<30s} {r['n_known']:>6} "
              f"{r['core_detected']:>10} {r['bio_detected']:>10} "
              f"{r['core_top5']:>10} {r['bio_top5']:>10}")
    print("  " + "-" * 90)
    print(f"  {'TOTAL':<30s} {total_known:>6} "
          f"{core_detected:>10} {bio_detected:>10} "
          f"{core_top5:>10} {bio_top5:>10}")
    print()
    core_sensitivity = core_detected / total_known * 100 if total_known else 0
    bio_sensitivity = bio_detected / total_known * 100 if total_known else 0
    print(f"  Core module sensitivity:  {core_detected}/{total_known} "
          f"({core_sensitivity:.1f}%)")
    print(f"  Bio module sensitivity:   {bio_detected}/{total_known} "
          f"({bio_sensitivity:.1f}%)")
    print()
    print(f"  Core Top-5 rate:  {core_top5}/{total_known} "
          f"({core_top5/total_known*100:.1f}%)" if total_known else "")
    print(f"  Bio  Top-5 rate:  {bio_top5}/{total_known} "
          f"({bio_top5/total_known*100:.1f}%)" if total_known else "")
    print(f"  Core Top-10 rate: {core_top10}/{total_known} "
          f"({core_top10/total_known*100:.1f}%)" if total_known else "")
    print(f"  Bio  Top-10 rate: {bio_top10}/{total_known} "
          f"({bio_top10/total_known*100:.1f}%)" if total_known else "")
    print()
    print("=" * 100)

    return bio_detected, total_known


if __name__ == "__main__":
    detected, total = run_benchmark()
    if detected >= total * 0.5:
        print("\n  PASS -- Bio module detects >=50% of known epitopes.\n")
    else:
        print("\n  NEEDS IMPROVEMENT -- Bio module detects <50% of known epitopes.\n")
