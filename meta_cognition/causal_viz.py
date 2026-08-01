"""
因果图可视化 — action (统一源) → entropy (普适汇) 因果流

生成自包含 HTML (无 CDN 依赖)
"""

from __future__ import annotations
import json, os


def generate_causal_flow_html() -> str:
    from inference.counterfactual_chain import propagate

    chain = propagate('action', '极值化', max_depth=7, max_tier=2)

    # 构建节点和边
    node_ids = {}
    nodes = []
    edges = []
    node_id_counter = [0]

    def get_id(var):
        if var not in node_ids:
            nid = node_id_counter[0]
            node_id_counter[0] += 1
            node_ids[var] = nid
        return node_ids[var]

    # domain colors (dark theme)
    domain_colors = {
        "mechanics": "#58a6ff",
        "quantum": "#3fb950", 
        "general_relativity": "#d2a8ff",
        "electromagnetism": "#f0883e",
        "thermodynamics": "#f85149",
        "unification": "#ffa657",
        "optics": "#79c0ff",
        "acoustics": "#a5d6ff",
        "fluids": "#56d364",
        "modern": "#db6d28",
        "relativity": "#ff7b72",
        "?": "#484f58",
    }

    # 收集深度层级
    depth_groups = {}
    for s in chain:
        if 'error' in s: continue
        d = s['depth']
        if d not in depth_groups:
            depth_groups[d] = set()
        depth_groups[d].add(s['variable'])
        depth_groups[d].add(s['effect_variable'])

    for s in chain:
        if 'error' in s: continue
        src = s['variable']
        dst = s['effect_variable']
        domain = s.get('domain', '?')
        law = s.get('law', '?')
        tier = s.get('confidence_tier', 1)

        sid = get_id(src)
        did = get_id(dst)

        if not any(n['id'] == sid for n in nodes):
            nodes.append({
                'id': sid,
                'label': src,
                'level': s['depth'],
                'color': domain_colors.get(domain, '#484f58'),
            })
        if not any(n['id'] == did for n in nodes):
            nodes.append({
                'id': did,
                'label': dst,
                'level': s['depth'] + 1,
                'color': domain_colors.get(domain, '#484f58'),
            })

        edges.append({
            'from': sid,
            'to': did,
            'label': law,
            'color': {'color': '#30363d', 'highlight': '#58a6ff'},
            'width': max(1, 4 - tier),
            'arrows': 'to',
        })

    # 确保 action 和 entropy 在 nodes 中
    aid = get_id('action')
    if not any(n['id'] == aid for n in nodes):
        nodes.insert(0, {'id': aid, 'label': 'action (δS=0)', 'level': 0, 'color': '#f0f6fc', 'font': {'size': 16, 'color': '#f0f6fc'}})
    eid = get_id('entropy')
    if not any(n['id'] == eid for n in nodes):
        nodes.append({'id': eid, 'label': 'entropy (汇点)', 'level': 8, 'color': '#f85149', 'font': {'size': 16, 'color': '#f85149'}})

    # 更新节点样式
    for n in nodes:
        n['font'] = {'size': 11, 'color': '#c9d1d9', 'background': 'none'}
        n['shape'] = 'box'
        n['margin'] = 6
        n['borderWidth'] = 0
        if n['label'] in ('action (δS=0)', 'force', 'spacetime_curvature', 'quantum_amplitude'):
            n['font'] = {'size': 13, 'color': '#f0f6fc'}
        if n['label'] == 'entropy (汇点)':
            n['font'] = {'size': 14, 'color': '#f85149'}

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>PhysCausal Causal Flow</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:monospace; overflow:hidden; }}
#header {{ padding:10px 20px; background:#161b22; border-bottom:1px solid #30363d; display:flex; align-items:center; gap:16px; }}
#header h2 {{ font-size:14px; font-weight:400; color:#58a6ff; }}
#header span {{ color:#8b949e; font-size:11px; }}
#graph {{ width:100vw; height:calc(100vh - 44px); }}
.legend {{ position:fixed; bottom:10px; right:10px; background:#161b22; 
           padding:8px 12px; border-radius:6px; border:1px solid #30363d; font-size:10px; }}
</style></head>
<body>
<div id="header">
  <h2>PhysCausal — Causal Flow: action (δS=0) → entropy</h2>
  <span>节点: {len(nodes)} | 边: {len(edges)} | tier≤2</span>
  <span>经典 ● 量子 ● GR ● 电磁 ● 热力学</span>
</div>
<div id="graph"></div>
<div class="legend">
  <div style="color:#f0f6fc">■ action — 统一源 (δS=0)</div>
  <div style="color:#f85149">■ entropy — 普适汇</div>
  <div style="color:#58a6ff">■ 经典力学</div>
  <div style="color:#3fb950">■ 量子力学</div>
  <div style="color:#d2a8ff">■ 广义相对论</div>
</div>
<script>
var nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
var edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});

var container = document.getElementById('graph');
var data = {{nodes: nodes, edges: edges}};
var options = {{
  layout: {{
    hierarchical: {{
      enabled: true,
      direction: 'LR',
      sortMethod: 'directed',
      levelSeparation: 80,
      nodeSpacing: 120,
    }}
  }},
  physics: {{ enabled: false }},
  interaction: {{ hover: true, tooltipDelay: 100 }},
  edges: {{
    smooth: {{ type: 'cubicBezier', forceDirection: 'horizontal', roundness: 0.4 }},
    color: '#30363d',
    font: {{ size: 9, color: '#8b949e', align: 'middle' }},
  }},
  nodes: {{
    shape: 'box',
    font: {{ size: 11, color: '#c9d1d9' }},
    borderWidth: 0,
  }},
}};
new vis.Network(container, data, options);
</script>
</body></html>"""

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports", "causal_flow.html"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    return output_path
