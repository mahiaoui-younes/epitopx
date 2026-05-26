#!/usr/bin/env python3
"""
Test 10 proteins: Bio module vs Bio + IEDB API comparison.

Runs the EpiTop1 prediction pipeline on 10 well-characterised proteins
with experimentally validated B-cell linear epitopes. Compares results
with and without the IEDB API integration.

Usage:
    python test_10_proteins_iedb.py
"""

from __future__ import annotations
import sys, os, time, logging
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np

# Enable IEDB API logging to see per-method status
logging.basicConfig(level=logging.INFO, format="  %(name)s: %(message)s")

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from bio.scoring import CombinedScorer
from bio.epitope_detector import EpitopeDetector


# ─────────────────────────────────────────────────────────────────────────────
# 10 Test Proteins with known epitopes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TestProtein:
    name: str
    accession: str
    sequence: str
    known_epitopes: List[str]
    description: str = ""


PROTEINS: list[TestProtein] = [
    # 1. Theileria annulata TaSP
    TestProtein(
        name="Theileria annulata TaSP",
        accession="CAC87893.1",
        description="Surface protein — validated epitope in hydrophilic repeat region.",
        sequence=(
            "MANKVISFLLAFIFSQSAADNCSEENQDSQESLVTSVENNHSEEMQEESRVVSETEHNKTP"
            "TSVHQEEDHNEESIHQPEELQPETVTVEVPEPVTSEEPKESDQTEEQKHEEPEASPAPEPV"
            "DEPAVHAQEDEGEDDEVTPEFEDDMKPADLLKKTNDQTESQPVSEENHTKEEKPEKGPKDE"
            "NKASHTATKVEEEENVEETEKPVQGDDDENKDEETKEEIDQADTSIHGETKPEDQGDNEKPV"
            "KAEEETPEEFQGSVIAILLAFTIGFLITKKRKVFVK"
        ),
        known_epitopes=["SEEPKESDQTEEQKHEEPEASPAPEPVDEPAVHA"],
    ),

    # 2. SARS-CoV-2 Spike RBD
    TestProtein(
        name="SARS-CoV-2 Spike RBD",
        accession="P0DTC2 (319-541)",
        description="Receptor-binding domain — epitopes from convalescent sera (IEDB).",
        sequence=(
            "RVQPTESIVRFPNITNLCPFGEVFNATRFASVYAWNRKRISNCVADYSVLYNSASFSTFKC"
            "YGVSPTKLNDLCFTNVYADSFVIRGDEVRQIAPGQTGKIADYNYKLPDDFTGCVIAWNSNN"
            "LDSKVGGNYNYLYRLFRKSNLKPFERDISTEIYQAGSTPCNGVEGFNCYFPLQSYGFQPTN"
            "GVGYQPYRVVVLSFELLHAPATVCGPKKSTNLVKNKCVNF"
        ),
        known_epitopes=[
            "YAWNRKRISNCVADY",
            "GDEVRQIAPGQTGKI",
            "LFRKSNLKPFERDIS",
            "SYGFQPTNGVGYQPY",
        ],
    ),

    # 3. HIV-1 gp41 MPER
    TestProtein(
        name="HIV-1 gp41 MPER",
        accession="P04578 (fragment)",
        description="Membrane-proximal external region — 2F5 and 4E10 neutralising epitopes.",
        sequence=(
            "AVGIGALFLGFLGAAGSTMGAASMTLTVQARQLLSGIVQQQNNLLRAIEAQQHLLQLTVW"
            "GIKQLQARILAVERYLKDQQLLGIWGCSGKLICTTAVPWNASWSNKSLEQIWNHTTWMEW"
            "DREINNYTSLIHSLIEESQNQQEKNEQELLELDKWASLWNWFNITNWLWYIK"
        ),
        known_epitopes=[
            "ELDKWASLWNWF",
            "NWFNITNWLWYIK",
            "NEQELLELDKWASLW",
        ],
    ),

    # 4. Influenza H3N2 HA1
    TestProtein(
        name="Influenza H3N2 HA1",
        accession="P03435 (HA1 domain)",
        description="Hemagglutinin HA1 — antigenic sites A-E.",
        sequence=(
            "QDLPGNDNSTATLCLGHHAVPNGTLVKTITDDQIEVTNATELVQSSSTGKICNNPHRILD"
            "GIDCTLIDALLGDPHCDVFQNETWDLFVERSKAFSNCYPYDVPDYASLRSLVASSGTLEFI"
            "TEGFTWTGVTQNGGSNACKRGPGSGFFSRLNWLTKSGSTYPVLNVTMPNNDNFDKLYING"
            "NLIAPWYAFALSRGFGSGIITSNAPMDECDAKCQTPQGAINSSLPFQNVHPVTIGECPKYV"
            "RSTKLRMVTGLRNIPSIQSRGLFGAIAGFIEGGWTGMIDGWYGYHHQNEQGSGYAADLKST"
            "QNAIDEITNKVNSVIEKMNTQFTAVGKEF"
        ),
        known_epitopes=[
            "SKAFSNCYPYDVPDY",
            "KSGSTYPVLNVTMPN",
            "SLPFQNVHPVTIGEC",
            "TQNGGSNACKRGPGS",
        ],
    ),

    # 5. P. falciparum CSP
    TestProtein(
        name="P. falciparum CSP",
        accession="P04925 (fragment)",
        description="Circumsporozoite protein — (NANP)n repeat B-cell epitope.",
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
            "NANPNVDPNANPNVD",
            "NKNNQGNGQGHNMPN",
            "EWSPCSVTCGNGIQV",
        ],
    ),

    # 6. Hepatitis B Surface Antigen
    TestProtein(
        name="HBV Surface Antigen",
        accession="P03138",
        description="HBV S antigen — 'a' determinant is major neutralising epitope.",
        sequence=(
            "MENITSGFLGPLLVLQAGFFLLTRILTIPQSLDSWWTSLNFLGGTTVCLGQNSQSPTSNHS"
            "PTSCPPTCPGYRWMCLRRFIIFLFILLLCLIFLLVLLDYQGMLPVCPLIPGSSTTSTGPCRT"
            "CMTTAQGTSMYPSCCCTKPSDGNCTCIPIPSSWAFGKFLWEWASARFSWLSLLVPFVQWFVG"
            "LSPTVWLSAIWMMWYWGPSLYNILSPFLPLLPIFFCLWVYI"
        ),
        known_epitopes=[
            "CRTCMTTAQGTSMYP",
            "STTSTGPCRTCMTTA",
            "PSCCCTKPSDGNCTC",
        ],
    ),

    # 7. Dengue-2 Envelope Domain III
    TestProtein(
        name="Dengue-2 E-DIII",
        accession="P04724 (domain III)",
        description="Envelope DIII — AB loop and FG loop neutralising epitopes.",
        sequence=(
            "MRCIGMSNRDFVEGVSGGSWVDIVLEHGSCVTTMAKNKPTLDFELIKTEAKQPATLRKYCIEAKL"
            "TNTTTESRCPTQGEPSLNEEQDKRFVCKHSMVDRGWGNGCGLFGKGGIVTCAMFRCKKNMEGKV"
            "VQPENLEYTIVITPHSGEEHAVGNDTGKHGKEIKITPQSSITEAELTGYGTVTMECSPRTGLDF"
            "NEMVLLQMENKAWLVHRQWFLDLPLPWLPGADTQ"
        ),
        known_epitopes=[
            "GSWVDIVLEHGSCVT",
            "KGGIVTCAMFRCKK",
            "EIKITPQSSITEAEL",
        ],
    ),

    # 8. M. tuberculosis ESAT-6
    TestProtein(
        name="M. tuberculosis ESAT-6",
        accession="P0A564",
        description="Major TB diagnostic antigen — multiple linear B-cell epitopes.",
        sequence=(
            "MTEQQWNFAGIEAAASAIQGNVTSIHSLLDEGKQSLTKLAAAWGGSGSEAYQGVQQKWDATA"
            "TELNNALQNLARTISEAGQAMASTEGNVTGMFA"
        ),
        known_epitopes=[
            "EAAASAIQGNVTSI",
            "QWNFAGIEAAASAI",
            "NNALQNLARTISEA",
        ],
    ),

    # 9. Human Beta-2 Microglobulin
    TestProtein(
        name="Human B2M",
        accession="P61769",
        description="MHC class I light chain — auto-antigen with mapped B-cell epitopes.",
        sequence=(
            "MSRSVALAVLALLSLSGLEAIQRTPKIQVYSRHPAENGKSNFLNCYVSGFHPSDIEVDLLK"
            "NGERIEKDEHLLLEDLKTVPFSKRIVQCTWQHQRGPMRDEFIIQGLQPFR"
        ),
        known_epitopes=[
            "IQVYSRHPAENGKSN",
            "SGFHPSDIEVDLLKN",
        ],
    ),

    # 10. Tetanus Toxin C-fragment
    TestProtein(
        name="Tetanus Toxin C-frag",
        accession="P04958 (fragment)",
        description="Tetanus toxin heavy chain C-terminal — well-studied B-cell epitopes.",
        sequence=(
            "DVDNALNEILEQNKAIIEQEIENLNNEIESEIYPYIGALKYIDKESKDKEIIPNIKDLKE"
            "LDQNKENIYLEIYNKEFTLNIDKKSASMYEQALNHIKDIKNDGINAGSYSKLTSKDKEL"
            "KPDINPYLSFTDRFDFIDPLNIIEYKMSNKYKNIDQIFEVKQFYDQNINKISAFENNKLY"
            "PNFDAYNAKMIGLYVKKINQEKLENMKFQIEINKINNYKFKNEDNPIDHTTSLILHGQKDL"
            "STFNLIDY"
        ),
        known_epitopes=[
            "QNKAIIEQEIENLN",
            "KEFTLNIDKKSASM",
            "NAKMIGLYVKKINQ",
        ],
    ),
]


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def find_epitope_pos(sequence: str, epitope: str) -> Tuple[int, int]:
    """Return 1-indexed (start, end), or (0, 0) if not found."""
    pos = sequence.upper().find(epitope.upper())
    if pos < 0:
        return (0, 0)
    return (pos + 1, pos + len(epitope))


