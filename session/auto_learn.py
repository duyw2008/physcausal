"""
自主学习 — 从 LLM 回答中发现知识缺口并自动补全

当 agent 检测到回答中暗示了定律库不完整
(如 "定律库中没有直接描述" / "缺少相关定律"),
自动触发学习循环:
  1. 问 LLM: "这个问题涉及哪些物理定律？"
  2. 提取定律名称和数学形式
  3. 物理验证 (与已有定律的 forbidden_directions 不冲突)
  4. 自动入库
"""

from __future__ import annotations
import re
from typing import Dict, List, Optional


# 知识缺口检测模式 — 只在回答明确说"需要补充"时才触发，避免误报
GAP_PATTERNS = [
    r'需要.*?(?:引入|补充|增加).*?(?:定律|原理|方程)',
    r'定律库中[没未无].*?(?:描述|覆盖|涉及)(?!.*?已包含)',
    r'(?:缺少|缺失)以下.*?(?:定律|原理)',
]


def detect_gaps(answer: str) -> bool:
    """检测回答中是否暗示了知识缺口"""
    for pattern in GAP_PATTERNS:
        if re.search(pattern, answer):
            return True
    return False


def extract_law_names(text: str) -> List[str]:
    """从文本中提取被提及的定律名称"""
    # 匹配 "XXX 定律" 或 "XXX 的定律" 或 "XXX (domain)"
    known = set()
    # Pattern 1: "XXX定律"
    for m in re.finditer(r'([\u4e00-\u9fff\w]+)定律', text):
        known.add(m.group(1) + "定律")
    # Pattern 2: "XXX 的定律"
    for m in re.finditer(r'([\u4e00-\u9fff\w]+)的定律', text):
        known.add(m.group(1))
    # Pattern 3: "开普勒第X定律"
    for m in re.finditer(r'(开普勒第[一二三四五六七八九十]+定律)', text):
        known.add(m.group(1))
    # Pattern 4: English names like "Kepler's Laws"
    for m in re.finditer(r"([A-Z][a-z]+(?:'s)?\s*(?:Law|laws?|Principle|principle))", text):
        known.add(m.group(1))
    return list(known)


def ask_llm_for_laws(client, question: str, gap_answer: str) -> Optional[List[Dict]]:
    """
    问 LLM: "这个问题涉及哪些物理定律？请列出名称和数学形式。"

    Returns:
        [{name, latex, inputs, outputs, causal_direction, domain}, ...]
    """
    if not client:
        return None

    prompt = (
        "你是一个物理学家。以下问题需要一个完整的物理解释，但当前定律库不完整。\n\n"
        f"用户问题: {question}\n\n"
        "请列出解释这个问题所需的关键物理定律，以 JSON 格式返回:\n"
        "[\n"
        '  {"name": "定律名", "latex": "数学公式", '
        '"inputs": ["输入变量"], "outputs": ["输出变量"], '
        '"domain": "领域 (mechanics/electromagnetism/thermodynamics/quantum/...)", '
        '"causal_direction": [["原因", "结果"]]}\n'
        "]\n\n"
        "只返回 JSON，不要其他文字。最多 5 条定律。"
    )

    try:
        response = client.chat([{"role": "user", "content": prompt}])
        # Extract JSON from response
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group())
    except Exception:
        pass

    return None


