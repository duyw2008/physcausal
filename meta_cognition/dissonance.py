"""
认知失调检测 — 内在驱动力的雏形

扫描定律库，找出 ""这个地方对不上"" 的位置:
  1. 两个定律覆盖相同变量，但因果方向冲突
  2. 两个定律来自不同领域，但共享输入/输出模式
  3. 一个定律的 forbidden_direction 恰好是另一个定律在特殊条件下的合理方向

每种冲突都是一个 ""值得研究的问题""，
不需要用户提问。
"""

from __future__ import annotations
from typing import Dict, List, Tuple


def detect_domain_boundaries() -> List[Dict]:
    """
    检测跨领域定律之间的张力。

    例如:
      Gravity (mechanics) 说质量决定引力
      EquivalencePrinciple (general_relativity) 说引力等于加速
      → 问题: 惯性质量和引力质量为什么相等？
    """
    from physics.laws import library
    laws = library.list_all()

    conflicts = []

    for i, law_a in enumerate(laws):
        for j, law_b in enumerate(laws):
            if i >= j:
                continue
            if law_a.domain == law_b.domain:
                continue  # 同领域不检测

            a_vars = set(law_a.inputs + law_a.outputs)
            b_vars = set(law_b.inputs + law_b.outputs)

            # 条件 1: 变量重叠
            overlap = a_vars & b_vars
            if not overlap:
                continue

            # 条件 2: 因果方向冲突或互补
            a_dirs = set(tuple(d) for d in law_a.causal_direction)
            b_dirs = set(tuple(d) for d in law_b.causal_direction)
            b_forbidden = set(tuple(d) for d in law_b.forbidden_directions)

            conflict_type = None
            question = None

            # A 的因果方向在 B 中是禁止的
            for d in a_dirs:
                if d in b_forbidden:
                    conflict_type = "forbidden_in_other_domain"
                    question = (
                        f"{law_a.name} ({law_a.domain}) 说 {d[0]}→{d[1]}，"
                        f"但 {law_b.name} ({law_b.domain}) 禁止这个方向。"
                        f"在什么条件下 {law_a.domain} 的规则优先？"
                    )
                    break

            # 变量重叠但因果方向互补 (如 A 的输入是 B 的输出)
            if not conflict_type:
                a_inputs = set(law_a.inputs)
                b_outputs = set(law_b.outputs)
                complementary = a_inputs & b_outputs
                if complementary:
                    conflict_type = "complementary_cross_domain"
                    var_name = list(complementary)[0]
                    question = (
                        f"{law_a.name} ({law_a.domain}) 将 {var_name} 作为输入，"
                        f"{law_b.name} ({law_b.domain}) 将 {var_name} 作为输出。"
                        f"在 {law_a.domain} ↔ {law_b.domain} 的边界上，{var_name} 的因果角色如何转换？"
                    )

            if conflict_type:
                conflicts.append({
                    "law_a": law_a.name,
                    "law_b": law_b.name,
                    "domain_a": law_a.domain,
                    "domain_b": law_b.domain,
                    "overlap": sorted(overlap),
                    "type": conflict_type,
                    "question": question,
                })

    return conflicts


def detect_scale_boundaries() -> List[Dict]:
    """
    检测尺度边界: 经典 ↔ 量子, 经典 ↔ 相对论。

    例如:
      Angular Momentum (经典力学) 说 L 守恒
      但 Schwarzschild (广义相对论) 说足够质量下会坍缩成黑洞
      → 在黑洞视界上角动量还守恒吗？
    """
    from physics.laws import library

    SCALE_MAP = {
        "mechanics": "classical",
        "electromagnetism": "classical",
        "thermodynamics": "classical",
        "fluids": "classical",
        "optics": "classical",
        "acoustics": "classical",
        "modern": "classical",
        "auto": "classical",
        "unknown": "classical",
        "quantum": "quantum",
        "general_relativity": "relativistic",
    }

    laws = library.list_all()
    boundaries = []

    for i, law_a in enumerate(laws):
        scale_a = SCALE_MAP.get(law_a.domain, "unknown")
        for j, law_b in enumerate(laws):
            if i >= j:
                continue
            scale_b = SCALE_MAP.get(law_b.domain, "unknown")
            if scale_a == scale_b:
                continue

            # 检测共享的物理概念 (通过变量名)
            a_vars = set(law_a.inputs + law_a.outputs)
            b_vars = set(law_b.inputs + law_b.outputs)
            overlap = a_vars & b_vars

            if overlap or law_a.name.lower() in law_b.name.lower() or law_b.name.lower() in law_a.name.lower():
                boundaries.append({
                    "law_a": law_a.name,
                    "law_b": law_b.name,
                    "scale_a": scale_a,
                    "scale_b": scale_b,
                    "question": (
                        f"{law_a.name} ({scale_a}) 和 {law_b.name} ({scale_b}) "
                        f"分别在不同的物理尺度上成立。它们在过渡区域如何衔接？"
                    ),
                })

    return boundaries


def generate_questions() -> List[str]:
    """生成 ""值得研究的问题"" 列表"""
    questions = []

    for c in detect_domain_boundaries():
        questions.append(c["question"])

    for b in detect_scale_boundaries():
        questions.append(b["question"])

    return questions


def cognitive_summary() -> str:
    """人类可读的认知失调报告"""
    lines = ["=== 认知失调检测 (Cognitive Dissonance) ==="]
    lines.append("")

    domain_conflicts = detect_domain_boundaries()
    scale_boundaries = detect_scale_boundaries()

    if domain_conflicts:
        lines.append(f"跨领域张力: {len(domain_conflicts)} 处")
        for c in domain_conflicts[:5]:
            lines.append(f"  ⚡ {c['domain_a']} ↔ {c['domain_b']}")
            lines.append(f"     {c['question']}")
            lines.append("")

    if scale_boundaries:
        lines.append(f"尺度边界: {len(scale_boundaries)} 处")
        for b in scale_boundaries[:5]:
            lines.append(f"  🌐 {b['scale_a']} ↔ {b['scale_b']}")
            lines.append(f"     {b['law_a']} × {b['law_b']}")
            lines.append(f"     {b['question']}")
            lines.append("")

    if not domain_conflicts and not scale_boundaries:
        lines.append("  未检测到认知失调。定律库内部一致。")

    return "\n".join(lines)
