"""
what_next — 物理学家元认知: 知道自己下一步该干什么

扫描当前状态 (发现 / 前沿 / 认知失调 / 透镜) →
生成优先级排序的行动建议 →
让 agent 自主决定"先验证量子域的汇聚"还是"先探索稀疏区"

核心原则:
  - 不是替代用户做决策，是提供结构化的"为什么这一步值得做"
  - 每个建议包含: what (行动), why (理由), how (工具/透镜), priority (分数)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import json
import os

from physics.laws import classify_variable

# ── 完成追踪 ──
from data_paths import completed_suggestions_path as _completed_path
_COMPLETED_FILE = _completed_path()


def _load_completed() -> set:
    """加载已完成的建议 (key: type|discovery_name|domain)"""
    try:
        with open(_COMPLETED_FILE) as f:
            return set(tuple(x) for x in json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        return set()


def _save_completed(completed: set):
    with open(_COMPLETED_FILE, "w") as f:
        json.dump([list(x) for x in completed], f)


def mark_completed(suggestion: Dict):
    """标记一条建议为已完成"""
    key = (suggestion.get("type", ""),
           suggestion.get("discovery_name", ""),
           suggestion.get("domain", ""))
    completed = _load_completed()
    completed.add(key)
    _save_completed(completed)


def _make_key(suggestion: Dict) -> tuple:
    return (suggestion.get("type", ""),
            suggestion.get("discovery_name", ""),
            suggestion.get("domain", ""))

# ── 域 → 透镜映射 ──
# 当一个发现尚未在某域验证时，推荐哪些透镜来交叉检验

DOMAIN_LENS_MAP: Dict[str, List[str]] = {
    "quantum": ["path_integral", "measurement_problem"],
    "geometry": ["geometric_identity", "wheeler_frontier"],
    "thermodynamics": ["arrow_of_time"],
    "symmetry": ["group_theory", "classification_by_symmetry"],
    "variational": ["least_action_ontology", "action_root"],
    "unification": ["bootstrap", "stability_structure"],
}

# 变量分类 → 域标签 (用于推断"发现覆盖了哪些域")
CATEGORY_DOMAIN: Dict[str, str] = {
    "fundamental": "classical",
    "geometric": "geometry",
    "quantum": "quantum",
    "derived": "classical",
}

# 全部可能的域
ALL_DOMAINS = {"classical", "geometry", "quantum", "thermodynamics", "electromagnetism"}


def _load_auto_laws() -> List[Dict]:
    from data_paths import auto_laws_path; path = auto_laws_path()
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _get_covered_domains(discovery: Dict) -> set:
    """从发现涉及的变量推断已覆盖的域"""
    domains = set()
    all_vars = discovery.get("inputs", []) + discovery.get("outputs", [])
    for var in all_vars:
        cat = classify_variable(var)
        dom = CATEGORY_DOMAIN.get(cat, "classical")
        domains.add(dom)
    # discovery 的 domain 字段也计入
    disc_domain = discovery.get("domain", "")
    # 量子力学 / 广义相对论 / 热力学 → 直接映射
    domain_keywords = {
        "quantum": "quantum", "量子": "quantum",
        "relativity": "geometry", "相对论": "geometry",
        "thermo": "thermodynamics", "热": "thermodynamics",
        "electro": "electromagnetism", "电磁": "electromagnetism",
        "unification": "unification",
    }
    for kw, dom in domain_keywords.items():
        if kw in disc_domain.lower():
            domains.add(dom)
    return domains


def _get_uncovered_domains(covered: set) -> List[str]:
    """返回尚未覆盖的域，按重要性排序"""
    return sorted(ALL_DOMAINS - covered - {"classical"})


def _is_valid_discovery(discovery: Dict) -> bool:
    """过滤垃圾条目"""
    name = discovery.get("name", "")
    inputs = discovery.get("inputs", [])
    outputs = discovery.get("outputs", [])
    # 跳过无名/空变量/已知垃圾
    if not name or name in ("未在给定定律",):
        return False
    if not inputs or not outputs:
        return False
    return True


def _load_auto_laws_deduped() -> List[Dict]:
    """加载自动发现，按名称去重"""
    laws = _load_auto_laws()
    seen_names = set()
    deduped = []
    for law in laws:
        name = law.get("name", "")
        if name in seen_names:
            continue
        seen_names.add(name)
        deduped.append(law)
    return deduped


def _suggest_cross_validation(discovery: Dict) -> List[Dict]:
    """
    对一条发现，建议在未覆盖的域做交叉验证。

    返回: [{what, why, how, lenses, priority}, ...]
    """
    name = discovery.get("name", "unnamed")
    covered = _get_covered_domains(discovery)
    uncovered = _get_uncovered_domains(covered)

    suggestions = []
    tier = discovery.get("confidence_tier", 4)

    for domain in uncovered:
        lenses = DOMAIN_LENS_MAP.get(domain, [])
        if not lenses:
            continue

        # 优先级: 量子域 > 几何域 > 热力学 > 其他
        domain_priority = {"quantum": 10, "geometry": 7,
                           "thermodynamics": 5}.get(domain, 3)
        # tier 3 的发现比 tier 4 更需要验证，且跨域验证本身价值高
        tier_bonus = 8 if tier == 3 else 2
        # 交叉验证是"已有发现的质量保证"，基线分比纯探索高
        priority = domain_priority + tier_bonus + 2  # +2 基线

        # 构建因果变量清单
        inputs = discovery.get("inputs", [])
        outputs = discovery.get("outputs", [])
        var_summary = " + ".join(inputs[:3]) + " → " + ", ".join(outputs[:3])

        suggestions.append({
            "type": "cross_validate",
            "what": f"交叉验证 {name} 在 {domain} 域",
            "why": (
                f"{var_summary} 已在 {', '.join(sorted(covered))} 域验证，"
                f"但尚未在 {domain} 域检验。{domain} 域的 {lenses[0]} 透镜"
                f"可能揭示对应物或矛盾。"
            ),
            "how": f"加载 {', '.join(lenses)} 透镜 → 扩展因果图 → 检测汇聚是否保持",
            "lenses": lenses,
            "domain": domain,
            "discovery_name": name,
            "priority": priority,
        })

    return suggestions


def _suggest_frontier_exploration() -> List[Dict]:
    """从前沿地图生成探索建议"""
    try:
        from meta_cognition.frontier import FrontierMap
        fm = FrontierMap()
        fm.build()
    except Exception:
        return []

    suggestions = []

    # 稀疏区
    sparse = fm.sparse_zones(min_domains=2)
    for z in sparse[:5]:
        cat = classify_variable(z["variable"])
        # sparse_zones 的 score 已含本体论权重，不重复乘
        # 归一化: 稀疏区分数通常在 3-40 范围，压缩到 3-12
        raw_score = z["score"]
        normalized = min(raw_score / 3.0, 12.0)  # 上限 12
        suggestions.append({
            "type": "frontier",
            "what": f"探索 {z['variable']} 在 {', '.join(z['domains_absent'][:2])} 域的桥接",
            "why": (
                f"{z['variable']} 出现在 {len(z.get('domains_present', []))} 个域但缺席 "
                f"{', '.join(z['domains_absent'][:2])}。"
                f"填补这些空白可能发现新的跨域桥接。"
            ),
            "how": f"innovation_engine.generate_candidates(变量={z['variable']}, 缺席域={z['domains_absent'][:2]})",
            "lenses": ["wheeler_frontier"],
            "domain": z["domains_absent"][0] if z["domains_absent"] else "unknown",
            "priority": round(normalized, 1),
        })

    # 尺度裂缝
    gaps = fm.scale_gaps()
    for g in gaps[:3]:
        suggestions.append({
            "type": "scale_gap",
            "what": f"桥接 {g['scale_a']} ↔ {g['scale_b']}: {g['variable']}",
            "why": (
                f"{g['variable']} 在 {g['scale_a']} 和 {g['scale_b']} 尺度都有出现，"
                f"但中间缺乏桥接。这可能是多尺度物理的突破口。"
            ),
            "how": f"cross_domain_discover(源={g['scale_a']}, 目标={g['scale_b']})",
            "lenses": ["bootstrap"],
            "domain": "unification",
            "priority": round(g["score"] * 2.5, 1),
        })

    return suggestions


def _suggest_dissonance_resolution() -> List[Dict]:
    """从认知失调检测未解决的张力"""
    try:
        from meta_cognition.dissonance import detect_all
        issues = detect_all()
    except Exception:
        return []

    suggestions = []
    for issue in issues[:3]:
        law_a = issue.get("law_a", "?")
        law_b = issue.get("law_b", "?")
        var = issue.get("variable", "?")
        suggestions.append({
            "type": "dissonance",
            "what": f"解决 {law_a} ↔ {law_b} 在 {var} 上的张力",
            "why": (
                f"{law_a} 和 {law_b} 对 {var} 的影响方向可能冲突。"
                f"这种认知失调可能是新物理的信号——更深的原则可能调和两者。"
            ),
            "how": f"chain 双向传播 → 检测汇聚/发散 → 寻找桥接定律",
            "lenses": ["bootstrap", "stability_structure"],
            "domain": issue.get("domain", "unknown"),
            "priority": 8.0,
        })

    return suggestions


def suggest_next(max_suggestions: int = 8) -> Dict:
    """
    扫描当前状态，生成优先级排序的"下一步行动"建议。

    返回:
      {
        "suggestions": [...],     // 排序后的建议列表
        "state_summary": "...",   // 当前状态摘要
        "top": {...},             // 最高优先级建议
      }
    """
    all_suggestions = []

    # 1. 从自动发现中生成交叉验证建议
    auto_laws = _load_auto_laws_deduped()
    tier3_plus = [l for l in auto_laws
                  if l.get("confidence_tier", 4) <= 3
                  and _is_valid_discovery(l)]
    for discovery in tier3_plus:
        all_suggestions.extend(_suggest_cross_validation(discovery))

    # 2. 前沿地图 → 探索建议
    all_suggestions.extend(_suggest_frontier_exploration())

    # 3. 认知失调 → 解决建议
    all_suggestions.extend(_suggest_dissonance_resolution())

    # 排序
    all_suggestions.sort(key=lambda s: s["priority"], reverse=True)

    # 聚焦偏置: 如果设定了方向, 提升相关建议的优先级
    try:
        from meta_cognition.research_directions import bias_by_focus
        fb = bias_by_focus()
        if fb.get("active"):
            focus_vars = set(fb.get("key_variables", []))
            for s in all_suggestions:
                # 检查建议是否涉及聚焦变量
                what_lower = s.get("what", "").lower()
                domain = s.get("domain", "")
                # 交叉验证: 检查发现名称中的变量
                disc_name = s.get("discovery_name", "").lower()
                if any(v in disc_name for v in focus_vars):
                    s["priority"] += 3.0
                # 前沿探索: 检查涉及域是否匹配
                if domain in fb.get("key_domains", []):
                    s["priority"] += 2.0
            all_suggestions.sort(key=lambda s: s["priority"], reverse=True)
    except Exception:
        pass

    # 过滤已完成的
    completed = _load_completed()
    pending = [s for s in all_suggestions if _make_key(s) not in completed]
    n_completed = len(all_suggestions) - len(pending)

    # 限制数量
    suggestions = pending[:max_suggestions]

    # 状态摘要
    covered_domains = set()
    for d in tier3_plus:
        covered_domains |= _get_covered_domains(d)
    state_summary = (
        f"待验证发现: {len(tier3_plus)} 条 | "
        f"已覆盖域: {', '.join(sorted(covered_domains)) if covered_domains else '无'} | "
        f"未完成: {len(pending)} | 已完成: {n_completed}"
    )

    return {
        "suggestions": suggestions,
        "state_summary": state_summary,
        "top": suggestions[0] if suggestions else None,
        "total_pending": len(tier3_plus),
    }


def suggest_report() -> str:
    """生成可读的建议报告"""
    result = suggest_next()

    lines = [
        "══════ PhysCausal 下一步建议 ══════",
        f"  {result['state_summary']}",
        "",
    ]

    if not result["suggestions"]:
        lines.append("  当前无待处理项。运行 research 或 autonomous 生成新发现。")
        return "\n".join(lines)

    type_cn = {
        "cross_validate": "交叉验证",
        "frontier": "前沿探索",
        "scale_gap": "尺度桥接",
        "dissonance": "失调解析",
    }

    for i, s in enumerate(result["suggestions"]):
        tag = type_cn.get(s["type"], s["type"])
        stars = "★★★" if s["priority"] >= 8 else "★★" if s["priority"] >= 5 else "★"
        lines.append(f"  {i+1}. {stars} [{tag}] {s['what']}")
        lines.append(f"     为何: {s['why'][:100]}")
        lines.append(f"     透镜: {', '.join(s['lenses'][:3])}")
        lines.append("")

    if result["top"]:
        top = result["top"]
        lines.append(f"  ══ 最高优先级 ══")
        lines.append(f"  行动: {top['what']}")
        lines.append(f"  方法: {top['how'][:120]}")

    return "\n".join(lines)
