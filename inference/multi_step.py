"""
多步推理 — 因果链组合查询

不只是单变量传播, 而是多步假设场景:
  "如果退相干加速, 熵增多少? 会影响对称破缺吗?"
"""

from __future__ import annotations
from typing import Dict, List


def multi_step_reason(query: str) -> str:
    """
    多步因果推理。

    格式: "变量A 变化 → 问变量B | 变量C"
           "kinetic_energy 增加 → entropy | broken_symmetry"

    步骤:
      1. 传播 A
      2. 检查 B 是否可达
      3. 如果可达, 继续传播到 C
    """
    from inference.counterfactual_chain import propagate, format_chain

    parts = query.split("→")
    if len(parts) < 2:
        return "格式: <var> <change> → <target1> | <target2>"

    start_part = parts[0].strip()
    targets = [t.strip() for t in parts[1].split("|")]

    # 解析起始: "变量 变化"
    start_words = start_part.split()
    if len(start_words) < 2:
        return "格式: <var> <change> → <target1> | <target2>  例如: temperature 升高 → entropy | broken_symmetry"

    var = start_words[0]
    change = " ".join(start_words[1:])

    lines = [f"═══ 多步推理: {var} {change} ═══"]

    # Step 1: 传播
    chain = propagate(var, change, max_depth=8)
    lines.append(format_chain(chain))
    lines.append("")

    # Step 2: 检查每个目标
    reached_vars = set()
    for step in chain:
        if "error" in step:
            continue
        reached_vars.add(step.get("effect_variable", ""))

    for target in targets:
        if target in reached_vars:
            # 找到到达路径
            paths = []
            for step in chain:
                if step.get("effect_variable") == target:
                    path_vars = [var]
                    # 回溯路径
                    current = target
                    for s in chain:
                        if s.get("effect_variable") == current:
                            cause = s.get("cause_variable", "")
                            if cause and cause not in path_vars:
                                path_vars.append(cause)
                                current = cause
                    paths.append(path_vars)

            lines.append(f"  ✓ {var} → {target}: 可达 ({len(paths)} 条路径)")
            if paths:
                # 简短路径
                short_path = " → ".join(reversed(paths[0][-4:]))
                lines.append(f"    最短: {short_path}")

            # 量化: 检查沿途是否有数值定律
            has_quant = False
            for step in chain:
                if step.get("effect_variable") == target:
                    law = step.get("law", "")
                    if any(c.isdigit() for c in law):
                        has_quant = True
            if has_quant:
                lines.append(f"    (可量化 — 沿途有数值定律)")
            else:
                lines.append(f"    (定性 — 方向已知, 数值需额外数据)")
        else:
            lines.append(f"  ✗ {var} → {target}: 不可达 (因果图缺边)")
            # 建议补边
            lines.append(f"    建议: speculate 探索 {var} ↔ {target} 的桥接")

    # 汇总
    reached_count = sum(1 for t in targets if t in reached_vars)
    lines.append(f"\n  总计: {reached_count}/{len(targets)} 目标可达")

    return "\n".join(lines)


def multi_step_report() -> str:
    """展示几条重要的多步推理路径"""
    queries = [
        "temperature 升高 → entropy | broken_symmetry",
        "velocity 增加 → entropy | drag_force",
        "environment_coupling 增强 → entropy | collapse_probability",
    ]

    parts = []
    for q in queries:
        parts.append(multi_step_reason(q))
        parts.append("")

    return "\n".join(parts)
