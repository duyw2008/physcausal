"""
论文信任层级 — arXiv 不能直接当事实

层级:
  tier 2: 已发表+高引+有实验验证 → 可直接参与推理
  tier 3: arXiv 预印本 / 低引 / 无实验 → 严肃假说, 需独立验证
  tier 4: 单篇预印本 / 争议性结论 → 探索编码, 不参与推理

额外检查:
  - 如果已有定律与之冲突 → 标记为 dissonance, 不自动入库
  - 如果与已有定律一致 → 可以升级置信度
  - 源论文信息必须记录 (arxiv_id, authors, citations, published)
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json, os, time
from data_paths import data_path


_PAPER_TRACKER = data_path("paper_tracker.json")


def _load_tracker() -> Dict:
    try:
        with open(_PAPER_TRACKER) as f:
            return json.load(f)
    except:
        return {"papers": [], "claims": []}


def _save_tracker(tracker: Dict):
    with open(_PAPER_TRACKER, "w") as f:
        json.dump(tracker, f, ensure_ascii=False, indent=2)


def assess_trust(paper: Dict, claim: Dict) -> int:
    """
    评估一条论文断言的信任层级。

    规则:
      published + citations > 100            → tier 2
      published + citations > 10             → tier 2
      arXiv only, no citations               → tier 3
      arXiv only, contradicts existing laws  → tier 4 (标记冲突)
    """
    published = paper.get("published", False)
    citations = paper.get("citations", 0)
    arxiv_id = paper.get("arxiv_id", "")

    # 检查是否与已有定律冲突
    from physics.laws import library
    conflict = False
    for law in library.list_all():
        law_ins = set(law.inputs)
        law_outs = set(law.outputs)
        claim_ins = set(claim.get("inputs", []))
        claim_outs = set(claim.get("outputs", []))
        # 相同输入但输出矛盾 = 冲突
        if law_ins & claim_ins and law_outs & claim_outs:
            for fd_src, fd_dst in law.forbidden_directions:
                if (fd_src in claim_ins or fd_src in claim_outs) and \
                   (fd_dst in claim_ins or fd_dst in claim_outs):
                    conflict = True
                    break

    if conflict:
        return 4  # 冲突 → 探索编码, 不参与推理

    if published and citations > 100:
        return 2
    elif published and citations > 10:
        return 2
    else:
        return 3  # arXiv预印本 = tier 3


def register_paper_claim(paper: Dict, claim: Dict):
    """注册一篇论文的因果断言, 带信任层级和元数据"""
    tracker = _load_tracker()

    trust = assess_trust(paper, claim)

    entry = {
        "arxiv_id": paper.get("arxiv_id", ""),
        "title": paper.get("title", "")[:120],
        "authors": paper.get("authors", [])[:5],
        "published": paper.get("published", False),
        "citations": paper.get("citations", 0),
        "ingested_at": time.time(),
        "claim": claim,
        "trust_tier": trust,
    }

    tracker["papers"].append({
        "arxiv_id": paper.get("arxiv_id", ""),
        "title": paper.get("title", "")[:120],
        "claims_count": 1,
        "ingested_at": time.time(),
    })
    tracker["claims"].append(entry)
    _save_tracker(tracker)

    return trust


def verify_against_graph(claim: Dict) -> Dict:
    """
    将论文断言与现有因果图对撞验证。

    返回: {consistent, conflicting, novel}
    """
    from physics.laws import library

    ins = set(claim.get("inputs", []))
    outs = set(claim.get("outputs", []))

    consistent = []
    conflicting = []

    for law in library.list_all():
        law_ins = set(law.inputs)
        law_outs = set(law.outputs)
        if ins & law_ins and outs & law_outs:
            # 检查因果方向
            for c_src, c_dst in claim.get("causal_direction", []):
                for l_src, l_dst in law.causal_direction:
                    if c_src == l_src and c_dst == l_dst:
                        consistent.append(law.name)
                    elif c_src == l_dst and c_dst == l_src:
                        conflicting.append(law.name)

    novel = not consistent and not conflicting

    return {
        "consistent": consistent,
        "conflicting": conflicting,
        "novel": novel,
    }


def paper_trust_report() -> str:
    """论文信任追踪报告"""
    tracker = _load_tracker()
    papers = tracker.get("papers", [])
    claims = tracker.get("claims", [])

    lines = [f"═══ 论文信任追踪 ({len(papers)} 篇) ═══"]

    by_tier = {}
    for c in claims:
        t = c.get("trust_tier", 3)
        by_tier[t] = by_tier.get(t, 0) + 1

    lines.append(f"  tier 2 (确立): {by_tier.get(2, 0)}")
    lines.append(f"  tier 3 (假说): {by_tier.get(3, 0)}")
    lines.append(f"  tier 4 (冲突): {by_tier.get(4, 0)}")
    lines.append("")
    lines.append("  最近摄入:")
    for p in papers[-5:]:
        lines.append(f"  [{p.get('arxiv_id','?')}] {p['title'][:70]}")

    return "\n".join(lines)
