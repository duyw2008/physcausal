"""
自然语言 → 知识网络命令路由
"""

from __future__ import annotations
from typing import Optional, Tuple

CN_EN_VARS = {
    "熵": "entropy", "温度": "temperature", "速度": "velocity",
    "质量": "mass", "能量": "energy", "动量": "momentum", "时间": "time",
    "相位": "phase", "信息": "information", "动能": "kinetic_energy",
    "阻力": "drag_force", "退相干": "decoherence", "耗散": "dissipation",
    "曲率": "spacetime_curvature", "测地线": "geodesic_path",
    "混合态": "mixed_state", "坍缩": "collapse_probability",
    "规范场": "gauge_field", "波长": "wavelength", "频率": "frequency",
    "额外维": "compact_dimension", "纠缠": "entanglement",
    "电流": "current", "电压": "voltage", "电荷": "charge",
    "压力": "pressure", "体积": "volume", "密度": "density",
    "对称": "symmetry", "破缺": "broken_symmetry",
}

CONCEPT_TO_VARS = {
    "decoherence": ["environment_coupling", "mixed_state", "phase_coherence"],
    "dissipation": ["drag_force", "kinetic_energy_loss", "entropy"],
    "退相干": ["environment_coupling", "mixed_state", "phase_coherence"],
    "耗散": ["drag_force", "kinetic_energy_loss", "entropy"],
}

NL_ROUTES = [
    (["概念", "簇", "聚类", "涌现"], "concept"),
    (["溯源", "升级", "tier", "层级"], "trace"),
    (["矛盾", "冲突", "自洽"], "contra"),
    (["上游", "什么导致", "什么产生", "原因"], "upstream"),
    (["下游", "导致什么", "影响什么", "结果"], "downstream"),
    (["关系", "连接", "怎么连", "路径", "桥接"], "connect"),
    (["是什么", "连接什么", "有关", "连接到"], "query"),
]


def _cn_to_en(text: str) -> str:
    for cn, en in CN_EN_VARS.items():
        if cn in text:
            text = text.replace(cn, en)
    return text


def parse_nl_query(text: str) -> Optional[Tuple]:
    from meta_cognition.knowledge_graph import kg

    text = _cn_to_en(text)
    text_lower = text.lower()

    # 1. 关键词路由
    for keywords, cmd in NL_ROUTES:
        if not any(kw in text_lower for kw in keywords):
            continue
        # 找变量
        for nid, nd in kg.nodes.items():
            if nd["type"] != "variable":
                continue
            vname = nd["data"].get("name", "")
            if not vname or vname.lower() not in text_lower:
                continue

            if cmd == "trace":
                for nid2, nd2 in kg.nodes.items():
                    if nd2["type"] == "law":
                        if vname in nd2["data"].get("inputs", []) + nd2["data"].get("outputs", []):
                            return ("trace", nd2["data"]["name"])
            elif cmd in ("upstream", "downstream", "query"):
                return (cmd, f"var:{vname}")
            elif cmd == "connect":
                # 找第二个变量或概念
                for nid3, nd3 in kg.nodes.items():
                    if nd3["type"] == "variable":
                        v2 = nd3["data"]["name"]
                        if v2 != vname and v2.lower() in text_lower:
                            return ("connect", f"var:{vname}", f"var:{v2}")
                # 概念回退
                for cname, vars_list in CONCEPT_TO_VARS.items():
                    if cname in text_lower:
                        return ("connect", f"var:{vars_list[0]}", f"var:{vname}")

        # 无变量参数的命令
        if cmd == "concept":
            return ("concept",)
        if cmd == "contra":
            return ("contra",)

    # 2. "X → Y" 模式
    import re
    m = re.search(r"(\w+)\s*[→↔\-]\s*(\w+)", text_lower)
    if m:
        v1, v2 = m.group(1), m.group(2)
        v1_ok = any(nd["type"] == "variable" and nd["data"].get("name", "").lower() == v1 for nd in kg.nodes.values())
        v2_ok = any(nd["type"] == "variable" and nd["data"].get("name", "").lower() == v2 for nd in kg.nodes.values())
        if v1_ok and v2_ok:
            return ("connect", f"var:{v1}", f"var:{v2}")

    return None


def execute_nl_query(text: str) -> Optional[str]:
    result = parse_nl_query(text)
    if not result:
        return None

    from meta_cognition.knowledge_graph import kg
    from meta_cognition.kg_migration import kg_query

    cmd = result[0]
    args = result[1:]

    if cmd == "concept":
        concepts = kg.emerge_concepts()
        lines = [f"概念涌现 ({len(concepts)} 个簇):"]
        for c in concepts:
            lines.append(f"  [{c['domain']}] {c['name']} ({c['size']} vars)")
        return "\n".join(lines)

    if cmd == "contra":
        contras = kg.detect_contradictions()
        bad = [c for c in contras if c["type"] in ("reverse_causality", "paper_vs_law")]
        if not bad:
            return "因果图自洽, 无反向冲突。"
        lines = ["矛盾检测:"]
        for c in bad:
            lines.append(f"  [{c['type']}] {c['message']}")
        return "\n".join(lines)

    if cmd == "trace":
        r = kg.trace_tier(args[0])
        if "error" in r:
            return r["error"]
        lines = [f"{args[0]} 溯源: tier {r['tier']}"]
        lines.append(f"  {r['upgrade_path']}")
        for cv in r.get("cross_validations", []):
            lines.append(f"    {'✓' if cv['passed'] else '✗'} {cv['domain']}")
        for p in r.get("papers", []):
            lines.append(f"    · {p}")
        return "\n".join(lines)

    if cmd == "upstream":
        paths = kg.upstream(args[0])
        lines = [f"{args[0]} 的上游 ({len(paths)} 条):"]
        for p in paths[:5]:
            lines.append(f"  {' ← '.join(p)}")
        return "\n".join(lines)

    if cmd == "downstream":
        paths = kg.downstream(args[0])
        lines = [f"{args[0]} 的下游 ({len(paths)} 条):"]
        for p in paths[:5]:
            lines.append(f"  {' → '.join(p)}")
        return "\n".join(lines)

    if cmd == "connect":
        paths = kg.connect(args[0], args[1])
        lines = [f"{args[0]} ↔ {args[1]} ({len(paths)} 条路径):"]
        for p in paths[:5]:
            lines.append(f"  {' → '.join(p)}")
        if not paths:
            lines.append("  知识网络中无直接路径。")
        return "\n".join(lines)

    if cmd == "query":
        return kg_query(args[0])

    return None
