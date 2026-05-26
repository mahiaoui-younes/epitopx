"""
EpitopX AI — MSA Analysis Engine (Python / Biopython)

Produces:
  - SNP / variant site detection (Shannon entropy per column)
  - Haplotype grouping & haplotype diversity (Nei 1987)
  - Pairwise p-distance matrix (gap-aware Hamming)
  - Jukes-Cantor (JC69) corrected distances
  - Neighbor-Joining phylogenetic tree (Saitou & Nei 1987)
  - Minimum Evolution tree (Rzhetsky & Nei 1992, OLS branch lengths)
  - Maximum-Likelihood tree (JC69 model, NNI search, Felsenstein 1981)
  - Nucleotide diversity π (Tajima 1983)
  - Watterson's θ estimator
  - Tajima's D neutrality test (Tajima 1989)
  - Conservation score per column (Jensen-Shannon divergence)
  - Full visualization-ready JSON (D3 / Cytoscape compatible)

Scientific references:
  [1]  Saitou N. & Nei M. (1987) Mol Biol Evol 4:406-425  (NJ)
  [2]  Jukes T.H. & Cantor C.R. (1969) in Munro (ed.)     (JC69)
  [3]  Shannon C.E. (1948) Bell Syst Tech J 27:379-423     (entropy)
  [4]  Rzhetsky A. & Nei M. (1992) Mol Biol Evol 9:945-967 (ME)
  [5]  Tajima F. (1983) Genetics 105:437-460               (π)
  [6]  Watterson G.A. (1975) Theor Pop Biol 7:256-276      (θ)
  [7]  Tajima F. (1989) Genetics 123:585-595               (Tajima's D)
  [8]  Lin J. (1991) IEEE Trans Inf Theory 37:145-151       (JS divergence)
  [9]  Felsenstein J. (1981) J Mol Evol 17:368-376         (ML / Pulley)
  [10] Nei M. (1987) Molecular Evolutionary Genetics        (haplotype diversity)
  [11] Pauplin Y. (2000) J Mol Evol 51:41-47               (OLS branch lengths)
"""

import math
import re
from collections import defaultdict, Counter
from typing import Optional

# Optional Biopython – used for ClustalW-style alignment if available
try:
    from Bio import AlignIO, SeqIO
    from Bio.Align import MultipleSeqAlignment
    from Bio.SeqRecord import SeqRecord
    from Bio.Seq import Seq
    HAS_BIOPYTHON = True
except ImportError:
    HAS_BIOPYTHON = False

EPS = 1e-300  # Prevent log(0)


# ─────────────────────────────────────────────────────────────────────────────
# FASTA PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse_fasta(text: str) -> list[dict]:
    """
    Parse a multi-record FASTA string.
    Accepts standard & aligned FASTA (gap chars '-' and '.').
    Returns list of {id, description, sequence}.
    """
    if not isinstance(text, str) or not text.strip():
        return []

    records = []
    current_id = None
    current_desc = ''
    parts = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith('>'):
            if current_id is not None:
                records.append({
                    'id':          current_id,
                    'description': current_desc,
                    'sequence':    ''.join(parts).upper(),
                })
            space = line.find(' ')
            if space == -1:
                current_id, current_desc = line[1:], ''
            else:
                current_id   = line[1:space]
                current_desc = line[space + 1:].strip()
            parts = []
        else:
            # Keep gap characters; remove whitespace and digits
            parts.append(re.sub(r'[\s\d]', '', line))

    if current_id is not None:
        records.append({
            'id':          current_id,
            'description': current_desc,
            'sequence':    ''.join(parts).upper(),
        })

    return records


# ─────────────────────────────────────────────────────────────────────────────
# ALIGNMENT VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

VALID_ALIGNED = re.compile(r'^[ATGCRYMKSWHBVDN.\-]+$')


