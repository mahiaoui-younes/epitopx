import re
from collections import Counter

lines = open('benchmark_500_results.txt', encoding='utf-16').readlines()
missed_bio = []
missed_core = []

for i, line in enumerate(lines):
    if 'Bio: missed' in line:
        m = re.search(r'Bio: missed \((\d+)%\)', line)
        if m:
            pct = int(m.group(1))
            for j in range(i-1, max(i-5,0), -1):
                em = re.search(r'Epitope: (\S+)', lines[j])
                if em:
                    missed_bio.append((em.group(1), pct))
                    break
    if 'Core: missed' in line:
        m = re.search(r'Core: missed \((\d+)%\)', line)
        if m:
            pct = int(m.group(1))
            for j in range(i-1, max(i-5,0), -1):
                em = re.search(r'Epitope: (\S+)', lines[j])
                if em:
                    missed_core.append((em.group(1), pct))
                    break

print(f"Bio missed: {len(missed_bio)}")
bio_zero = [e for e,p in missed_bio if p == 0]
bio_near = [e for e,p in missed_bio if 0 < p < 30]
bio_close = [e for e,p in missed_bio if p >= 30]
print(f"  0% overlap: {len(bio_zero)}")
print(f"  1-29%: {len(bio_near)}")
print(f"  30%+: {len(bio_close)}")

lens = [len(e) for e,_ in missed_bio]
print(f"  Avg length: {sum(lens)/len(lens):.1f}")
print(f"  Short (<=10): {sum(1 for l in lens if l<=10)}")
print(f"  Medium (11-15): {sum(1 for l in lens if 11<=l<=15)}")
print(f"  Long (>15): {sum(1 for l in lens if l>15)}")

# Amino acid composition of missed
aa = Counter()
for e,_ in missed_bio:
    for c in e: aa[c] += 1
total_aa = sum(aa.values())
print(f"  Top AAs: {[(k, round(v/total_aa,3)) for k,v in aa.most_common(10)]}")

# Hydrophobic fraction in missed
hydrophobic = set("AILMFWVP")
hydrophilic = set("DEKRNQHST")
h_fracs = []
p_fracs = []
for e,_ in missed_bio:
    hf = sum(1 for c in e if c in hydrophobic) / len(e)
    pf = sum(1 for c in e if c in hydrophilic) / len(e)
    h_fracs.append(hf)
    p_fracs.append(pf)
print(f"  Avg hydrophobic fraction: {sum(h_fracs)/len(h_fracs):.3f}")
print(f"  Avg hydrophilic fraction: {sum(p_fracs)/len(p_fracs):.3f}")
print(f"  High hydrophobic (>0.5): {sum(1 for f in h_fracs if f > 0.5)}")

# Close misses (30%+) - these are the ones we can potentially rescue
print(f"\nClose misses (30%+ overlap): {len(bio_close)}")
for e,p in bio_close[:20]:
    hf = sum(1 for c in e if c in hydrophobic) / len(e)
    print(f"  {e:25s} overlap={p}% hydrophobic={hf:.2f} len={len(e)}")

print(f"\nCore missed: {len(missed_core)}")
core_zero = sum(1 for _,p in missed_core if p == 0)
core_near = sum(1 for _,p in missed_core if 0 < p < 30)
core_close = sum(1 for _,p in missed_core if p >= 30)
print(f"  0%: {core_zero}, 1-29%: {core_near}, 30%+: {core_close}")