def auto_learn(agent, question: str, answer: str) -> Dict:
    """
    自主学习主循环: 检测缺口 → 提取建议定律 → 验证 → 入库

    Returns:
        {learned: [law_names], attempted: int, success: bool}
    """
    if not detect_gaps(answer):
        return {"learned": [], "attempted": 0, "success": False}

    from physics.laws import library, PhysicsLaw, ConstraintType
    import numpy as np

    # 尝试从 LLM 获取候选定律
    bridge = agent.llm
    if not bridge.is_available():
        return {"learned": [], "attempted": 0, "success": False}

    candidates = ask_llm_for_laws(bridge.client, question, answer)
    if not candidates:
        return {"learned": [], "attempted": 0, "success": False}

    learned = []
    for c in candidates:
        name = c.get("name", "")
        latex = c.get("latex", "")
        domain = c.get("domain", "unknown")
        inputs = c.get("inputs", [])
        outputs = c.get("outputs", [])
        causal_dir = c.get("causal_direction", [])

        if not name or not inputs:
            continue

        # 检查是否已存在 — 增强去重: 需同时满足名称相似 + 变量重叠
        cn_lower = name.lower()
        existing_vars = set(v.lower() for v in inputs + outputs)
        duplicate = False
        for law in library.list_all():
            en_lower = law.name.lower()
            law_vars = set(v.lower() for v in law.inputs + law.outputs)
            # 1. 精确或包含匹配
            name_match = (
                cn_lower == en_lower or
                (len(cn_lower) > 3 and len(en_lower) > 3 and
                 (cn_lower in en_lower or en_lower in cn_lower))
            )
            # 2. 变量重叠 > 50%
            var_overlap = len(existing_vars & law_vars) / max(len(existing_vars | law_vars), 1)
            # 需要名称匹配 + 变量重叠同时满足
            if name_match and var_overlap > 0.3:
                duplicate = True; break
            # 3. 通用概念黑名单: 太泛的"定律"不应自动学习
            for generic in ["物理定律", "该定律", "m定律", "一个几何原理", "一个分析力学原理"]:
                if generic in name:
                    duplicate = True; break
            if duplicate:
                break
        if duplicate:
            continue

        # 物理验证: 候选定律的 causal_direction 不能违反已有定律的 forbidden_directions
        conflict = False
        for src, dst in causal_dir:
            for law in library.list_all():
                for fd_src, fd_dst in law.forbidden_directions:
                    if (fd_src.lower() in src.lower() and fd_dst.lower() in dst.lower()):
                        conflict = True
                        break
                if conflict:
                    break
            if conflict:
                break

        if conflict:
            continue

        # 入库
        try:
            law = PhysicsLaw(
                name=name,
                domain=domain,
                latex=latex,
                inputs=inputs,
                outputs=outputs,
                constraint_type=ConstraintType.SCM_EQUATION,
                formula=lambda *args: 0.0,
                causal_direction=[tuple(d) for d in causal_dir],
                forbidden_directions=[],
            )
            law._auto_learned = True  # 标记为自学习
            library.register(law)
            learned.append(name)
        except Exception:
            pass

    # 持久化
    if learned:
        _save_auto_laws()

    return {
        "learned": learned,
        "attempted": len(candidates),
        "success": len(learned) > 0,
    }


def _save_auto_laws():
    """保存自学习定律到持久文件"""
    import json, os
    from physics.laws import library
    auto_laws = []
    for law in library.list_all():
        if hasattr(law, '_auto_learned') and law._auto_learned:
            entry = {
                "name": law.name,
                "domain": law.domain,
                "latex": law.latex if hasattr(law, 'latex') else "",
                "inputs": law.inputs,
                "outputs": law.outputs,
                "causal_direction": list(law.causal_direction),
                "confidence_tier": getattr(law, 'confidence_tier', 4),
            }
            if hasattr(law, '_chain_discovered') and law._chain_discovered:
                entry["_chain_discovered"] = True
            if hasattr(law, '_discovery_note') and law._discovery_note:
                entry["_discovery_note"] = law._discovery_note
            auto_laws.append(entry)
    if auto_laws:
        from data_paths import auto_laws_path; path = auto_laws_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(auto_laws, f, ensure_ascii=False, indent=2)


def detect_external_mentions(answer: str) -> List[str]:
    """检测 LLM 回答中提到的外部定律 (不在 PhysCausal 库中)"""
    from physics.laws import library
    external = set()
    for m in re.finditer(r'([A-Za-z\u4e00-\u9fff]{2,}(?:定律|定理|原理|方程|法则|效应))', answer):
        name = m.group(1)
        in_library = any(law.name in name or name in law.name for law in library.list_all())
        if not in_library and len(name) > 2:
            external.add(name)
    return sorted(external)


