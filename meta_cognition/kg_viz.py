"""
知识网络可视化 — HTML 交互图

生成带 vis.js 的交互式知识图谱,
按类型着色, 可拖拽, 可缩放。
"""

from __future__ import annotations
from typing import Dict, List
import json, os, webbrowser


COLORS = {
    "law": "#4A90D9",
    "variable": "#50B86C",
    "cross_validation": "#E8A838",
    "paper": "#D94A4A",
    "analogy": "#9B59B6",
    "memory": "#E67E22",
    "tag": "#95A5A6",
}


def generate_html(output_path: str = None) -> str:
    """生成交互式知识网络 HTML"""
    from meta_cognition.knowledge_graph import kg
    from meta_cognition.kg_migration import migrate_all
    migrate_all()

    if output_path is None:
        output_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "reports", "knowledge_graph.html"
        )

    nodes_data = []
    edges_data = []

    # 节点
    for nid, nd in kg.nodes.items():
        ntype = nd["type"]
        label = nid.replace("var:", "").replace("law:", "").replace("paper:", "")
        label = label[:25]
        color = COLORS.get(ntype, "#999")
        nodes_data.append({
            "id": nid, "label": label, "group": ntype,
            "color": color, "title": f"{ntype}: {label}",
        })

    # 边
    for src, dst, etype in kg.edges:
        edges_data.append({"from": src, "to": dst, "label": etype, "arrows": "to"})

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Noether Knowledge Graph</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<link href="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.css" rel="stylesheet">
<style>
  body {{ margin: 0; background: #0d1117; color: #c9d1d9; font-family: monospace; }}
  #header {{ padding: 12px 20px; background: #161b22; border-bottom: 1px solid #30363d; }}
  #header h2 {{ margin: 0; font-size: 16px; }}
  #header span {{ font-size: 12px; color: #8b949e; }}
  #mynetwork {{ width: 100vw; height: calc(100vh - 50px); }}
  .legend {{ position: fixed; bottom: 10px; right: 10px; background: #161b22; 
             padding: 8px 12px; border-radius: 6px; border: 1px solid #30363d; font-size: 11px; }}
  .legend span {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 4px; }}
</style></head><body>
<div id="header">
  <h2>Noether 知识网络 <span>{len(nodes_data)} 节点 · {len(edges_data)} 边</span></h2>
</div>
<div id="mynetwork"></div>
<div class="legend">
  {"".join(f'<div><span style="background:{c}"></span> {t} ({sum(1 for n in nodes_data if n["group"]==t)})</div>' for t, c in COLORS.items())}
</div>
<script>
var nodes = new vis.DataSet({json.dumps(nodes_data, ensure_ascii=False)});
var edges = new vis.DataSet({json.dumps(edges_data, ensure_ascii=False)});
var container = document.getElementById('mynetwork');
var data = {{ nodes: nodes, edges: edges }};
var options = {{
  physics: {{ solver: 'forceAtlas2Based', forceAtlas2Based: {{ gravitationalConstant: -30 }} }},
  edges: {{ smooth: {{ type: 'continuous' }}, color: '#30363d' }},
  groups: {{
    law: {{ shape: 'box', color: '{COLORS["law"]}' }},
    variable: {{ shape: 'dot', color: '{COLORS["variable"]}', size: 15 }},
    analogy: {{ shape: 'diamond', color: '{COLORS["analogy"]}' }},
    paper: {{ shape: 'triangle', color: '{COLORS["paper"]}' }},
  }}
}};
new vis.Network(container, data, options);
</script></body></html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    return output_path


def open_viz():
    path = generate_html()
    webbrowser.open(f"file://{path}")
    return f"知识网络可视化: {path}\n节点: {len(kg.nodes)} 边: {len(kg.edges)}"
