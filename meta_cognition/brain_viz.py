"""
诺特脑图可视化 — 细胞殖民地交互图
"""

from __future__ import annotations
import json, os


def generate_brain_html() -> str:
    from meta_cognition.cell_colony import get_colony, _build_graph
    colony = get_colony()
    graph = _build_graph()

    # 统计每个节点的细胞
    cells_by_node = {}
    from collections import Counter
    for cell in colony.cells:
        n = cell.node
        if n not in cells_by_node:
            cells_by_node[n] = []
        cells_by_node[n].append(cell.specialization or "stem")

    # 特殊化颜色
    spec_colors = {
        "audit": "#f85149",
        "bridge": "#58a6ff",
        "extend": "#3fb950",
        "analogy": "#d2a8ff",
        "stem": "#8b949e",
    }

    # 构建节点和边
    nodes = []
    edges = []
    node_ids = {}
    
    # 添加因果图中有细胞的节点
    for var, specs in cells_by_node.items():
        nid = len(node_ids)
        node_ids[var] = nid
        counts = Counter(specs)
        dominant = counts.most_common(1)[0][0]
        color = spec_colors.get(dominant, "#8b949e")
        title = f"{var} ({len(specs)}细胞: {dict(counts)})"
        nodes.append({
            "id": nid, "label": var, "color": color,
            "title": title, "value": len(specs),
            "font": {"size": max(10, min(18, 10 + len(specs)))},
        })

    # 因果边
    for var, node in graph.items():
        if var in node_ids:
            for _, dst, _ in node["effects"]:
                if dst in node_ids:
                    edges.append({
                        "from": node_ids[var], "to": node_ids[dst],
                        "color": {"color": "#21262d", "highlight": "#30363d"},
                        "arrows": "to", "width": 0.5,
                    })

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Noether Brain Map</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:monospace; overflow:hidden; }}
#header {{ padding:8px 16px; background:#161b22; border-bottom:1px solid #30363d; font-size:12px; }}
#header span {{ margin-right:16px; }}
#graph {{ width:100vw; height:calc(100vh - 36px); }}
.legend {{ position:fixed; bottom:10px; right:10px; background:#161b22; 
           padding:6px 10px; border-radius:4px; border:1px solid #30363d; font-size:10px; }}
</style></head>
<body>
<div id="header">
  <span>🧠 诺特脑图</span>
  <span>世代:{colony.generation}</span>
  <span>细胞:{len(colony.cells)}/{colony.MAX_CELLS}</span>
  <span>发现:{colony.total_discoveries}</span>
</div>
<div id="graph"></div>
<div class="legend">
  <div style="color:#f85149">■ 审计(audit)</div>
  <div style="color:#58a6ff">■ 桥接(bridge)</div>
  <div style="color:#3fb950">■ 扩展(extend)</div>
  <div style="color:#d2a8ff">■ 类比(analogy)</div>
  <div style="color:#8b949e">■ 干细胞(stem)</div>
</div>
<script>
var nodes = new vis.DataSet({json.dumps(nodes, ensure_ascii=False)});
var edges = new vis.DataSet({json.dumps(edges, ensure_ascii=False)});
new vis.Network(document.getElementById('graph'), {{nodes:nodes, edges:edges}}, {{
  physics: {{ stabilization: {{ iterations: 100 }} }},
  nodes: {{ shape:'dot', scaling:{{min:8, max:40}} }},
  edges: {{ smooth:false }},
  interaction: {{ hover:true }},
}});
</script></body></html>"""

    output = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports", "brain_map.html"
    )
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        f.write(html)
    return output
