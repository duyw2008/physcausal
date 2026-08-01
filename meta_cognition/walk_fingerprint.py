"""Walk 形状指纹 — 压缩域序列+边类型序列为紧凑可共振字符串"""

def walk_fingerprint(walk: list) -> str:
    """压缩 walk 形状: 域序列 + 边类型序列 → 紧凑指纹"""
    if len(walk) < 2:
        return ""
    domains = []
    edge_types = []
    for step in walk:
        if len(step) >= 4:
            dom = step[3][:8]
            domains.append(dom)
        if len(step) >= 2:
            law = step[1]
            if "composed" in str(law) or "COMPOSE" in str(law):
                edge_types.append("cmp")
            elif "hebbian" in str(law):
                edge_types.append("heb")
            elif "math_verified" in str(law) or "derive" in str(law):
                edge_types.append("mth")
            elif "feed" in str(law) or "arxiv" in str(law):
                edge_types.append("feed")
            elif "seed" in str(law) or "chaos" in str(law):
                edge_types.append("chn")
            else:
                edge_types.append("law")
    dom_key = ",".join(domains[:3])
    typ_key = ",".join(edge_types[:3])
    return f"D:{dom_key}|T:{typ_key}"
