"""
前沿地图可视化 — 纯 SVG 散点图 (无 CDN 依赖)

稀疏区/尺度裂缝/断头路 → 三色散点 + 坐标轴 + 悬停提示
"""

from __future__ import annotations
import json, os


def generate_frontier_html() -> str:
    from meta_cognition.frontier import FrontierMap
    fm = FrontierMap()
    fm.build()

    sparse = fm.sparse_zones(min_domains=2)
    gaps = fm.scale_gaps()
    dead = fm.dead_ends()

    # === 数据点 ===
    points = []  # {cx, cy, r, label, group, detail}

    for z in sparse:
        points.append({
            "cx": len(z.get("domains_absent", [])),
            "cy": z.get("frequency", 1),
            "r": 6,
            "label": z["variable"],
            "group": "sparse",
            "detail": f"缺席: {', '.join(z.get('domains_absent', [])[:3])}",
        })

    scales = {"classical": 1, "quantum": 2, "relativistic": 3}
    for g in gaps:
        points.append({
            "cx": scales.get(g["scale_a"], 1),
            "cy": scales.get(g["scale_b"], 3),
            "r": 7,
            "label": g["variable"],
            "group": "gap",
            "detail": f"{g['scale_a']} \u2194 {g['scale_b']}",
        })

    for d in dead[:20]:
        points.append({
            "cx": d.get("depth", 1),
            "cy": d.get("score", 1) * 5,
            "r": 5,
            "label": d.get("dead_variable", "?")[:12],
            "group": "dead",
            "detail": f"from {d.get('start_variable', '?')} depth={d.get('depth', 0)}",
        })

    color_map = {"sparse": "#50B86C", "gap": "#E8A838", "dead": "#D94A4A"}
    group_counts = {"sparse": len(sparse), "gap": len(gaps), "dead": len(dead)}

    # === 坐标计算 ===
    xs = [p["cx"] for p in points]
    ys = [p["cy"] for p in points]
    x_min, x_max = min(xs) - 1, max(xs) + 1
    y_min, y_max = min(ys) - 1, max(ys) + 1

    W, H = 800, 520
    margin = {"top": 30, "right": 40, "bottom": 50, "left": 60}
    pw = W - margin["left"] - margin["right"]
    ph = H - margin["top"] - margin["bottom"]

    def tx(x):
        return margin["left"] + (x - x_min) / (x_max - x_min) * pw

    def ty(y):
        return margin["top"] + ph - (y - y_min) / (y_max - y_min) * ph

    # === 坐标轴刻度 ===
    x_ticks = list(range(int(x_min), int(x_max) + 1, max(1, (int(x_max) - int(x_min)) // 8)))
    y_ticks = list(range(int(y_min), int(y_max) + 1, max(1, (int(y_max) - int(y_min)) // 6)))

    axis_lines = f'<line x1="{margin["left"]}" y1="{margin["top"]}" x2="{margin["left"]}" y2="{H - margin["bottom"]}" stroke="#30363d" stroke-width="1"/>'
    axis_lines += f'<line x1="{margin["left"]}" y1="{H - margin["bottom"]}" x2="{W - margin["right"]}" y2="{H - margin["bottom"]}" stroke="#30363d" stroke-width="1"/>'

    tick_marks = ""
    for t in x_ticks:
        x = tx(t)
        tick_marks += f'<line x1="{x}" y1="{H - margin["bottom"]}" x2="{x}" y2="{H - margin["bottom"] + 5}" stroke="#30363d" stroke-width="1"/>'
        tick_marks += f'<text x="{x}" y="{H - margin["bottom"] + 20}" fill="#8b949e" font-size="11" text-anchor="middle">{t}</text>'
    for t in y_ticks:
        y = ty(t)
        tick_marks += f'<line x1="{margin["left"]}" y1="{y}" x2="{margin["left"] - 5}" y2="{y}" stroke="#30363d" stroke-width="1"/>'
        tick_marks += f'<text x="{margin["left"] - 10}" y="{y + 4}" fill="#8b949e" font-size="11" text-anchor="end">{t}</text>'

    axis_labels = (
        f'<text x="{margin["left"] + pw / 2}" y="{H - 4}" fill="#8b949e" font-size="12" text-anchor="middle">缺席域数 / 深度</text>'
        f'<text x="14" y="{margin["top"] + ph / 2}" fill="#8b949e" font-size="12" text-anchor="middle" transform="rotate(-90,14,{margin["top"] + ph / 2})">频率 / 得分</text>'
    )

    # === 散点 ===
    circles = ""
    tooltips = ""
    for i, p in enumerate(points):
        x, y, r = tx(p["cx"]), ty(p["cy"]), p["r"]
        c = color_map[p["group"]]
        circles += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{c}" opacity="0.85" stroke="{c}" stroke-width="1" class="dot" data-group="{p["group"]}" data-idx="{i}"/>'

        tooltips += (
            f'<div class="tip" id="tip-{i}" style="left:{x:.1f}px;top:{y - r - 30:.1f}px">'
            f'<b>{p["label"]}</b><br>{p["detail"]}<br><span style="color:{c}">{p["group"]}</span>'
            f'</div>'
        )

    # === 图例 ===
    legend_items = "".join(
        f'<span style="display:inline-flex;align-items:center;margin-right:14px">'
        f'<span style="background:{color_map[g]};display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px"></span>'
        f'{g} ({n})</span>'
        for g, n in [("sparse", group_counts["sparse"]), ("gap", group_counts["gap"]), ("dead", group_counts["dead"])]
    )

    html = f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="utf-8"><title>Frontier Map — PhysCausal</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#0d1117; color:#c9d1d9; font-family:monospace; }}
#header {{ padding:12px 20px; background:#161b22; border-bottom:1px solid #30363d; }}
#header h2 {{ font-size:15px; font-weight:400; color:#58a6ff; }}
#header span {{ color:#8b949e; font-size:12px; margin-left:8px; }}
#container {{ position:relative; width:{W}px; height:{H}px; margin:12px auto; }}
svg {{ display:block; }}
.dot {{ cursor:pointer; transition:r 0.15s; }}
.dot:hover {{ r: 9; opacity:1; }}
.tip {{ display:none; position:absolute; background:#21262d; color:#c9d1d9; 
        font-size:11px; padding:6px 10px; border-radius:5px; border:1px solid #30363d;
        white-space:nowrap; pointer-events:none; z-index:10; transform:translate(-50%,-100%); }}
.tip.show {{ display:block; }}
.dot:hover + .tip {{ display:block; }}
#legend {{ text-align:center; padding:6px 0 14px; font-size:12px; color:#8b949e; }}
</style></head>
<body>
<div id="header">
  <h2>PhysCausal Frontier Map
    <span>sparse:{group_counts["sparse"]} gap:{group_counts["gap"]} dead:{group_counts["dead"]}</span>
  </h2>
</div>
<div id="container">
  <svg viewBox="0 0 {W} {H}" width="{W}" height="{H}">
    {axis_lines}
    {tick_marks}
    {axis_labels}
    {circles}
  </svg>
  {tooltips}
</div>
<div id="legend">{legend_items}</div>
<script>
(function() {{
  const dots = document.querySelectorAll('.dot');
  let active = null;
  dots.forEach(d => {{
    d.addEventListener('mouseenter', function() {{
      const idx = this.dataset.idx;
      const tip = document.getElementById('tip-' + idx);
      if (tip) {{ tip.classList.add('show'); active = tip; }}
    }});
    d.addEventListener('mouseleave', function() {{
      if (active) {{ active.classList.remove('show'); active = null; }}
    }});
  }});
}})();
</script>
</body></html>"""

    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports", "frontier_map.html"
    )
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(html)

    return output_path