def learn_from_chain(chain: List[Dict]) -> Dict:
    """
    从反事实链传播结果中学习新的因果结构。

    检测两种模式:
      1. 汇聚路径: 多个不同变量通过同一规律指向同一目标
      2. 跨域传递: 链步跨越领域边界但无显式桥接定律

    置信层级保护:
      - 如果链中任何一步使用了 tier >= 3 的定律, 不自动入库
      - tier 4 的发现只报告, 不注册

    不需要 LLM — 纯图结构分析。
    """
    from physics.laws import library, PhysicsLaw, ConstraintType

    if not chain or "error" in chain[0]:
        return {"learned": [], "attempted": 0, "success": False}

    # ── 置信层级检查 ──
    max_chain_tier = max(
        (s.get("confidence_tier", 1) for s in chain if "confidence_tier" in s),
        default=1
    )
    blocked_by_tier = max_chain_tier >= 3

    candidates = []

    # ── 模式 1: 汇聚路径检测 ──
    # 按 (law, effect_variable) 分组
    by_target: Dict[Tuple[str, str], List[Dict]] = {}
    for step in chain:
        key = (step.get("law", ""), step.get("effect_variable", ""))
        if key[0] and key[1]:
            by_target.setdefault(key, []).append(step)

    for (law_name, target_var), steps in by_target.items():
        source_vars = [s["variable"] for s in steps if s.get("variable")]
        if len(set(source_vars)) >= 2:
            # 多条路径汇聚 — 这是结构发现
            domains = list(set(s.get("domain", "unknown") for s in steps))
            unique_sources = list(dict.fromkeys(source_vars))  # 去重保序
            candidate_name = f"Convergence_{target_var}"
            candidates.append({
                "name": candidate_name,
                "domain": "unification",
                "latex": "",
                "inputs": unique_sources,
                "outputs": [target_var],
                "causal_direction": [[src, target_var] for src in unique_sources],
                "source_type": "chain_convergence",
                "description": (
                    f"Chain propagation reveals {len(unique_sources)} independent "
                    f"paths ({chr(44).join(unique_sources)}) converging on {target_var} "
                    f"via {law_name}. This suggests an invariance or conservation law "
                    f"unifying domains: {chr(44).join(domains)}."
                ),
            })

    # ── 模式 2: 跨域传递检测 ──
    # 重建因果父子关系: effect_variable of parent == variable of child
    # 通过 chain_path 判断: 如果 step_b.path 以 step_a.path 为前缀, 则 a→b 是因果边
    indexed_steps = []
    for step in chain:
        domain = step.get("domain", "unknown")
        var = step.get("variable", "")
        effect = step.get("effect_variable", "")
        cpath = step.get("chain_path", [])
        if domain not in ("unknown", "auto", "unification") and var and effect:
            indexed_steps.append((domain, var, effect, cpath, step.get("depth", 0)))

    for i, (dom_a, var_a, eff_a, path_a, depth_a) in enumerate(indexed_steps):
        for j, (dom_b, var_b, eff_b, path_b, depth_b) in enumerate(indexed_steps):
            if i == j:
                continue
            # 只有当 B 的 variable 等于 A 的 effect_variable (真正的因果边)
            if var_b != eff_a:
                continue
            # 且 path_a 是 path_b 的前缀 (确实是父子关系, 不是巧合同名)
            if len(path_a) >= len(path_b):
                continue
            if path_b[:len(path_a)] != path_a:
                continue
            if dom_a == dom_b:
                continue

            # 找到了真正的跨域因果边
            bridge_exists = False
            for law in library.list_all():
                law_vars = set(law.inputs + law.outputs)
                if eff_a in law_vars and var_b in law_vars:
                    bridge_exists = True
                    break
            if not bridge_exists:
                candidate_name = f"Bridge_{dom_a}_{dom_b}"
                candidates.append({
                    "name": candidate_name,
                    "domain": "unification",
                    "latex": "",
                    "inputs": [eff_a],
                    "outputs": [var_b],
                    "causal_direction": [[eff_a, var_b]],
                    "source_type": "cross_domain_bridge",
                    "description": (
                        f"Chain step: {eff_a} ({dom_a}) → {var_b} ({dom_b}) "
                        f"crosses domain boundary without an explicit bridging law."
                    ),
                })

    # ── 去重 + 验证 + 入库 ──
    learned = []
    for c in candidates:
        name = c["name"]
        inputs = c.get("inputs", [])
        outputs = c.get("outputs", [])
        causal_dir = c.get("causal_direction", [])

        # 去重
        existing_vars = set(v.lower() for v in inputs + outputs)
        duplicate = False
        for law in library.list_all():
            law_vars = set(v.lower() for v in law.inputs + law.outputs)
            var_overlap = len(existing_vars & law_vars) / max(len(existing_vars | law_vars), 1)
            if var_overlap > 0.8:
                duplicate = True
                break
        if duplicate:
            continue

        # 物理验证: forbidden检查
        conflict = False
        for src, dst in causal_dir:
            for law in library.list_all():
                for fd_src, fd_dst in law.forbidden_directions:
                    if fd_src.lower() in src.lower() and fd_dst.lower() in dst.lower():
                        conflict = True
                        break
                if conflict:
                    break
            if conflict:
                break
        if conflict:
            continue

        # ── 置信层级保护: tier >= 3 的链不自动入库 ──
        if blocked_by_tier:
            learned.append(f"[blocked:tier{max_chain_tier}]{name}")
            continue

        # 生成描述性名称 (防重名)
        final_name = name
        existing_names = {law.name for law in library.list_all()}
        suffix = 2
        while final_name in existing_names:
            final_name = f"{name}_{suffix}"
            suffix += 1

        try:
            law = PhysicsLaw(
                name=final_name,
                domain=c.get("domain", "unification"),
                latex=c.get("latex", ""),
                inputs=inputs,
                outputs=outputs,
                constraint_type=ConstraintType.SCM_EQUATION,
                formula=lambda *args: 0.0,
                causal_direction=[tuple(d) for d in causal_dir],
                forbidden_directions=[],
            )
            law._auto_learned = True
            law._chain_discovered = True
            law._discovery_note = c.get("description", "")
            law.confidence_tier = 4  # 自发现定律默认为探索性编码
            library.register(law)
            learned.append(final_name)
        except Exception:
            pass

    if learned:
        _save_auto_laws()

    return {
        "learned": learned,
        "attempted": len(candidates),
        "success": len(learned) > 0 and not any("[blocked:" in l for l in learned),
        "patterns": {
            "convergences": sum(1 for c in candidates if c.get("source_type") == "chain_convergence"),
            "bridges": sum(1 for c in candidates if c.get("source_type") == "cross_domain_bridge"),
        },
        "max_chain_tier": max_chain_tier,
        "blocked_by_tier": blocked_by_tier,
    }


