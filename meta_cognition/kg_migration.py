"""
知识网络迁移 — 8个JSON → 统一图

每次启动时调用, 增量导入。已存在的节点跳过。
"""

from meta_cognition.knowledge_graph import kg
from data_paths import auto_laws_path, load_cv_summary
import json, os


def migrate_all():
    """将所有数据源 migration 到知识网络"""
    
    # 1. 定律 → 变量
    try:
        with open(auto_laws_path()) as f:
            laws = json.load(f)
    except:
        laws = []

    for law in laws:
        name = law.get("name", "unnamed")
        tier = law.get("confidence_tier", 4)
        domain = law.get("domain", "unknown")
        inputs = law.get("inputs", [])
        outputs = law.get("outputs", [])

        # 定律节点
        kg.add_node(f"law:{name}", "law", {
            "name": name, "tier": tier, "domain": domain,
            "inputs": inputs, "outputs": outputs,
            "note": law.get("_discovery_note", ""),
        })

        # 变量节点 + has_input/has_output 边
        for v in inputs:
            kg.add_node(f"var:{v}", "variable", {"name": v})
            kg.add_edge(f"var:{v}", f"law:{name}", "has_input")
        for v in outputs:
            kg.add_node(f"var:{v}", "variable", {"name": v})
            kg.add_edge(f"law:{name}", f"var:{v}", "has_output")

    # 2. 交叉验证
    cv = load_cv_summary()
    for r in cv:
        disc = r.get("discovery", "?")
        domain = r.get("target_domain", "?")
        passed = r.get("convergence_preserved", False)
        cv_id = f"cv:{disc}@{domain}"
        kg.add_node(cv_id, "cross_validation", {
            "discovery": disc, "domain": domain, "passed": passed,
        })
        kg.add_edge(f"law:{disc}", cv_id, "validated_in")

    # 3. 论文
    try:
        with open("data/paper_tracker.json") as f:
            tracker = json.load(f)
    except:
        tracker = {}
    for p in tracker.get("papers", []):
        aid = p.get("arxiv_id", "?")
        kg.add_node(f"paper:{aid}", "paper", {
            "title": p.get("title", ""), "arxiv_id": aid,
        })
    for c in tracker.get("claims", []):
        claim = c.get("claim", {})
        name = claim.get("name", "?")
        aid = c.get("arxiv_id", "?")
        kg.add_edge(f"paper:{aid}", f"law:{name}", "discovered_in")

    # 4. 类比
    try:
        from creative.causal_analogy import find_causal_analogies
        analogies = find_causal_analogies(max_chains=15, min_similarity=0.5)
        for a in analogies:
            va, vb = a["chain_a_start"], a["chain_b_start"]
            sim = a["similarity"]
            aid = f"analogy:{va}↔{vb}"
            kg.add_node(aid, "analogy", {"a": va, "b": vb, "similarity": sim})
            kg.add_edge(f"var:{va}", aid, "analogous_to")
            kg.add_edge(f"var:{vb}", aid, "analogous_to")
    except:
        pass

    # 5. 记忆
    try:
        with open("data/memory.json") as f:
            memories = json.load(f)
    except:
        memories = []
    for m in memories:
        mid = f"mem:{m.get('time',0)}"
        kg.add_node(mid, "memory", {"content": m.get("content",""), "tags": m.get("tags",[])})
        for tag in m.get("tags", []):
            kg.add_node(f"tag:{tag}", "tag", {"name": tag})
            kg.add_edge(mid, f"tag:{tag}", "tagged_as")

    kg.save()

    # 统计
    s = kg.stats()
    return (
        f"知识网络迁移完成\n"
        f"  节点: {s['nodes']} ({dict(s['node_types'])})\n"
        f"  边: {s['edges']} ({dict(s['edge_types'])})"
    )


def kg_query(node_id: str) -> str:
    """查询知识网络中的节点"""
    result = kg.query(node_id)
    if "error" in result:
        return result["error"]

    node = result["node"]
    lines = [f"═══ {node_id} ═══"]
    lines.append(f"  类型: {node['type']}")
    if node["data"]:
        for k, v in node["data"].items():
            if isinstance(v, str) and len(v) > 60:
                v = v[:60] + "..."
            elif isinstance(v, list):
                v = ", ".join(str(x) for x in v[:5])
            lines.append(f"  {k}: {v}")

    lines.append(f"\n  入边 ({result['incoming']}):")
    for target, etype in result["in_edges"][:10]:
        lines.append(f"    ← {target} [{etype}]")

    lines.append(f"  出边 ({result['outgoing']}):")
    for target, etype in result["out_edges"][:10]:
        lines.append(f"    → {target} [{etype}]")

    return "\n".join(lines)


def kg_stats_report() -> str:
    s = kg.stats()
    lines = ["═══ 知识网络 ═══"]
    lines.append(f"  节点: {s['nodes']}")
    for t, c in sorted(s["node_types"].items()):
        lines.append(f"    {t}: {c}")
    lines.append(f"  边: {s['edges']}")
    for t, c in sorted(s["edge_types"].items()):
        lines.append(f"    {t}: {c}")
    return "\n".join(lines)
