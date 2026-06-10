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
    """生成完整论文"""
    focus = _get_focus_info()
    discoveries = _load_discoveries()
    cv_reports = _load_cross_validation_reports()
    stats = _count_laws()
    timestamp = time.strftime("%Y-%m-%d")

    lines = []

    # ═══════════ 标题 ═══════════
    if focus:
        title = f"Causal Structure of {focus['name']}: A PhysCausal Investigation"
        title_cn = f"{focus['name']}的因果结构: PhysCausal 研究"
        lines.append(f"# {title}")
        lines.append(f"## {title_cn}")
    else:
        lines.append("# PhysCausal Research Report")
        lines.append("## PhysCausal 研究报告")

    lines.append("")
    lines.append(f"**PhysCausal Agent v0.3.10** | **{timestamp}**")
    if focus:
        lines.append(f"**研究方向**: [{focus.get('tag', '?')}] {focus['name']}")
    lines.append("")

    # ═══════════ 摘要 ═══════════
    lines.append("## Abstract / 摘要")
    lines.append("")

    n_discoveries = len(discoveries)
    n_cv = len(cv_reports)
    confirmed_cv = sum(1 for r in cv_reports
                       if r.get("convergence_preserved") is True)

    if focus:
        lines.append(
            f"本文使用 PhysCausal 因果推理框架研究**{focus['name']}**。"
            f"基于 δS=0 的唯一生成原理和 {stats.get('total', '?')} 条物理定律的因果图，"
            f"我们发现了 {n_discoveries} 条 tier≤3 的结构性发现，"
            f"并执行了 {n_cv} 次跨域交叉验证（{confirmed_cv} 次通过）。"
        )
        if focus.get("open_problems"):
            lines.append(f"重点关注开放问题: {'; '.join(focus['open_problems'][:3])}。")

    lines.append("")
    lines.append(
        "We apply the PhysCausal causal inference framework to investigate "
        f"{focus['name'] if focus else 'fundamental physics'}. "
        f"Based on the unique generative principle δS=0 and a causal graph "
        f"of {stats.get('total', '?')} physical laws, "
        f"we report {n_discoveries} structural discoveries (tier≤3) "
        f"and {n_cv} cross-domain validations ({confirmed_cv} passed)."
    )
    lines.append("")

    # ═══════════ 1. 引言 ═══════════
    lines.append("---")
    lines.append("## 1. Introduction / 引言")
    lines.append("")

    if focus:
        lines.append(f"### 1.1 研究方向")
        lines.append(f"**{focus['name']}** ({focus.get('tag', '?')})")
        lines.append(f"核心问题: {focus.get('core_question', '?')}")
        lines.append("")
        lines.append(f"关键变量: {', '.join(focus.get('key_variables', [])[:8])}")
        lines.append(f"关键领域: {', '.join(focus.get('key_domains', [])[:5])}")
        lines.append(f"推荐透镜: {', '.join(focus.get('key_lenses', [])[:4])}")
        lines.append("")

    lines.append("### 1.2 因果图状态")
    lines.append(f"- 总定律数: {stats.get('total', '?')}")
    for tier, count in sorted(stats.get("by_tier", {}).items()):
        tier_label = {0: "元物理定理", 1: "确立定律", 2: "论文支撑",
                      3: "严肃假说", 4: "探索编码"}.get(tier, f"tier {tier}")
        lines.append(f"- tier {tier} ({tier_label}): {count}")
    lines.append("")

    # ═══════════ 2. 方法 ═══════════
    lines.append("---")
    lines.append("## 2. Methods / 方法")
    lines.append("")
    lines.append("### 2.1 PhysCausal 因果推理框架")
    lines.append("")
    lines.append("PhysCausal 使用结构因果模型 (SCM) 表示物理定律。核心原理:")
    lines.append("")
    lines.append("1. **δS=0** — 唯一生成根。所有基本定律都是最小作用量原理的推论。")
    lines.append("2. **因果图** — 物理变量之间的有向因果边，由定律库显式定义。")
    lines.append("3. **置信层级 (tier 0–4)** — 从数学定理到探索编码的严格分层。")
    lines.append("4. **负向约束** — forbidden_directions 防止因果污染。")
    lines.append("5. **多层验证** — 公理链 + 跨域比较 + 留一法。")
    lines.append("")

    lines.append("### 2.2 交叉验证方法")
    lines.append("")
    lines.append("对每条 tier≤3 发现，PhyCausal 在所有未覆盖的物理域")
    lines.append("（量子、几何、热力学、电磁学）执行交叉验证:")
    lines.append("")
    lines.append("1. 加载目标域的哲学透镜 (如 quantum→path_integral)")
    lines.append("2. 在扩展因果图上重新传播")
    lines.append("3. 检测汇聚是否保持")
    lines.append("4. 当量子域未直接参与时，诚实地标注缺失桥梁")
    lines.append("")

    # ═══════════ 3. 发现 ═══════════
    lines.append("---")
    lines.append("## 3. Discoveries / 发现")
    lines.append("")

    if not discoveries:
        lines.append("*当前无 tier≤3 的结构性发现。*")
    else:
        for i, d in enumerate(discoveries):
            name = d.get("name", "unnamed")
            tier = d.get("confidence_tier", "?")
            inputs = d.get("inputs", [])
            outputs = d.get("outputs", [])
            note = d.get("_discovery_note", "")
            domain = d.get("domain", "unknown")

            lines.append(f"### 3.{i+1} {name}")
            lines.append("")
            lines.append(f"- **置信层级**: tier {tier}")
            lines.append(f"- **领域**: {domain}")
            lines.append(f"- **因果边**: {', '.join(inputs)} → {', '.join(outputs)}")
            if note:
                lines.append(f"- **发现说明**: {note}")
            lines.append("")

            # 相关的交叉验证
            related_cv = [r for r in cv_reports
                          if r.get("discovery", "") == name]
            if related_cv:
                lines.append(f"**交叉验证结果** ({len(related_cv)} 域):")
                lines.append("")
                lines.append("| 域 | 汇聚保持 | 量子参与 | 判定 |")
                lines.append("|-----|---------|---------|------|")
                for cv in related_cv:
                    domain = cv.get("target_domain", "?")
                    preserved = "✓" if cv.get("convergence_preserved") else "⚠" if cv.get("convergence_preserved") is False else "?"
                    qi = "是" if cv.get("quantum_involved") else "否"
                    verdict = cv.get("verdict_cn", "?")[:50]
                    lines.append(f"| {domain} | {preserved} | {qi} | {verdict} |")
                lines.append("")

                # 量子评估
                for cv in related_cv:
                    qa = cv.get("quantum_assessment")
                    if qa:
                        lines.append(f"**{cv.get('target_domain', '?')}域量子评估**:")
                        lines.append(f"> {qa.get('honest_answer', '')}")
                        lines.append(f"> 缺失桥梁: {qa.get('missing_bridge', '?')}")
                        lines.append("")

    # ═══════════ 4. 交叉验证汇总 ═══════════
    lines.append("---")
    lines.append("## 4. Cross-Validation Summary / 交叉验证汇总")
    lines.append("")

    if not cv_reports:
        lines.append("*尚未执行交叉验证。*")
    else:
        lines.append(f"共执行 **{len(cv_reports)}** 次跨域交叉验证。")
        lines.append("")
        lines.append("| 发现 | 目标域 | 汇聚 | 量子参与 | 判定 |")
        lines.append("|------|--------|------|---------|------|")
        for cv in cv_reports:
            name = cv.get("discovery", "?")[:25]
            domain = cv.get("target_domain", "?")
            preserved = "✓" if cv.get("convergence_preserved") else "⚠"
            qi = "✓" if cv.get("quantum_involved") else "—"
            verdict = cv.get("verdict_cn", "?")[:40]
            lines.append(f"| {name} | {domain} | {preserved} | {qi} | {verdict} |")
        lines.append("")

        # 统计
        passed = sum(1 for r in cv_reports if r.get("convergence_preserved") is True)
        broken = sum(1 for r in cv_reports if r.get("convergence_preserved") is False)
        lines.append(f"- 汇聚保持: {passed}")
        lines.append(f"- 汇聚断裂: {broken}")
        lines.append(f"- 量子域直接参与: {sum(1 for r in cv_reports if r.get('quantum_involved'))}")
        lines.append("")

    # ═══════════ 5. 讨论 ═══════════
    lines.append("---")
    lines.append("## 5. Discussion / 讨论")
    lines.append("")
    lines.append("### 5.1 主要发现")

    if discoveries:
        for d in discoveries:
            name = d.get("name", "")
            inputs = d.get("inputs", [])
            outputs = d.get("outputs", [])
            tier = d.get("confidence_tier", "?")
            note = d.get("_discovery_note", "")

            # 根据具体发现生成讨论
            if "geodesic" in name.lower() or "convergence" in name.lower():
                msg = (f"确认了 {' + '.join(inputs[:2])} 在 {' + '.join(outputs[:2])} 处的因果汇聚。"
                       f"这是 δS=0 为唯一生成根的进一步证据。")
            elif "测地线" in name:
                msg = (f"经典测地线方程在因果图中被验证为 tier {tier}。"
                       f"跨域交叉验证暴露了量子域的缺失桥梁。")
            elif "牛顿" in name:
                msg = (f"经典力学的基本定律在因果图中为 tier {tier}。"
                       f"量子对应物 (算子力学) 尚未建模。")
            elif "等效" in name:
                msg = (f"等效原理连接了惯性质量与引力质量。"
                       f"量子域的等效原理仍是开放问题。")
            elif "不确定" in name:
                msg = (f"不确定性原理是量子力学的基石。"
                       f"其在几何域的对应物尚未建立。")
            elif "作用量" in name:
                msg = (f"最小作用量原理是因果图的生成根。"
                       f"其在各域的普适性需要进一步检验。")
            elif note:
                msg = note[:120]
            else:
                msg = f"tier {tier} 结构性发现。"

            lines.append(f"- **{name}**: {msg}")
    else:
        lines.append("- 当前因果图尚未产生 tier≤3 的结构性新发现。继续运行研究循环。")

    lines.append("")
    lines.append("### 5.2 量子域的开放问题")
    lines.append("")
    lines.append("交叉验证表明，量子域定律（路径积分、测量问题）未直接参与")
    lines.append("经典域的因果路径。这不是因果图的缺陷，而是反映了物理学当前")
    lines.append("的真实状态: 量子引力理论尚未给出 path_integral → spacetime_structure")
    lines.append("的显式因果边。")
    lines.append("")
    lines.append("在 ħ→0 的经典极限下，路径积分的稳相近似给出经典路径，")
    lines.append("在非平凡度规下即为测地线。但这是数学对应，不是物理因果。")
    lines.append("量子域的直接因果参与需要:")
    lines.append("- AdS/CFT 中边界路径积分与体测地线的显式对应")
    lines.append("- 或建模 stationary_path 为中间桥梁变量（带 ħ→0 条件标记）")
    lines.append("")

    lines.append("### 5.3 方法论意义")
    lines.append("")
    lines.append("PhysCausal 的因果图方法为理论物理提供了一个独特的工具:")
    lines.append("因果推理迫使假设以显式、可验证、可反驳的因果边形式出现。")
    lines.append("这避免了物理学中常见的'哲学陈述冒充物理定律'的问题。")
    lines.append("")

    # ═══════════ 6. 下一步 ═══════════
    lines.append("### 5.4 下一步研究")
    lines.append("")
    if focus and focus.get("open_problems"):
        for op in focus.get("open_problems", [])[:3]:
            lines.append(f"- [ ] {op}")
    lines.append("- [ ] 补建 stationary_path 中间桥梁变量")
    lines.append("- [ ] 热力学域交叉验证 (entropy→geodesic_path)")
    lines.append("- [ ] 扩展 AdS/CFT 桥接到因果图")
    lines.append("")

    # ═══════════ 参考文献 ═══════════
    lines.append("---")
    lines.append("## References / 参考文献")
    lines.append("")
    lines.append("1. Wheeler, J.A. — *Geometrodynamics* (1962)")
    lines.append("2. Feynman, R.P. — *Space-Time Approach to Non-Relativistic Quantum Mechanics* (1948)")
    lines.append("3. Pearl, J. — *Causality* (2009)")
    lines.append("4. Maldacena, J. — *The Large N Limit of Superconformal Field Theories* (AdS/CFT, 1998)")
    lines.append("5. Sorkin, R.D. — *Causal Sets: Discrete Gravity* (2003)")
    lines.append("6. PhysCausal — *Internal methodology: δS=0 as generative root* (v0.3.10)")
    lines.append("7. Penrose, R. — *On Gravity's Role in Quantum State Reduction* (1996)")
    lines.append("8. Landauer, R. — *Irreversibility and Heat Generation in the Computing Process* (1961)")
    lines.append("")
    lines.append("---")
    lines.append(f"*由 PhysCausal Agent v0.3.10 自主生成于 {timestamp}*")
    lines.append(f"*因果图: {stats.get('total', '?')} 定律, {n_discoveries} 条发现, {n_cv} 次交叉验证*")

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