def learn_external_mentions(agent, answer: str) -> Dict:
    """
    从 LLM 回答中检测外部知识, 逐个向 LLM 学习。

    流程:
      1. 检测答案中提到的外部定律名
      2. 逐个问 LLM: "请描述这个定律"
      3. 解析 LLM 返回的 JSON
      4. 物理验证 + 入库
    """
    external = detect_external_mentions(answer)
    if not external:
        return {"learned": [], "attempted": 0, "success": False}

    bridge = agent.llm
    if not bridge or not bridge.is_available():
        return {"learned": [], "attempted": len(external), "success": False}

    from physics.laws import library, PhysicsLaw, ConstraintType
    learned = []

    for law_name in external[:5]:  # 每次最多学 5 条
        prompt = (
            f"请描述物理定律 '{law_name}'。以 JSON 格式返回:\n"
            '{"name": "定律名", "latex": "数学公式", '
            '"inputs": ["输入变量1", "输入变量2"], '
            '"outputs": ["输出变量"], '
            '"domain": "领域", '
            '"causal_direction": [["原因", "结果"]]}\n\n'
            "只返回 JSON。"
        )
        try:
            response = bridge.client.chat([{"role": "user", "content": prompt}])
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                import json
                data = json.loads(json_match.group())
                name = data.get("name", law_name)
                
                # 黑名单: 太通用的概念不学
                if any(g in name for g in ["物理定律", "该定律", "m定律", "一个几何", "一个分析"]):
                    continue
                
                # 去重检查 — 需要名称 + 变量双重匹配
                existing = False
                new_vars = set(v.lower() for v in data.get("inputs", []) + data.get("outputs", []))
                for law in library.list_all():
                    law_vars = set(v.lower() for v in law.inputs + law.outputs)
                    name_sim = (name.lower() in law.name.lower() or law.name.lower() in name.lower())
                    var_overlap = len(new_vars & law_vars) / max(len(new_vars | law_vars), 1) if new_vars else 0
                    if name_sim and var_overlap > 0.3:
                        existing = True; break
                if existing:
                    continue
                
                law = PhysicsLaw(
                    name=name,
                    domain=data.get("domain", "auto"),
                    latex=data.get("latex", ""),
                    inputs=data.get("inputs", []),
                    outputs=data.get("outputs", []),
                    constraint_type=ConstraintType.SCM_EQUATION,
                    formula=lambda *args: 0.0,
                    causal_direction=[tuple(d) for d in data.get("causal_direction", [])],
                    forbidden_directions=[],
                )
                law._auto_learned = True
                library.register(law)
                learned.append(name)
        except Exception:
            pass

    if learned:
        _save_auto_laws()

    return {
        "learned": learned,
        "attempted": len(external),
        "success": len(learned) > 0,
    }