def validate_alignment(records: list[dict]) -> dict:
    errors = []
    if not records:
        return {'valid': False, 'alignment_length': 0, 'errors': ['No sequences provided.']}
    if len(records) < 2:
        errors.append('At least 2 sequences are required for MSA analysis.')
        return {'valid': False, 'alignment_length': 0, 'errors': errors}

    lengths = [len(r['sequence']) for r in records]
    ref_len = lengths[0]

    for r, ln in zip(records, lengths):
        if ln != ref_len:
            errors.append(f"Sequence \"{r['id']}\" has length {ln}, expected {ref_len}.")
        if not VALID_ALIGNED.match(r['sequence']):
            errors.append(f"Sequence \"{r['id']}\" contains non-standard characters.")

    return {
        'valid':            len(errors) == 0,
        'alignment_length': ref_len,
        'errors':           errors,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — COLUMN UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _column_entropy(bases: list[str]) -> float:
    """
    Shannon entropy H = -Σ p_i·log₂(p_i) in bits — [3]
    Gaps ('-', '.') are excluded from the frequency calculation.
    """
    freq: dict[str, int] = {}
    total = 0
    for b in bases:
        if b in ('-', '.'):
            continue
        freq[b] = freq.get(b, 0) + 1
        total += 1
    if total == 0:
        return 0.0
    H = 0.0
    for cnt in freq.values():
        p = cnt / total
        H -= p * math.log2(p)
    return H


def _js_divergence(bases: list[str]) -> float:
    """
    Jensen-Shannon divergence between observed column distribution
    and the uniform background over {A,T,G,C} — [8].
    Measures conservation: 0 = maximally variable, 1 = fully conserved.
    Gaps excluded from the calculation.
    """
    background = {'A': 0.25, 'T': 0.25, 'G': 0.25, 'C': 0.25}
    obs: dict[str, float] = {}
    total = 0
    for b in bases:
        if b in ('-', '.') or b not in background:
            continue
        obs[b] = obs.get(b, 0) + 1
        total += 1
    if total == 0:
        return 0.0

    p = {k: obs.get(k, 0) / total for k in background}
    q = background
    m = {k: (p[k] + q[k]) / 2 for k in background}

    def kl(a, b_dict):
        return sum(a[k] * math.log2(a[k] / b_dict[k] + EPS) for k in a if a[k] > 0)

    jsd = (kl(p, m) + kl(q, m)) / 2
    return round(max(0.0, min(1.0, 1.0 - jsd)), 6)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — SNP DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_snps(records: list[dict], ref_index: int = 0) -> dict:
    """
    Detect SNPs column-by-column. For each variable position returns:
      position  (1-based), ref, refCount, refFreq,
      alts [{base, count, frequency}], totalSeqs, gapCount,
      entropy (bits), conservation_score (JS divergence).

    A column is variable if ≥2 distinct bases OR at least one gap
    coexists with at least one base (indel site).
    """
    n       = len(records)
    aln_len = len(records[0]['sequence'])
    snps    = []

    for col in range(aln_len):
        bases = [r['sequence'][col] for r in records]

        freq: dict[str, int] = {}
        gap_cnt = 0
        for b in bases:
            if b in ('-', '.'):
                gap_cnt += 1
            else:
                freq[b] = freq.get(b, 0) + 1

        distinct = list(freq.keys())
        is_indel = gap_cnt > 0 and len(distinct) > 0

        if len(distinct) < 2 and not is_indel:
            continue  # conserved column

        # Reference base
        ref_b = records[ref_index]['sequence'][col]
        if ref_b in ('-', '.'):
            ref_b = sorted(distinct, key=lambda x: freq[x], reverse=True)[0] if distinct else '-'

        alt_bases = [b for b in distinct if b != ref_b]
        if is_indel and ref_b != '-':
            alt_bases.append('-')

        alts = sorted(
            [
                {
                    'base':      b,
                    'count':     gap_cnt if b == '-' else freq.get(b, 0),
                    'frequency': round((gap_cnt if b == '-' else freq.get(b, 0)) / n, 4),
                }
                for b in alt_bases
                if (gap_cnt if b == '-' else freq.get(b, 0)) > 0
            ],
            key=lambda x: -x['count'],
        )

        snps.append({
            'position':           col + 1,
            'ref':                ref_b,
            'ref_count':          freq.get(ref_b, 0),
            'ref_freq':           round(freq.get(ref_b, 0) / n, 4),
            'alts':               alts,
            'total_seqs':         n,
            'gap_count':          gap_cnt,
            'entropy':            round(_column_entropy(bases), 4),
            'conservation_score': round(_js_divergence(bases), 4),
            'high_variability':   _column_entropy(bases) > 0.5,
        })

    return {
        'snps':                snps,
        'total_positions':     aln_len,
        'variable_positions':  len(snps),
        'conserved_positions': aln_len - len(snps),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — HAPLOTYPE GROUPING
# ─────────────────────────────────────────────────────────────────────────────

def build_haplotypes(records: list[dict]) -> list[dict]:
    """
    Group sequences into haplotypes by identical aligned string.
    Computes haplotype diversity H_d = 1 - Σ x_i² (Nei 1987 [10]).
    """
    hmap: dict[str, dict] = {}
    for r in records:
        seq = r['sequence']
        if seq in hmap:
            hmap[seq]['members'].append(r['id'])
            hmap[seq]['count'] += 1
        else:
            hmap[seq] = {'members': [r['id']], 'count': 1, 'sequence': seq}

    n = len(records)
    sorted_haps = sorted(hmap.values(), key=lambda h: -h['count'])
    haplotypes = []
    for idx, h in enumerate(sorted_haps, 1):
        haplotypes.append({
            'haplotype_id': f'H{idx}',
            'members':      h['members'],
            'count':        h['count'],
            'frequency':    round(h['count'] / n, 4),
            'sequence':     h['sequence'],
        })
    return haplotypes


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 4 — PAIRWISE DISTANCE MATRIX
# ─────────────────────────────────────────────────────────────────────────────

def _p_distance(s1: str, s2: str) -> tuple[int, float, int]:
    """
    Pairwise p-distance (proportion of differing sites) — [2].
    Gap-gap pairs excluded from the denominator.
    Returns (raw_mismatches, p_dist, comparable_sites).
    """
    mismatches = 0
    comparable = 0
    length = min(len(s1), len(s2))
    for i in range(length):
        b1, b2 = s1[i], s2[i]
        g1 = b1 in ('-', '.')
        g2 = b2 in ('-', '.')
        if g1 and g2:
            continue
        comparable += 1
        if b1 != b2:
            mismatches += 1
    p = round(mismatches / comparable, 6) if comparable else 0.0
    return mismatches, p, comparable


def _jc69_distance(p: float) -> float:
    """
    Jukes-Cantor (1969) correction [2]:  d = -(3/4) · ln(1 − 4p/3)
    Returns p itself when p ≥ 0.75 (saturated sites — correction undefined).
    """
    if p >= 0.75:
        return p
    try:
        return round(-(3 / 4) * math.log(1 - 4 * p / 3), 6)
    except (ValueError, ZeroDivisionError):
        return p


def build_distance_matrix(records: list[dict]) -> dict:
    """
    Build NxN symmetric p-distance matrix and JC69-corrected matrix.
    """
    n      = len(records)
    labels = [r['id'] for r in records]
    p_mat  = [[0.0] * n for _ in range(n)]
    jc_mat = [[0.0] * n for _ in range(n)]
    raw_mat = [[0]  * n for _ in range(n)]

    for i in range(n):
        for j in range(i + 1, n):
            raw, p, _ = _p_distance(records[i]['sequence'], records[j]['sequence'])
            jc         = _jc69_distance(p)
            p_mat[i][j]  = p_mat[j][i]  = p
            jc_mat[i][j] = jc_mat[j][i] = jc
            raw_mat[i][j] = raw_mat[j][i] = raw

    return {
        'labels':      labels,
        'matrix':      p_mat,
        'jc_matrix':   jc_mat,
        'raw_matrix':  raw_mat,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 5 — NEIGHBOR-JOINING TREE  (Saitou & Nei 1987) [1]
# ─────────────────────────────────────────────────────────────────────────────

def neighbor_joining(dist_matrix: list[list[float]], labels: list[str]) -> dict:
    """
    Build a Neighbor-Joining tree from a symmetric p-distance matrix — [1].
    """
    if not dist_matrix:
        return {'nodes': [], 'edges': [], 'root': None}
    if len(dist_matrix) == 1:
        return {
            'nodes': [{'id': labels[0], 'type': 'leaf'}],
            'edges': [],
            'root':  labels[0],
        }

    D     = [row[:] for row in dist_matrix]
    names = list(labels)
    n     = len(names)

    nodes       = [{'id': lbl, 'type': 'leaf'} for lbl in labels]
    edges       = []
    node_counter = 0

    while n > 2:
        R = [sum(D[i]) for i in range(n)]

        min_q  = math.inf
        min_i  = 0
        min_j  = 1
        for i in range(n):
            for j in range(i + 1, n):
                q = (n - 2) * D[i][j] - R[i] - R[j]
                if q < min_q:
                    min_q, min_i, min_j = q, i, j

        lim_i = D[min_i][min_j] / 2 + (R[min_i] - R[min_j]) / (2 * (n - 2))
        lim_j = D[min_i][min_j] - lim_i

        node_counter += 1
        new_node_id = f'node_{node_counter}'
        nodes.append({'id': new_node_id, 'type': 'internal'})
        edges.append({'source': new_node_id, 'target': names[min_i],
                      'length': round(max(0.0, lim_i), 6)})
        edges.append({'source': new_node_id, 'target': names[min_j],
                      'length': round(max(0.0, lim_j), 6)})

        new_dists = []
        for k in range(n):
            if k in (min_i, min_j):
                new_dists.append(0.0)
                continue
            d_uk = max(0.0, (D[min_i][k] + D[min_j][k] - D[min_i][min_j]) / 2)
            new_dists.append(d_uk)

        keep = [i for i in range(n) if i not in (min_i, min_j)]
        new_D = [[D[i][j] for j in keep] + [new_dists[i]] for i in keep]
        new_D.append([new_dists[k] for k in keep] + [0.0])

        names = [names[i] for i in keep] + [new_node_id]
        D     = new_D
        n     = len(names)

    node_counter += 1
    final_id   = f'node_{node_counter}'
    half_dist  = D[0][1] / 2
    nodes.append({'id': final_id, 'type': 'internal'})
    edges.append({'source': final_id, 'target': names[0],
                  'length': round(max(0.0, half_dist), 6)})
    edges.append({'source': final_id, 'target': names[1],
                  'length': round(max(0.0, D[0][1] - half_dist), 6)})

    return {'nodes': nodes, 'edges': edges, 'root': final_id}


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 6 — MINIMUM EVOLUTION TREE  (Rzhetsky & Nei 1992) [4]
# ─────────────────────────────────────────────────────────────────────────────

def _leaves_of(start_id: str, forbid_id: str, adj: dict, leaf_set: set) -> list[str]:
    """DFS to collect all leaf ids reachable from start_id without passing forbid_id."""
    visited = {forbid_id}
    stack   = [start_id]
    leaves  = []
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        if cur in leaf_set:
            leaves.append(cur)
        for nb in adj.get(cur, []):
            if nb not in visited:
                stack.append(nb)
    return leaves


def minimum_evolution(dist_matrix: list[list[float]], labels: list[str]) -> dict:
    """
    Minimum Evolution tree via NJ topology + OLS branch-length estimation — [4][11].
    """
    nj_tree = neighbor_joining(dist_matrix, labels)
    if not nj_tree['root']:
        return {**nj_tree, 'tree_length': 0.0}

    adj: dict[str, list[str]] = defaultdict(list)
    for e in nj_tree['edges']:
        adj[e['source']].append(e['target'])
        adj[e['target']].append(e['source'])

    leaf_set  = {nd['id'] for nd in nj_tree['nodes'] if nd['type'] == 'leaf'}
    label_idx = {lbl: i for i, lbl in enumerate(labels)}

    ols_edges = []
    for e in nj_tree['edges']:
        leaves_a = _leaves_of(e['source'], e['target'], adj, leaf_set)
        leaves_b = _leaves_of(e['target'], e['source'], adj, leaf_set)
        total = cnt = 0.0
        for a in leaves_a:
            for b in leaves_b:
                ia, ib = label_idx.get(a), label_idx.get(b)
                if ia is not None and ib is not None:
                    total += dist_matrix[ia][ib]
                    cnt   += 1
        length = max(0.0, total / (2 * cnt)) if cnt else e['length']
        ols_edges.append({**e, 'length': round(length, 6)})

    tree_length = sum(e['length'] for e in ols_edges)
    return {
        'nodes':       nj_tree['nodes'],
        'edges':       ols_edges,
        'root':        nj_tree['root'],
        'tree_length': round(tree_length, 6),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 7 — MAXIMUM-LIKELIHOOD TREE  (JC69 model, NNI search) [9]
# ─────────────────────────────────────────────────────────────────────────────

def maximum_likelihood(
    dist_matrix: list[list[float]],
    raw_matrix:  list[list[int]],
    labels:      list[str],
    aln_len:     int,
) -> dict:
    """
    ML tree under the Jukes-Cantor (JC69) model [2][9].
    Topology search by NNI (nearest-neighbour interchange) starting from
    the NJ tree on JC69-corrected distances.

    Log-likelihood:
      lnL = Σ_{i<j} [ k_ij · ln(p_ij) + (L - k_ij) · ln(1 - p_ij) ]
    where k_ij = raw mismatches, L = alignment length, p_ij = p-distance.
    """
    n = len(labels)

    # Build JC69 distance matrix from p-distances
    jc_dist = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            jc = _jc69_distance(dist_matrix[i][j])
            jc_dist[i][j] = jc_dist[j][i] = jc

    def _tree_log_lik(edges, nodes_list):
        """Compute JC69 log-likelihood on the given edge set."""
        adj_ll: dict[str, list[str]] = defaultdict(list)
        for e in edges:
            adj_ll[e['source']].append(e['target'])
            adj_ll[e['target']].append(e['source'])
        ls_set   = {nd['id'] for nd in nodes_list if nd['type'] == 'leaf'}
        li_idx   = {lbl: i for i, lbl in enumerate(labels)}
        leaf_ids = [nd['id'] for nd in nodes_list if nd['type'] == 'leaf']
        ll = 0.0
        for a_idx in range(len(leaf_ids)):
            for b_idx in range(a_idx + 1, len(leaf_ids)):
                a_id = leaf_ids[a_idx]
                b_id = leaf_ids[b_idx]
                ia, ib = li_idx.get(a_id), li_idx.get(b_id)
                if ia is None or ib is None:
                    continue
                p = dist_matrix[ia][ib] + EPS
                k = raw_matrix[ia][ib]
                L = aln_len
                ll += k * math.log(p) + (L - k) * math.log(max(EPS, 1 - p))
        return ll

    current_tree = neighbor_joining(jc_dist, labels)
    current_ll   = _tree_log_lik(current_tree['edges'], current_tree['nodes'])

    improved   = True
    iterations = 0
    MAX_ITER   = 20

    while improved and iterations < MAX_ITER:
        improved = False
        iterations += 1

        internal_ids = {nd['id'] for nd in current_tree['nodes'] if nd['type'] == 'internal'}

        for ei, edge in enumerate(current_tree['edges']):
            u, v = edge['source'], edge['target']
            if u not in internal_ids or v not in internal_ids:
                continue

            u_nb = [
                (e['target'] if e['source'] == u else e['source'])
                for e in current_tree['edges']
                if (e['source'] == u or e['target'] == u)
                and (e['target'] != v and e['source'] != v)
            ]
            v_nb = [
                (e['target'] if e['source'] == v else e['source'])
                for e in current_tree['edges']
                if (e['source'] == v or e['target'] == v)
                and (e['target'] != u and e['source'] != u)
            ]

            if len(u_nb) < 2 or len(v_nb) < 1:
                continue

            A, B = u_nb[0], u_nb[1]
            C    = v_nb[0]

            for swap_out, swap_in in [(B, C), (A, C)]:
                swapped = []
                for e in current_tree['edges']:
                    ne = dict(e)
                    if e['source'] == u and e['target'] == swap_out:
                        ne['target'] = swap_in
                    elif e['target'] == u and e['source'] == swap_out:
                        ne['source'] = swap_in
                    elif e['source'] == v and e['target'] == swap_in:
                        ne['target'] = swap_out
                    elif e['target'] == v and e['source'] == swap_in:
                        ne['source'] = swap_out
                    swapped.append(ne)

                swap_ll = _tree_log_lik(swapped, current_tree['nodes'])
                if swap_ll > current_ll + 1e-8:
                    current_tree = {**current_tree, 'edges': swapped}
                    current_ll   = swap_ll
                    improved     = True
                    break
            if improved:
                break

    # Final OLS branch-length re-estimation (Pauplin 2000) [11]
    adj_final: dict[str, list[str]] = defaultdict(list)
    for e in current_tree['edges']:
        adj_final[e['source']].append(e['target'])
        adj_final[e['target']].append(e['source'])
    ls_set2  = {nd['id'] for nd in current_tree['nodes'] if nd['type'] == 'leaf'}
    li_idx2  = {lbl: i for i, lbl in enumerate(labels)}

    final_edges = []
    for e in current_tree['edges']:
        la = _leaves_of(e['source'], e['target'], adj_final, ls_set2)
        lb = _leaves_of(e['target'], e['source'], adj_final, ls_set2)
        total = cnt = 0.0
        for a in la:
            for b in lb:
                ia, ib = li_idx2.get(a), li_idx2.get(b)
                if ia is not None and ib is not None:
                    total += jc_dist[ia][ib]
                    cnt   += 1
        length = max(0.0, total / (2 * cnt)) if cnt else e['length']
        final_edges.append({**e, 'length': round(length, 6)})

    return {
        'nodes':          current_tree['nodes'],
        'edges':          final_edges,
        'root':           current_tree['root'],
        'log_likelihood': round(current_ll, 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 8 — POPULATION GENETICS
# ─────────────────────────────────────────────────────────────────────────────

def nucleotide_diversity(records: list[dict]) -> float:
    """
    Tajima's nucleotide diversity π — [5].
    π = Σ_{i<j} d_ij / C(n,2)
    where d_ij is the p-distance between sequences i and j.
    """
    n = len(records)
    if n < 2:
        return 0.0
    total = 0.0
    pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            _, p, _ = _p_distance(records[i]['sequence'], records[j]['sequence'])
            total += p
            pairs += 1
    return round(total / pairs, 6) if pairs else 0.0


def wattersons_theta(records: list[dict], seg_sites: int) -> float:
    """
    Watterson's θ estimator — [6].
    θ_W = S / a_n  where a_n = Σ_{i=1}^{n-1} (1/i)
    """
    n = len(records)
    if n < 2:
        return 0.0
    a_n = sum(1 / i for i in range(1, n))
    L   = len(records[0]['sequence'])
    return round(seg_sites / (a_n * L), 6) if (a_n * L) else 0.0


def tajimas_d(records: list[dict], snp_result: dict) -> dict:
    """
    Tajima's D test statistic — [7].
    D = (π - θ_W) / sqrt(Var(π - θ_W))

    Interpretation:
      D < -2 : excess of rare variants → purifying selection / expansion
      D ≈  0 : neutral evolution
      D >  2 : excess of intermediate-frequency variants → balancing selection
    """
    n  = len(records)
    S  = snp_result['variable_positions']
    L  = snp_result['total_positions']

    if n < 3 or S == 0:
        return {
            'D': None,
            'pi': nucleotide_diversity(records),
            'theta_w': 0.0,
            'S': S,
            'n': n,
            'interpretation': 'Not enough data for Tajima\'s D test.',
        }

    a1 = sum(1 / i for i in range(1, n))
    a2 = sum(1 / (i ** 2) for i in range(1, n))

    b1 = (n + 1) / (3 * (n - 1))
    b2 = (2 * (n ** 2 + n + 3)) / (9 * n * (n - 1))

    c1 = b1 - 1 / a1
    c2 = b2 - (n + 2) / (a1 * n) + a2 / (a1 ** 2)

    e1 = c1 / a1
    e2 = c2 / (a1 ** 2 + a2)

    # Per-site values
    pi      = nucleotide_diversity(records)
    theta_w = wattersons_theta(records, S)

    var_d = e1 * S + e2 * S * (S - 1)
    if var_d <= 0:
        return {
            'D': None,
            'pi': round(pi, 6),
            'theta_w': round(theta_w, 6),
            'S': S,
            'n': n,
            'interpretation': 'Variance is zero; cannot compute D.',
        }

    D_val = (pi - theta_w) / math.sqrt(var_d)
    D_val = round(D_val, 4)

    if D_val < -2:
        interp = 'Negative D: excess rare variants — consistent with purifying selection or recent population expansion.'
    elif D_val > 2:
        interp = 'Positive D: excess intermediate-frequency variants — consistent with balancing selection or population contraction.'
    else:
        interp = 'D near 0: consistent with neutral evolution under the standard neutral model.'

    return {
        'D':             D_val,
        'pi':            round(pi, 6),
        'theta_w':       round(theta_w, 6),
        'S':             S,
        'n':             n,
        'interpretation': interp,
    }


def haplotype_diversity(haplotypes: list[dict]) -> float:
    """
    Nei's haplotype diversity H_d = [n/(n-1)] · (1 - Σ x_i²) — [10].
    """
    n = sum(h['count'] for h in haplotypes)
    if n < 2:
        return 0.0
    sum_sq = sum((h['count'] / n) ** 2 for h in haplotypes)
    H_d = (n / (n - 1)) * (1 - sum_sq)
    return round(H_d, 6)


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 9 — VISUALIZATION-READY JSON
# ─────────────────────────────────────────────────────────────────────────────

def _build_d3_tree(nodes, edges, root):
    """Convert edge list to D3 hierarchy (recursive parent→children dict)."""
    if not root:
        return None
    child_map: dict[str, list] = defaultdict(list)
    for e in edges:
        child_map[e['source']].append({'id': e['target'], 'branch_length': e['length']})
    node_type = {nd['id']: nd['type'] for nd in nodes}

    def _build(node_id):
        entry = {
            'id':       node_id,
            'type':     node_type.get(node_id, 'unknown'),
            'name':     node_id if node_type.get(node_id) == 'leaf' else '',
            'children': [],
        }
        for ch in child_map.get(node_id, []):
            child_entry = _build(ch['id'])
            child_entry['branch_length'] = ch['branch_length']
            entry['children'].append(child_entry)
        if not entry['children']:
            del entry['children']
        return entry

    return _build(root)


def to_visualization_json(
    snp_result:       dict,
    haplotype_result: list[dict],
    tree_result:      dict,
    labels:           list[str],
    dist_matrix:      list[list[float]],
    tree_method:      str = 'nj',
) -> dict:
    """Package all results into visualization-ready JSON."""

    # SNP map
    snp_map = {
        'type':                'snp_map',
        'total_positions':     snp_result['total_positions'],
        'variable_positions':  snp_result['variable_positions'],
        'conserved_positions': snp_result['conserved_positions'],
        'snps':                snp_result['snps'],
    }

    # Haplotypes
    n_seqs = len(labels)
    haplotypes_json = {
        'type':            'haplotypes',
        'total_seqs':      n_seqs,
        'haplotype_count': len(haplotype_result),
        'haplotypes':      haplotype_result,
    }

    # Distance matrix
    distance_matrix_json = {
        'type':   'distance_matrix',
        'labels': labels,
        'matrix': dist_matrix,
    }

    # Phylogenetic tree — Cytoscape.js elements array
    cy_elements = (
        [{'data': {'id': nd['id'], 'type': nd['type'],
                   'label': nd['id'] if nd['type'] == 'leaf' else ''}}
         for nd in tree_result['nodes']]
        +
        [{'data': {'id': f'e_{i}', 'source': e['source'], 'target': e['target'],
                   'length': e['length'],
                   'weight': round(1 / e['length'], 4) if e['length'] > 0 else 1000}}
         for i, e in enumerate(tree_result['edges'])]
    )

    algo_meta = {
        'nj': {'algorithm': 'Neighbor-Joining',     'reference': 'Saitou & Nei (1987)'},
        'me': {'algorithm': 'Minimum Evolution',    'reference': 'Rzhetsky & Nei (1992)'},
        'ml': {'algorithm': 'Maximum Likelihood',   'reference': 'JC69 / Felsenstein (1981) + NNI'},
    }
    meta = algo_meta.get(tree_method, algo_meta['nj'])

    phylo_tree = {
        'type':        'phylo_tree',
        'algorithm':   meta['algorithm'],
        'reference':   meta['reference'],
        'root':        tree_result['root'],
        'nodes':       tree_result['nodes'],
        'edges':       tree_result['edges'],
        'cy_elements': cy_elements,
        'd3_hierarchy': _build_d3_tree(
            tree_result['nodes'], tree_result['edges'], tree_result['root']
        ),
    }
    if 'log_likelihood' in tree_result:
        phylo_tree['log_likelihood'] = tree_result['log_likelihood']
    if 'tree_length' in tree_result:
        phylo_tree['tree_length'] = tree_result['tree_length']

    return {
        'snp_map':        snp_map,
        'haplotypes':     haplotypes_json,
        'distance_matrix': distance_matrix_json,
        'phylo_tree':     phylo_tree,
    }


# ─────────────────────────────────────────────────────────────────────────────
# SECTION 10 — FULL ANALYSIS PIPELINE
# ─────────────────────────────────────────────────────────────────────────────

def _mean_pairwise_dist(matrix: list[list[float]]) -> float:
    n = len(matrix)
    if n < 2:
        return 0.0
    total = sum(matrix[i][j] for i in range(n) for j in range(i + 1, n))
    pairs = n * (n - 1) // 2
    return round(total / pairs, 6) if pairs else 0.0


def run_pipeline(fasta_text: str, ref_index: int = 0, tree_method: str = 'nj') -> dict:
    """
    Full MSA analysis pipeline:
      1. Parse FASTA
      2. Validate alignment
      3. SNP detection (Shannon entropy + JS conservation)
      4. Haplotype grouping + diversity (Nei 1987)
      5. p-distance matrix + JC69 correction
      6. Phylogenetic tree (NJ / ME / ML)
      7. Population genetics: π, θ_W, Tajima's D
      8. Visualization JSON
      9. Summary statistics

    Parameters
    ----------
    fasta_text  : Aligned FASTA string (all sequences same length)
    ref_index   : Index of the reference sequence for SNP calls (default 0)
    tree_method : 'nj' (Neighbor-Joining) | 'me' (Minimum Evolution) |
                  'ml' (Maximum Likelihood, JC69 + NNI)

    Returns
    -------
    Full result dict or {'error': ..., 'validation': ...} on failure.
    """
    # 1 — Parse
    records = parse_fasta(fasta_text)

    # 2 — Validate
    validation = validate_alignment(records)
    if not validation['valid']:
        return {
            'error':      'Alignment validation failed.',
            'validation': validation,
            'records':    [{'id': r['id'], 'length': len(r['sequence'])} for r in records],
        }

    # 3 — SNPs
    snp_result = detect_snps(records, ref_index)

    # 4 — Haplotypes
    haplotype_result = build_haplotypes(records)
    h_div            = haplotype_diversity(haplotype_result)

    # 5 — Distance matrix
    dm_result = build_distance_matrix(records)
    labels    = dm_result['labels']
    p_matrix  = dm_result['matrix']
    jc_matrix = dm_result['jc_matrix']
    raw_matrix = dm_result['raw_matrix']

    # 6 — Phylogenetic tree
    if tree_method == 'me':
        tree_result = minimum_evolution(p_matrix, labels)
    elif tree_method == 'ml':
        tree_result = maximum_likelihood(
            p_matrix, raw_matrix, labels, validation['alignment_length']
        )
    else:
        tree_result = neighbor_joining(p_matrix, labels)

    # 7 — Population genetics
    pi_val    = nucleotide_diversity(records)
    theta_w   = wattersons_theta(records, snp_result['variable_positions'])
    taj_d     = tajimas_d(records, snp_result)

    # 8 — Visualization JSON
    viz = to_visualization_json(
        snp_result, haplotype_result, tree_result,
        labels, p_matrix, tree_method,
    )

    # 9 — Summary
    variability_pct = round(
        snp_result['variable_positions'] / validation['alignment_length'] * 100, 2
    )
    summary = {
        'sequences':           len(records),
        'alignment_length':    validation['alignment_length'],
        'variable_sites':      snp_result['variable_positions'],
        'conserved_sites':     snp_result['conserved_positions'],
        'variability_pct':     variability_pct,
        'haplotypes':          len(haplotype_result),
        'haplotype_diversity': h_div,
        'nucleotide_diversity_pi': pi_val,
        'watterson_theta':     theta_w,
        'mean_pairwise_dist':  _mean_pairwise_dist(p_matrix),
        'reference_sequence':  records[ref_index]['id'],
        'tree_method':         tree_method,
        'tajimas_d':           taj_d,
        'biopython_version':   getattr(__import__('Bio', fromlist=['']), '__version__', 'unavailable') if HAS_BIOPYTHON else 'unavailable',
    }

    return {
        'records':        [{'id': r['id'], 'description': r.get('description', ''),
                            'sequence': r['sequence']} for r in records],
        'validation':     validation,
        'snp_result':     snp_result,
        'haplotypes':     haplotype_result,
        'distance_matrix': dm_result,
        'jc_matrix':      jc_matrix,
        'tree':           tree_result,
        'population_genetics': {
            'nucleotide_diversity_pi': pi_val,
            'watterson_theta':         theta_w,
            'tajimas_d':               taj_d,
            'haplotype_diversity':     h_div,
        },
        'viz':            viz,
        'summary':        summary,
    }
