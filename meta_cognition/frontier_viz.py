"""
前沿地图可视化 — HTML 交互图

稀疏区/尺度裂缝/断头路 → 彩色散点图
"""

from __future__ import annotations
import json, os, webbrowser


def generate_frontier_html() -> str:
    from meta_cognition.frontier import FrontierMap
    fm = FrontierMap()
    fm.build()

    sparse = fm.sparse_zones(min_domains=2)
    gaps = fm.scale_gaps()
    dead = fm.dead_ends()

    points = []
    # 稀疏区: x=缺席域数, y=频率, 大小=基础变量权重
    for z in sparse:
        from physics.laws import classify_variable
        cat = classify_variable(z["variable"])
        weight = {"fundamental": 12, "geometric": 10, "quantum": 8}.get(cat, 5)
        points.append({
            "x": len(z.get("domains_absent", [])),
            "y": z.get("frequency", 1),
            "label": z["variable"],
            "group": "sparse",
            "size": weight,
            "detail": f"缺席: {', '.join(z.get('domains_absent',[])[:3])}",
        })

    # 尺度裂缝
    for g in gaps:
        scales = {"classical": 1, "quantum": 2, "relativistic": 3}
        points.append({
            "x": scales.get(g["scale_a"], 1),
            "y": scales.get(g["scale_b"], 3),
            "label": g["variable"],
            "group": "gap",
            "size": 10,
            "detail": f"{g['scale_a']} ↔ {g['scale_b']}",
        })

    # 断头路
    for d in dead[:20]:
        points.append({
            "x": d.get("depth", 1),
            "y": d.get("score", 1) * 5,
            "label": d.get("dead_variable", "?")[:12],
            "group": "dead",
            "size": 6,
            "detail": f"from {d.get('start_variable','?')} depth={d.get('depth',0)}",
        })

    colors = {"sparse": "#50B86C", "gap": "#E8A838", "dead": "#D94A4A"}
    groups = {"sparse": len(sparse), "gap": len(gaps), "dead": len(dead)}

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports", "frontier_map.html"
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Frontier Map</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis/4.21.0/vis.min.js"></script>
<style>
  body {{ margin:0; background:#0d1117; color:#c9d1d9; font-family:monospace; }}
  #header {{ padding:12px 20px; background:#161b22; border-bottom:1px solid #30363d; }}
  #chart {{ width:100vw; height:calc(100vh-50px); }}
  .legend {{ position:fixed; bottom:10px; right:10px; background:#161b22; 
             padding:8px 12px; border-radius:6px; border:1px solid #30363d; font-size:11px; }}
</style></head><body>
<div id="header"><h2>PhysCausal Frontier Map <span>sparse:{groups['sparse']} gap:{groups['gap']} dead:{groups['dead']}</span></h2></div>
<div id="chart"></div>
<div class="legend">
  {"".join(f'<div><span style="background:{c};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:4px"></span> {g} ({n})</div>' for g,n,c in [('sparse',groups['sparse'],colors['sparse']),('gap',groups['gap'],colors['gap']),('dead',groups['dead'],colors['dead'])])}
</div>
<script>
var items = {json.dumps([{**p, "color": colors[p["group"]]} for p in points], ensure_ascii=False)};
var dataset = new vis.DataSet(items);
new vis.Graph2d(document.getElementById('chart'), dataset, {{
  style:'points', drawPoints:{{style:'circle',size:(item)=>item.size||5}},
  dataAxis:{{left:{{title:'Y'}}, bottom:{{title:'X'}}}},
  defaultGroup:'sparse',
  groups:{{sparse:{{content:'稀疏区'}},gap:{{content:'尺度裂缝'}},dead:{{content:'断头路'}}}},
  showMajorLabels:true, showMinorLabels:false,
  tooltip:(item)=>`<b>${{item.label}}</b><br>${{item.detail}}${{item.group}}`,
  height:'100%',
}});
</script></body></html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    return output_path
