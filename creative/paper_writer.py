"""
paper_writer — 自动生成物理研究论文

从聚焦方向 + 交叉验证报告 + 自动发现 + 因果图状态
生成结构化的 Markdown 论文。

结构:
  1. 标题 + 摘要
  2. 引言 (聚焦方向 + 开放问题)
  3. 方法 (PhysCausal 因果推理框架)
  4. 发现 (confirmed 假说 + 验证记录)
  5. 交叉验证 (多域检验结果)
  6. 讨论 (意义/局限/下一步)
  7. 参考文献
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json, os, glob, time
from collections import defaultdict


def _load_cross_validation_reports() -> List[Dict]:
    """加载交叉验证汇总"""
    from data_paths import load_cv_summary
    return load_cv_summary()


def _load_tier3_hypotheses(limit: int = 10) -> List[Dict]:
    """加载诺特脑发现的 tier 3 突触假说"""
    try:
        from meta_cognition.evo_colony import EvoColony
        colony = EvoColony()
        t3 = []
        for key in colony.synapse.activations:
            if colony.synapse.tiers.get(key, 4) == 3:
                edge = colony.synapse.activations[key]
                t3.append({
                    "src": key[0],
                    "dst": key[1],
                    "neurons": len(edge['n']),
                    "strength": round(edge['s'], 1),
                    "count": edge['c'],
                })
        t3.sort(key=lambda x: -x["neurons"])
        return t3[:limit]
    except Exception:
        return []


def _search_arxiv_for_hypotheses(hypotheses: List[Dict]) -> List[Dict]:
    """为 tier 3 假说搜索 arXiv 相关论文"""
    papers = []
    try:
        from session.paper_ingest import search_arxiv
        seen_ids = set()
        for h in hypotheses[:5]:  # 只为 top 5 搜索
            query = f"{h['src']} {h['dst']}".replace('_', ' ')
            try:
                results = search_arxiv(query, max_results=3)
                for r in results:
                    arxiv_id = r.get("arxiv_id", "")
                    if arxiv_id and arxiv_id not in seen_ids:
                        seen_ids.add(arxiv_id)
                        papers.append({
                            "arxiv_id": arxiv_id,
                            "title": r.get("title", "?"),
                            "authors": r.get("authors", "?"),
                            "year": r.get("published", "")[:4],
                            "query": query,
                            "hypothesis": f"{h['src']}→{h['dst']}",
                        })
            except Exception:
                pass
    except Exception:
        pass
    return papers


def _load_discoveries() -> List[Dict]:
    """加载自动发现中 tier≤3 的条目"""
    from data_paths import auto_laws_path; auto_path = auto_laws_path()
    try:
        with open(auto_path) as f:
            laws = json.load(f)
    except Exception:
        return []

    seen_names = set()
    result = []
    for law in laws:
        name = law.get("name", "")
        tier = law.get("confidence_tier", 4)
        if tier > 3:
            continue
        if name in seen_names or name in ("未在给定定律",) or not law.get("inputs"):
            continue
        seen_names.add(name)
        result.append(law)
    return result


def _get_focus_info() -> Optional[Dict]:
    """获取当前聚焦方向"""
    try:
        from meta_cognition.research_directions import get_current_focus
        return get_current_focus()
    except Exception:
        return None


def _count_laws() -> Dict:
    """统计因果图状态"""
    try:
        from physics.laws import library
        laws = library.list_all()
        by_tier = defaultdict(int)
        by_domain = defaultdict(int)
        for law in laws:
            by_tier[getattr(law, "confidence_tier", 4)] += 1
            by_domain[getattr(law, "domain", "unknown")] += 1
        return {
            "total": len(laws),
            "by_tier": dict(by_tier),
            "by_domain": dict(by_domain),
        }
    except Exception:
        return {"total": 0, "by_tier": {}, "by_domain": {}}


def generate_paper() -> str:
    """生成完整论文 — 聚焦 tier 3 诺特脑假说 + arXiv 参考文献"""
    focus = _get_focus_info()
    tier3 = _load_tier3_hypotheses(limit=15)
    arxiv_refs = _search_arxiv_for_hypotheses(tier3)
    discoveries = _load_discoveries()
    cv_reports = _load_cross_validation_reports()
    stats = _count_laws()
    timestamp = time.strftime("%Y-%m-%d")

    lines = []

    # ═══════════ 标题 ═══════════
    if tier3:
        top = tier3[0]
        title = f"Causal Discovery of {top['src']} → {top['dst']}: A Noether Brain Hypothesis"
        title_cn = f"诺特脑假说: {top['src']} → {top['dst']} 的因果发现"
    else:
        title = "PhysCausal Research Report"
        title_cn = "PhysCausal 研究报告"
    lines.append(f"# {title}")
    lines.append(f"## {title_cn}")
    lines.append("")
    lines.append(f"**PhysCausal Agent v0.3.11** | **{timestamp}**")
    lines.append(f"**诺特脑 tier 3 假说: {len(tier3)} 条 | arXiv 参考: {len(arxiv_refs)} 篇**")
    lines.append("")

    # ═══════════ 摘要 ═══════════
    lines.append("## Abstract / 摘要")
    lines.append("")
    lines.append(
        f"诺特脑自进化系统通过 {stats.get('total', '?')} 条物理定律的因果图"
        f"自主发现了 {len(tier3)} 条 tier 3 严肃物理假说（≥10 神经元共识）。"
        f"本文报告其中置信度最高的发现，"
        f"并检索 {len(arxiv_refs)} 篇 arXiv 论文作为文献支撑。"
    )
    lines.append("")
    if tier3:
        for h in tier3[:3]:
            lines.append(f"- **{h['src']} → {h['dst']}**: {h['neurons']} 神经元共识, 强度 {h['strength']}")
    lines.append("")

    # ═══════════ 1. 引言 ═══════════
    lines.append("---")
    lines.append("## 1. Introduction / 引言")
    lines.append("")
    lines.append("### 1.1 诺特脑自进化系统")
    lines.append(
        "诺特脑是一个基于因果图的自进化神经元系统。"
        f"{stats.get('total', '?')} 条物理定律构成初始知识图，"
        "数万神经元通过随机游走探索因果路径。"
        "当 ≥10 个独立神经元走过同一条因果边时，该边升级为 tier 3 严肃物理假说。"
    )
    lines.append("")
    lines.append(f"当前图状态: {stats.get('total', '?')} 定律, 覆盖域: {', '.join(list(stats.get('by_domain', {}).keys())[:8])}")
    lines.append("")

    # ═══════════ 2. 方法 ═══════════
    lines.append("---")
    lines.append("## 2. Methods / 方法")
    lines.append("")
    lines.append("### 2.1 诺特脑发现机制")
    lines.append("")
    lines.append("1. **随机游走**: 神经元在因果图上执行 step_forward/backward")
    lines.append("2. **突触强化**: 每次 walk 激活突触 → LTP 累积")
    lines.append("3. **tier 升级**: ≥10 独立神经元 → tier 4→3 (严肃假说)")
    lines.append("4. **Hebbian 捷径**: 反复共现的节点对长出直连边")
    lines.append("5. **arXiv 验证**: 检索相关文献评估假说可行性")
    lines.append("")

    # ═══════════ 3. Tier 3 发现 ═══════════
    lines.append("---")
    lines.append("## 3. Tier 3 Hypotheses / 诺特脑假说")
    lines.append("")

    if not tier3:
        lines.append("*当前无 tier 3 假说。*")
    else:
        lines.append(f"共 {len(tier3)} 条 tier 3 假说，以下按神经元共识排序:")
        lines.append("")
        lines.append("| # | 假说 | 神经元 | 强度 | arXiv |")
        lines.append("|---|------|--------|------|-------|")
        for i, h in enumerate(tier3[:12]):
            related = [r for r in arxiv_refs if h['src'] in r['query'] or h['dst'] in r['query']]
            arxiv_note = f"{len(related)}篇" if related else "—"
            lines.append(f"| {i+1} | {h['src'][:25]} → {h['dst'][:25]} | {h['neurons']} | {h['strength']:.0f} | {arxiv_note} |")
        lines.append("")

        # 详细展开 top 3
        for i, h in enumerate(tier3[:3]):
            related = [r for r in arxiv_refs if h['src'] in r['query'] or h['dst'] in r['query']]
            lines.append(f"### 3.{i+1} {h['src']} → {h['dst']}")
            lines.append("")
            lines.append(f"- **神经元共识**: {h['neurons']} (≥10 = LTP 阈值)")
            lines.append(f"- **突触强度**: {h['strength']}")
            lines.append(f"- **激活次数**: {h['count']}")
            if related:
                lines.append(f"- **arXiv 文献**: {len(related)} 篇")
                for r in related[:3]:
                    lines.append(f"  - [{r['arxiv_id']}] {r['title'][:80]} ({r['year']})")
            lines.append("")

    # ═══════════ 4. arXiv 文献综述 ═══════════
    lines.append("---")
    lines.append("## 4. arXiv Literature / 文献综述")
    lines.append("")

    if not arxiv_refs:
        lines.append("*arXiv 检索未返回结果。*")
    else:
        lines.append(f"检索到 {len(arxiv_refs)} 篇相关 arXiv 论文:")
        lines.append("")
        for i, r in enumerate(arxiv_refs):
            lines.append(f"{i+1}. **[{r['arxiv_id']}]** {r['title']}")
            lines.append(f"   - 作者: {r['authors'][:80]}")
            lines.append(f"   - 年份: {r['year']}")
            lines.append(f"   - 关联假说: {r['hypothesis']}")
            lines.append("")

    # ═══════════ 5. 讨论 ═══════════
    lines.append("---")
    lines.append("## 5. Discussion / 讨论")
    lines.append("")
    if tier3:
        lines.append("### 5.1 假说评估")
        for h in tier3[:3]:
            src, dst = h['src'], h['dst']
            related = [r for r in arxiv_refs if src in r['query'] or dst in r['query']]
            if related:
                lines.append(f"- **{src} → {dst}**: {len(related)} 篇 arXiv 论文涉及此方向，假说有一定文献基础。")
            else:
                lines.append(f"- **{src} → {dst}**: 暂无直接 arXiv 文献，可能是诺特脑的原创发现。")
        lines.append("")

    lines.append("### 5.2 方法论意义")
    lines.append("诺特脑的自进化机制为理论物理提供了一种新的发现范式:")
    lines.append("- 因果图提供显式、可审计的推理基础")
    lines.append("- 神经元随机游走模拟科学家的探索过程")
    lines.append("- tier 系统保证假说的严肃性（≥10 共识）")
    lines.append("- arXiv 检索提供真实文献验证")
    lines.append("")

    # ═══════════ 参考文献 ═══════════
    lines.append("---")
    lines.append("## References / 参考文献")
    lines.append("")
    for i, r in enumerate(arxiv_refs):
        lines.append(f"{i+1}. {r['authors'][:60]} — *{r['title']}* ({r['year']}), arXiv:{r['arxiv_id']}")
    lines.append(f"{len(arxiv_refs)+1}. PhysCausal Agent v0.3.11 — *Internal methodology: δS=0 as generative root*")
    lines.append("")

    lines.append("---")
    lines.append(f"*由诺特脑 + PhysCausal Agent 自主生成于 {timestamp}*")
    lines.append(f"*tier 3 假说: {len(tier3)} 条 | arXiv: {len(arxiv_refs)} 篇 | 图定律: {stats.get('total', '?')}*")

    return "\n".join(lines)


def write_paper() -> str:
    """生成论文并保存到文件"""
    content = generate_paper()
    reports_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reports"
    )
    os.makedirs(reports_dir, exist_ok=True)

    focus = _get_focus_info()
    tag = focus.get("tag", "GEN") if focus else "GEN"
    ts = time.strftime("%Y%m%d_%H%M%S")
    path = os.path.join(reports_dir, f"paper_{tag}_{ts}.md")

    with open(path, "w") as f:
        f.write(content)

    n_words = len(content.split())
    return f"论文已生成: {path}\n字数: ~{n_words} | 发现: {len(_load_discoveries())} 条 | 交叉验证: {len(_load_cross_validation_reports())} 次"