def overlap_fraction(ps, pe, ks, ke) -> float:
    """Fraction of known epitope covered by prediction."""
    if ks == 0:
        return 0.0
    known = set(range(ks, ke + 1))
    pred = set(range(ps, pe + 1))
    return len(known & pred) / len(known) if known else 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Run the benchmark
# ─────────────────────────────────────────────────────────────────────────────

def run_test():
    print("=" * 110)
    print("  EpiTop1 -- 10-PROTEIN BENCHMARK: Bio vs Bio+IEDB")
    print("=" * 110)
    print()

    # Accumulators
    total_known = 0
    stats = {"bio": {"det": 0, "top5": 0, "top10": 0},
             "iedb": {"det": 0, "top5": 0, "top10": 0}}
    rows = []

    for idx, prot in enumerate(PROTEINS, 1):
        seq = prot.sequence.upper().replace("\n", "").replace(" ", "")
        print("-" * 110, flush=True)
        print(f"  [{idx}/10] {prot.name} ({prot.accession})  --  {len(seq)} aa", flush=True)
        print(f"  {prot.description}", flush=True)
        print(flush=True)

        # ── Bio (no IEDB) ──
        t0 = time.time()
        bio_scorer = CombinedScorer(use_iedb=False)
        bio_res = bio_scorer.get_residue_results(seq)
        bio_det = EpitopeDetector({"min_length": 8, "max_length": 25, "top_n": 20})
        bio_hits = bio_det.detect(seq, bio_res)
        bio_time = time.time() - t0

        # ── Bio + IEDB ──
        print(f"  Querying IEDB API (7 methods)...", end="", flush=True)
        t0 = time.time()
        iedb_scorer = CombinedScorer(use_iedb=True)
        iedb_res = iedb_scorer.get_residue_results(seq)
        iedb_det = EpitopeDetector({"min_length": 8, "max_length": 25, "top_n": 20})
        iedb_hits = iedb_det.detect(seq, iedb_res)
        iedb_time = time.time() - t0
        print(f" done.", flush=True)

        print(f"  Bio:  {len(bio_hits):>2} predictions ({bio_time:.1f}s)", flush=True)
        print(f"  IEDB: {len(iedb_hits):>2} predictions ({iedb_time:.1f}s)", flush=True)
        print(flush=True)

        prot_bio_det = 0; prot_bio_t5 = 0; prot_bio_t10 = 0
        prot_iedb_det = 0; prot_iedb_t5 = 0; prot_iedb_t10 = 0

        for epi in prot.known_epitopes:
            total_known += 1
            ks, ke = find_epitope_pos(seq, epi)
            if ks == 0:
                print(f"  WARNING: Epitope not found: {epi}")
                continue

            # Best overlap for bio
            best_bio_ov, best_bio_rk = 0.0, 999
            for h in bio_hits:
                ov = overlap_fraction(h.start, h.end, ks, ke)
                if ov > best_bio_ov:
                    best_bio_ov = ov; best_bio_rk = h.rank

            # Best overlap for iedb
            best_iedb_ov, best_iedb_rk = 0.0, 999
            for h in iedb_hits:
                ov = overlap_fraction(h.start, h.end, ks, ke)
                if ov > best_iedb_ov:
                    best_iedb_ov = ov; best_iedb_rk = h.rank

            bio_ok = best_bio_ov >= 0.50
            iedb_ok = best_iedb_ov >= 0.50

            if bio_ok:
                prot_bio_det += 1
                if best_bio_rk <= 5: prot_bio_t5 += 1
                if best_bio_rk <= 10: prot_bio_t10 += 1
            if iedb_ok:
                prot_iedb_det += 1
                if best_iedb_rk <= 5: prot_iedb_t5 += 1
                if best_iedb_rk <= 10: prot_iedb_t10 += 1

            tag_bio = f"FOUND rank {best_bio_rk} ({best_bio_ov:.0%})" if bio_ok else f"missed ({best_bio_ov:.0%})"
            tag_iedb = f"FOUND rank {best_iedb_rk} ({best_iedb_ov:.0%})" if iedb_ok else f"missed ({best_iedb_ov:.0%})"
            marker = ""
            if iedb_ok and not bio_ok:
                marker = "  << IEDB IMPROVEMENT"
            elif not iedb_ok and bio_ok:
                marker = "  << IEDB REGRESSION"

            print(f"  Epitope: {epi[:35]:<35s}  pos {ks}-{ke}")
            print(f"    Bio:  {tag_bio}")
            print(f"    IEDB: {tag_iedb}{marker}")

        stats["bio"]["det"] += prot_bio_det
        stats["bio"]["top5"] += prot_bio_t5
        stats["bio"]["top10"] += prot_bio_t10
        stats["iedb"]["det"] += prot_iedb_det
        stats["iedb"]["top5"] += prot_iedb_t5
        stats["iedb"]["top10"] += prot_iedb_t10

        rows.append({
            "name": prot.name,
            "n": len(prot.known_epitopes),
            "bio_det": prot_bio_det, "bio_t5": prot_bio_t5,
            "iedb_det": prot_iedb_det, "iedb_t5": prot_iedb_t5,
        })
        print()

    # ── Summary table ──
    print("=" * 110)
    print("  SUMMARY -- Bio vs Bio+IEDB")
    print("=" * 110)
    print()
    hdr = f"  {'Protein':<30s} {'Known':>6}  {'Bio Det':>8} {'IEDB Det':>9}  {'Bio Top5':>9} {'IEDB Top5':>10}"
    print(hdr)
    print("  " + "-" * 95)
    for r in rows:
        print(f"  {r['name']:<30s} {r['n']:>6}  {r['bio_det']:>8} {r['iedb_det']:>9}"
              f"  {r['bio_t5']:>9} {r['iedb_t5']:>10}")
    print("  " + "-" * 95)

    b, i = stats["bio"], stats["iedb"]
    print(f"  {'TOTAL':<30s} {total_known:>6}  {b['det']:>8} {i['det']:>9}"
          f"  {b['top5']:>9} {i['top5']:>10}")
    print()

    def pct(n, d): return f"{n/d*100:.1f}%" if d else "N/A"

    print(f"  Sensitivity (>=50% overlap):")
    print(f"    Bio:      {b['det']}/{total_known}  ({pct(b['det'], total_known)})")
    print(f"    Bio+IEDB: {i['det']}/{total_known}  ({pct(i['det'], total_known)})")
    print()
    print(f"  Top-5 rate:")
    print(f"    Bio:      {b['top5']}/{total_known}  ({pct(b['top5'], total_known)})")
    print(f"    Bio+IEDB: {i['top5']}/{total_known}  ({pct(i['top5'], total_known)})")
    print()
    print(f"  Top-10 rate:")
    print(f"    Bio:      {b['top10']}/{total_known}  ({pct(b['top10'], total_known)})")
    print(f"    Bio+IEDB: {i['top10']}/{total_known}  ({pct(i['top10'], total_known)})")
    print()

    diff = i['det'] - b['det']
    if diff > 0:
        print(f"  >>> IEDB improved detection by +{diff} epitopes!")
    elif diff == 0:
        print(f"  >>> Same detection rate -- IEDB maintained accuracy.")
    else:
        print(f"  >>> IEDB lost {-diff} detections (needs tuning).")

    print()
    print("=" * 110)
    return b, i, total_known


if __name__ == "__main__":
    import io
    buf = io.StringIO()
    _orig_print = print
    def print(*args, **kwargs):
        kwargs_f = dict(kwargs)
        kwargs_f['file'] = buf
        _orig_print(*args, **kwargs)
        _orig_print(*args, **kwargs_f)
    import builtins
    builtins.print = print

    bio_stats, iedb_stats, total = run_test()

    with open("_test_10_results.txt", "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    _orig_print("\nResults saved to _test_10_results.txt")
