"""
自然语言 → 知识网络命令路由

让 Noether 听懂 "熵的上游是什么" 而不是 kg var:entropy
"""

from __future__ import annotations
from typing import Optional, Tuple


# ── 关键词 → 命令映射 ──

NL_ROUTES = [
    # 概念涌现
    (["概念", "簇", "聚类", "涌现", "自动发现"], "concept"),
    # 溯源
    (["溯源", "升级", "tier", "层级", "怎么升", "证据", "凭什么"], "trace"),
    # 矛盾
    (["矛盾", "冲突", "自洽", "检查", "有问题"], "contra"),
    # 上游 ("什么导致", "什么影响X")
    (["上游", "什么导致", "什么产生", "原因", "来自"], "upstream"),
    # 下游 ("X导致什么", "X影响什么")
    (["下游", "导致什么", "影响什么", "结果", "产生什么"], "downstream"),
    # 连接 ("X和Y的关系", "怎么连")
    (["关系", "连接", "怎么连", "路径", "桥接"], "connect"),
    # 变量查询 ("entropy 是什么")
    (["是什么", "连接什么", "有关", "连接到", "连到"], "query"),
]



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

def _cn_to_en(text: str) -> str:
    result = text
    for cn, en in CN_EN_VARS.items():
        if cn in result:
            result = result.replace(cn, en)
    return result


def parse_nl_query(text: str) -> Optional[Tuple[str, str]]:
    """
    从自然语言中解析知识网络查询。

    返回: (command_type, argument) 或 None
    """
    from meta_cognition.knowledge_graph import kg

    text = _cn_to_en(text)
    text_lower = text.lower()

    # 1. 检查关键词路由
    for keywords, cmd in NL_ROUTES:
        if any(kw in text_lower for kw in keywords):
            # 提取变量名: 查找知识网络中存在的变量
            for nid, nd in kg.nodes.items():
                if nd["type"] == "variable":
                    vname = nd["data"].get("name", "")
                    if vname and vname.lower() in text_lower:
                        if cmd == "trace":
                            # 找包含该变量的定律
                            for nid2, nd2 in kg.nodes.items():
                                if nd2["type"] == "law":
                                    all_v = nd2["data"].get("inputs", []) + nd2["data"].get("outputs", [])
                                    if vname in all_v:
                                        return ("trace", nd2["data"]["name"])
                        elif cmd in ("upstream", "downstream"):
                            return (cmd, f"var:{vname}")
                        elif cmd == "query":
                            return ("query", f"var:{vname}")
                        elif cmd == "connect":
                            # 查找第二个变量
                            for nid3, nd3 in kg.nodes.items():
                                if nd3["type"] == "variable" and nd3["data"]["name"] != vname:
                                    v2 = nd3["data"]["name"]
                                    if v2.lower() in text_lower:
                                        return ("connect", f"var:{vname}", f"var:{v2}")

            # 概念/矛盾/溯源 不需要变量参数
            if cmd == "concept":
                return ("concept", "")
            if cmd == "contra":
                return ("contra", "")
            if cmd == "trace":
                # 尝试从文本中找定律名
                for nid, nd in kg.nodes.items():
                    if nd["type"] == "law":
                        lname = nd["data"]["name"]
                        if lname.lower() in text_lower:
                            return ("trace", lname)

    # 2. 检查 "X 到 Y" / "X ↔ Y" 模式
    import re
    arrow_patterns = [
        r"(\w+)\s*[→↔\-→]\s*(\w+)",
        r"(\w+)\s*(?:和|与|到)\s*(\w+)\s*(?:的关系|怎么连|路径)",
    ]
    for pattern in arrow_patterns:
        m = re.search(pattern, text_lower)
        if m:
            v1, v2 = m.group(1), m.group(2)
            # 验证是否是知识网络中的变量
            v1_exists = any(nd["type"] == "variable" and nd["data"].get("name","").lower() == v1 
                          for nd in kg.nodes.values())
            v2_exists = any(nd["type"] == "variable" and nd["data"].get("name","").lower() == v2 
                          for nd in kg.nodes.values())
            if v1_exists and v2_exists:
                return ("connect", f"var:{v1}", f"var:{v2}")

    return None


def execute_nl_query(text: str) -> Optional[str]:
    """执行自然语言知识网络查询"""
    result = parse_nl_query(text)
    if not result:
        return None

    from meta_cognition.knowledge_graph import kg
    from meta_cognition.kg_migration import kg_query, migrate_all

    cmd = result[0]
    args = result[1:]

    if cmd == "concept":
        concepts = kg.emerge_concepts()
        lines = [f"═══ 概念涌现 ({len(concepts)} 个簇) ═══"]
        for c in concepts:
            lines.append(f"  [{c['domain']}] {c['name']} ({c['size']} vars)")
            lines.append(f"    核心: {', '.join(c['core'])}")
        return "\n".join(lines)

    elif cmd == "contra":
        contras = kg.detect_contradictions()
        reverse = [c for c in contras if c["type"] == "reverse_causality"]
        paper = [c for c in contras if c["type"] == "paper_vs_law"]
        if not reverse and not paper:
            return "无因果冲突。因果图自洽。"
        lines = [f"═══ 矛盾检测 ═══"]
        for c in reverse + paper:
            lines.append(f"  [{c['type']}] {c['message']}")
        return "\n".join(lines)

    elif cmd == "trace":
        result = kg.trace_tier(args[0])
        if "error" in result:
            return result["error"]
        lines = [f"═══ {args[0]} 溯源 ═══"]
        lines.append(f"  层级: tier {result['tier']}")
        lines.append(f"  路径: {result['upgrade_path']}")
        for cv in result.get("cross_validations", []):
            lines.append(f"    {'✓' if cv['passed'] else '✗'} {cv['domain']}")
        for p in result.get("papers", []):
            lines.append(f"    · {p}")
        return "\n".join(lines)

    elif cmd == "upstream":
        paths = kg.upstream(args[0])
        lines = [f"═══ {args[0]} 的上游 ═══"]
        for p in paths[:5]:
            lines.append(f"  {' ← '.join(p)}")
        return "\n".join(lines)

    elif cmd == "downstream":
        paths = kg.downstream(args[0])
        lines = [f"═══ {args[0]} 的下游 ═══"]
        for p in paths[:5]:
            lines.append(f"  {' → '.join(p)}")
        return "\n".join(lines)

    elif cmd == "connect":
        paths = kg.connect(args[0], args[1])
        lines = [f"═══ {args[0]} ↔ {args[1]} ═══"]
        lines.append(f"  路径: {len(paths)} 条")
        for p in paths[:5]:
            lines.append(f"    {' → '.join(p)}")
        return "\n".join(lines)

    elif cmd == "query":
        return kg_query(args[0])

    return None
