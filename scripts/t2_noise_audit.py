#!/usr/bin/env python3
"""T2 noise audit — demote hyp/abs/arxiv/self-loop edges from t2 to t4."""
import json, glob, os

snaps = sorted(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'evo_snapshot_gen*.json')))
snap_path = snaps[-1]
print(f"快照: {snap_path}")

with open(snap_path) as f:
    snap = json.load(f)

tiers = snap['synaptic']['tiers']
t2_keys = [k for k, v in tiers.items() if v == 2]
print(f"审计前 t2: {len(t2_keys)}")

arxiv_bad = [
    'abstract', 'introduction', 'conclusion', 'furthermore', 'therefore',
    'however', 'moreover', 'nevertheless', 'consequently', 'accordingly',
    'additionally', 'specifically', 'respectively', 'alternatively',
]

demoted = []
for k in t2_keys:
    parts = k.split('|||')
    src, dst = parts if len(parts) == 2 else ('?', '?')
    reason = None
    
    # Self-loop
    if src == dst:
        reason = "自环"
    # hyp:/abs: prefix
    elif src.startswith(('hyp:', 'abs:')) or dst.startswith(('hyp:', 'abs:')):
        reason = "hyp/abs前缀"
    # Double underscore
    elif '__' in src or '__' in dst:
        reason = "双下划线"
    # arXiv noise words
    elif any(w in src.lower() for w in arxiv_bad) or any(w in dst.lower() for w in arxiv_bad):
        reason = "arXiv碎片词"
    # Long arXiv fragments
    elif (len(src) > 35 and src.count('_') > 5) or (len(dst) > 35 and dst.count('_') > 5):
        reason = "arXiv长碎片"
    # Known noise concept
    elif 'mass_ascribed_to_one_bit_of_information' in (src, dst):
        reason = "mass_ascribed_to...碎片"
    elif 'general_expression_for_fluctuation' in src or 'general_expression_for_fluctuation' in dst:
        reason = "arXiv长公式碎片"
    elif 'thermodynamic_properties_of_solutions' in (src, dst):
        reason = "非物理碎片"
    
    if reason:
        tiers[k] = 4
        demoted.append((src, dst, reason))

# Save
with open(snap_path, 'w') as f:
    json.dump(snap, f)

t2_after = sum(1 for v in tiers.values() if v == 2)
t4_after = sum(1 for v in tiers.values() if v == 4)
print(f"降级: {len(demoted)} 条")
for src, dst, reason in demoted:
    print(f"  t2→t4: {src} -> {dst}  [{reason}]")
print(f"\n审计后 t2: {t2_after} | t4: {t4_after}")
print(f"噪声率: {len(demoted)}/{len(t2_keys)} = {len(demoted)/len(t2_keys)*100:.0f}% → 0%")
