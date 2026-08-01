#!/usr/bin/env python3
"""导出费曼脑 3D 数据"""
import json, os, sys
from collections import Counter
sys.path.insert(0, '/home/duyw/physcausal')

from meta_cognition.evo_colony import EvoColony

colony = EvoColony()
snap_gen, snap_data = EvoColony.find_latest_snapshot()
if not snap_data:
    print("no snapshot")
    sys.exit(1)

colony.restore_from_snapshot(snap_data)

def classify(name):
    for kw, dom in {
        'force':'mechanics','mass':'mechanics','energy':'mechanics',
        'acceleration':'mechanics','momentum':'mechanics','velocity':'mechanics',
        'kinetic':'mechanics','action':'mechanics',
        'wavelength':'optics','frequency':'optics','photon':'optics',
        'optical':'optics','ringdown':'optics','wave':'optics',
        'current':'electromagnetism','voltage':'electromagnetism',
        'charge':'electromagnetism','field':'electromagnetism',
        'electric':'electromagnetism','magnetic':'electromagnetism',
        'lorentz':'electromagnetism',
        'temperature':'thermodynamics','entropy':'thermodynamics',
        'heat':'thermodynamics','thermal':'thermodynamics',
        'quantum':'quantum','wavefunction':'quantum','probability':'quantum',
        'spin':'quantum','planck':'quantum',
        'spacetime':'general_relativity','curvature':'general_relativity',
        'gravitational':'general_relativity','black_hole':'general_relativity',
        'relativistic':'general_relativity','geodesic':'general_relativity',
    }.items():
        if kw in name.lower():
            return dom
    return 'unknown'

DOMAIN_COLORS = {
    'mechanics': 0x4499cc, 'electromagnetism': 0xcc8844,
    'thermodynamics': 0xff6644, 'quantum': 0x8844cc,
    'general_relativity': 0xcc44cc, 'optics': 0x44cc88,
    'unknown': 0x555555,
}

cache = colony.graph._cache
cell_by_node = Counter(c.node for c in colony.cells)

nodes = []
for name, nd in cache.items():
    dom = classify(name)
    pop = cell_by_node.get(name, 0)
    deg = len(nd.get('effects', []))
    max_s = 0
    for eff in nd.get('effects', []):
        if isinstance(eff, (list, tuple)) and len(eff) >= 3:
            key = (name, eff[1])
            act = colony.synapse.activations.get(key, {})
            s_val = act.get('s', 0) if isinstance(act, dict) else 0
            if s_val > max_s: max_s = s_val
    depth = min(5, max(1, int(max_s * 2))) if max_s > 0 else 3
    size = max(0.5, min(3.0, 0.5 + pop * 0.02))
    nodes.append({'id': name, 'domain': dom, 'depth': depth,
                  'color': DOMAIN_COLORS.get(dom, 0x555555),
                  'size': size, 'pop': pop, 'deg': deg, 's': round(max_s, 2)})

edges_list = []
emergent_edges = []
for name, nd in cache.items():
    for eff in nd.get('effects', []):
        if isinstance(eff, (list, tuple)) and len(eff) >= 3:
            law, dst, dom = eff[0], eff[1], eff[2]
            key = (name, dst)
            act = colony.synapse.activations.get(key, {})
            s_val = act.get('s', 0) if isinstance(act, dict) else 0
            strength = min(2.0, max(0.05, s_val))
            opacity = min(0.7, max(0.05, s_val * 0.7))
            edge = {'s': name, 't': dst, 'strength': strength,
                    'color': 0xffd700 if dom == 'emergent' else 0x4488cc,
                    'opacity': 0.8 if dom == 'emergent' else opacity}
            if dom == 'emergent':
                emergent_edges.append(edge)
            elif s_val > 0.1:
                edges_list.append(edge)

output = {'gen': colony.generation, 'cells': len(colony.cells),
          'nodes': nodes, 'edges': edges_list, 'emergent_edges': emergent_edges,
          'emergent_count': len(emergent_edges), 'edge_count': len(edges_list)}

out_path = '/home/duyw/physcausal/reports/brain_data.json'
with open(out_path, 'w') as f:
    json.dump(output, f)
print(f"OK: {len(nodes)} nodes, {len(edges_list)}+{len(emergent_edges)} edges, gen={colony.generation}")
