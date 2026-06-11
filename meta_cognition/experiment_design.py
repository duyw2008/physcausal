"""
实验设计 — 从因果断裂中生成干预建议

Noether 发现验证断裂后, 能说 "该做什么实验来验证这条边"。
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json, os
from data_paths import load_cv_summary, data_path


def _discoveries_with_gaps() -> List[Dict]:
    """找出有验证断裂的发现 + 缺失的桥接"""
    cv = load_cv_summary()
    gaps = []
    for r in cv:
        if r.get("convergence_preserved") is False:
            gaps.append({
                "discovery": r.get("discovery", "?"),
                "domain": r.get("target_domain", "?"),
                "inputs": r.get("inputs", []),
                "outputs": r.get("outputs", []),
                "missing_bridge": r.get("quantum_assessment", {}).get("missing_bridge", ""),
            })
    return gaps


def suggest_experiment(gap: Dict) -> str:
    """
    为一条因果断裂设计实验。
    
    策略:
      - 如果有缺失桥梁 → 建议直接测量桥梁变量
      - 如果只缺域连接 → 建议寻找该域的实验验证
    """
    discovery = gap.get("discovery", "?")
    domain = gap.get("domain", "?")
    bridge = gap.get("missing_bridge", "")
    inputs = gap.get("inputs", [])
    outputs = gap.get("outputs", [])

    if bridge:
        return (
            f"【{discovery} @ {domain}】\n"
            f"  缺失桥梁: {bridge}\n"
            f"  建议: 设计测量 {bridge.split('→')[0].strip()} 的实验,\n"
            f"        观察是否影响 {outputs[0] if outputs else '?'}。\n"
            f"        例如: 在低温/高真空条件下测量环境耦合与熵增的关系。"
        )
    elif domain == "quantum" and inputs:
        return (
            f"【{discovery} @ quantum】\n"
            f"  建议: 在量子系统中直接操作 {' 或 '.join(inputs[:2])},\n"
            f"        测量其对 {outputs[0] if outputs else '?'} 的影响。\n"
            f"        例如: 用 trapped ion / superconducting qubit 平台。"
        )
    else:
        return (
            f"【{discovery} @ {domain}】\n"
            f"  输入: {', '.join(inputs[:2])} → 输出: {', '.join(outputs[:2])}\n"
            f"  建议: 设计 {domain} 域实验, 干预输入变量, 测量输出。"
        )


def experiment_plan_report() -> str:
    """为所有验证断裂生成实验计划"""
    gaps = _discoveries_with_gaps()
    
    lines = [f"═══ 实验设计 ({len(gaps)} 条断裂) ═══"]
    lines.append("")
    
    if not gaps:
        lines.append("  所有交叉验证均通过。无断裂需要实验验证。")
        return "\n".join(lines)
    
    for i, gap in enumerate(gaps):
        lines.append(f"  {i+1}. {suggest_experiment(gap)}")
        lines.append("")
    
    # 优先级建议
    priorities = []
    for gap in gaps:
        if gap.get("missing_bridge"):
            priorities.append(f"高: {gap['discovery']} — 有明确缺失桥梁, 可直接设计实验")
        elif gap["domain"] == "quantum":
            priorities.append(f"中: {gap['discovery']} — 量子域实验可行, 平台成熟")
        else:
            priorities.append(f"低: {gap['discovery']} — 需进一步分析")
    
    lines.append("── 优先级 ──")
    for p in priorities[:5]:
        lines.append(f"  {p}")
    
    return "\n".join(lines)
