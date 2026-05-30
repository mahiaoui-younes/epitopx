/**
 * alignment-worker.js — Web Worker for NW / Star alignment
 * Runs off the main UI thread so the browser never freezes.
 * Communicates via postMessage:
 *   IN  { seqs, matchScore, mismatchScore, gapOpen }
 *   OUT { type:'progress', done, total }   (periodic)
 *       { type:'result',  alignedSeqs }
 *       { type:'error',   message }
 */

/* ── Needleman-Wunsch (global pairwise) ─────────────────────────── */
function needlemanWunsch(seqA, seqB, match, mismatch, gapOpen) {
  const m = seqA.length, n = seqB.length;
  const score = [];
  for (let i = 0; i <= m; i++) {
    score[i] = new Int32Array(n + 1);
  }
  for (let i = 0; i <= m; i++) score[i][0] = i * gapOpen;
  for (let j = 0; j <= n; j++) score[0][j] = j * gapOpen;

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const diag = score[i-1][j-1] + (seqA[i-1] === seqB[j-1] ? match : mismatch);
      const up   = score[i-1][j] + gapOpen;
      const left = score[i][j-1] + gapOpen;
      score[i][j] = Math.max(diag, up, left);
    }
  }

  let alignA = '', alignB = '';
  let i = m, j = n;
  while (i > 0 && j > 0) {
    const s = score[i][j];
    if (s === score[i-1][j-1] + (seqA[i-1] === seqB[j-1] ? match : mismatch)) {
      alignA = seqA[i-1] + alignA; alignB = seqB[j-1] + alignB; i--; j--;
    } else if (s === score[i-1][j] + gapOpen) {
      alignA = seqA[i-1] + alignA; alignB = '-' + alignB; i--;
    } else {
      alignA = '-' + alignA; alignB = seqB[j-1] + alignB; j--;
    }
  }
  while (i > 0) { alignA = seqA[i-1] + alignA; alignB = '-' + alignB; i--; }
  while (j > 0) { alignA = '-' + alignA; alignB = seqB[j-1] + alignB; j--; }

  return { alignA, alignB, score: score[m][n] };
}

/* ── Star alignment helper ───────────────────────────────────────── */
function mergeStarAlignments(pairAligns, centreIdx) {
  const n = pairAligns.length;
  let refCentre = null;
  for (let i = 0; i < n; i++) {
    if (i !== centreIdx) { refCentre = pairAligns[i].centre; break; }
  }
  if (!refCentre) return [pairAligns[centreIdx].other];

  let masterCentre = refCentre.split('');
  const masterOthers = new Array(n).fill(null).map(() => []);

  for (let seqIdx = 0; seqIdx < n; seqIdx++) {
    if (seqIdx === centreIdx) {
      masterOthers[seqIdx] = masterCentre.slice();
      continue;
    }
    const pc = pairAligns[seqIdx].centre.split('');
    const po = pairAligns[seqIdx].other.split('');
    let masterPos = 0, pairPos = 0;
    const mapped = [];

    while (pairPos < pc.length && masterPos < masterCentre.length) {
      const mc = masterCentre[masterPos];
      const cc = pc[pairPos];
      if (mc === '-' && cc !== '-') {
        mapped.push('-'); masterPos++;
      } else if (mc !== '-' && cc === '-') {
        masterCentre.splice(masterPos, 0, '-');
        for (let k = 0; k < seqIdx; k++) {
          if (masterOthers[k]) masterOthers[k].splice(masterPos, 0, '-');
        }
        mapped.push(po[pairPos]); pairPos++; masterPos++;
      } else {
        mapped.push(po[pairPos]); masterPos++; pairPos++;
      }
    }
    while (pairPos < po.length) { mapped.push(po[pairPos++]); }
    masterOthers[seqIdx] = mapped;
  }

  const maxLen = Math.max(...masterOthers.map(r => r.length));
  return masterOthers.map(row => {
    while (row.length < maxLen) row.push('-');
    return row.join('');
  });
}

/* ── Star alignment (main) ───────────────────────────────────────── */
function starAlignment(seqs, match, mismatch, gapOpen) {
  if (seqs.length === 1) return [{ id: seqs[0].id, aligned: seqs[0].seq }];
  if (seqs.length === 2) {
    const { alignA, alignB } = needlemanWunsch(seqs[0].seq, seqs[1].seq, match, mismatch, gapOpen);
    return [
      { id: seqs[0].id, aligned: alignA },
      { id: seqs[1].id, aligned: alignB },
    ];
  }

  const n = seqs.length;
  // Phase 1: find centre — n*(n-1)/2 pairwise NW
  const totals = new Array(n).fill(0);
  const totalPairs = (n * (n - 1)) / 2;
  let done = 0;
  let lastReport = 0;

  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const { score } = needlemanWunsch(seqs[i].seq, seqs[j].seq, match, mismatch, gapOpen);
      totals[i] += score;
      totals[j] += score;
      done++;
      // Report progress every 5%
      const pct = Math.floor((done / (totalPairs + n)) * 100);
      if (pct >= lastReport + 5) {
        lastReport = pct;
        self.postMessage({ type: 'progress', done, total: totalPairs + n });
      }
    }
  }

  const centreIdx = totals.indexOf(Math.max(...totals));
  const centreSeq = seqs[centreIdx].seq;

  // Phase 2: align each sequence against centre
  const pairAligns = seqs.map((s, idx) => {
    if (idx === centreIdx) return { centre: s.seq, other: s.seq };
    const { alignA, alignB } = needlemanWunsch(centreSeq, s.seq, match, mismatch, gapOpen);
    done++;
    const pct = Math.floor((done / (totalPairs + n)) * 100);
    if (pct >= lastReport + 5) {
      lastReport = pct;
      self.postMessage({ type: 'progress', done, total: totalPairs + n });
    }
    return { centre: alignA, other: alignB };
  });

  const mergedAligns = mergeStarAlignments(pairAligns, centreIdx);
  return seqs.map((s, idx) => ({ id: s.id, aligned: mergedAligns[idx] }));
}

/* ── Message handler ─────────────────────────────────────────────── */
self.onmessage = function (e) {
  const { seqs, matchScore, mismatchScore, gapOpen } = e.data;
  try {
    const alignedSeqs = starAlignment(seqs, matchScore, mismatchScore, gapOpen);
    self.postMessage({ type: 'result', alignedSeqs });
  } catch (err) {
    self.postMessage({ type: 'error', message: err.message });
  }
};
