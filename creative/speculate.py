"""
speculate — 无约束大胆假设

与 innovation_engine 的区别:
  innovation_engine:  受 forbidden + 本体论约束, 生成 tier 3 候选 (小心求证)
  speculate:          无约束自由关联, 生成 tier 4 探索编码 (大胆假设)

原则:
  - 不检查 forbidden — 这是沙盒, 什么都可以想
  - 不要求公理链一致 — 可以违反现有物理
  - 不排斥已有边 — 可以"重新发明"已知关系
  - 全部标记 tier 4 — 绝对不会自动升级
  - 可以跨任意域、任意尺度、任意变量对
  - 输出带"为什么这么想"的简短理由 (种子)

用法:
  speculate 10    → 生成 10 条大胆假说
  speculate --save → 生成并保存到 auto_laws (tier 4)
"""

from __future__ import annotations
from typing import Dict, List, Set
import random
import json
import os
import time

# ── 联想种子: 物理直觉中的非标准连接 ──
SPECULATIVE_SEEDS = [
    # (变量A, 变量B, 为什么值得想)
    ("entropy", "wave_function", "熵和信息在黑洞热力学和量子测量中可能共享结构"),
    ("collapse_probability", "spacetime_curvature", "如果坍缩改变度规? (Penrose 引力坍缩)"),
    ("quantum_amplitude", "temperature", "量子涨落和热涨落可能有统一的统计描述"),
    ("gauge_field", "consciousness", "如果观测者的对称群决定可观测的物理?"),
    ("compact_dimension", "entropy", "额外维度的卷曲可能是熵的几何来源"),
    ("dark_energy", "quantum_amplitude", "宇宙学常数 = 真空量子涨落的总和?"),
    ("magnetic_field", "spacetime_curvature", "电磁场和引力场在 Kaluza-Klein 中统一"),
    ("virtual_particles", "mass", "希格斯机制: 虚粒子的凝聚产生质量"),
    ("phase", "geodesic_path", "几何相位(Berry phase)是否影响粒子在时空中的路径?"),
    ("measurement", "time", "量子测量是否定义时间箭头?"),
    ("wavelength", "entropy", "热波长: 温度是否决定量子相干尺度?"),
    ("scalar_field", "collapse_probability", "暴胀子场是否和坍缩机制共享动力学?"),
    ("mixed_state", "geodesic_path", "退相干路径是否偏向特定测地线?"),
    ("charge", "higher_d_metric", "电荷是否是额外维度中的动量?"),
    ("force_gravity", "quantum_amplitude", "引力子: 引力的量子传播子"),
]


def speculate(n: int = 10) -> List[Dict]:
    """
    无约束生成大胆假说。

    来源:
      - 联想种子 (SPECULATIVE_SEEDS)
      - 随机变量对 (不加任何过滤)
      - 跨域强关联 (随机抽不同域变量)
    """
    from physics.laws import library, classify_variable

    # 收集所有变量
    all_vars = set()
    var_domains = {}
    for law in library.list_all():
        for v in law.inputs + law.outputs:
            all_vars.add(v)
            var_domains.setdefault(v, set()).add(law.domain)

    vars_list = list(all_vars)
    speculations = []

    # 策略 1: 联想种子 (优先)
    for src, dst, why in SPECULATIVE_SEEDS:
        if len(speculations) >= n:
            break
        speculations.append({
            "src": src,
            "dst": dst,
            "why": why,
            "source": "speculative_seed",
            "confidence_tier": 4,
        })

    # 策略 2: 随机跨域对
    attempts = 0
    while len(speculations) < n and attempts < n * 20:
        attempts += 1
        a = random.choice(vars_list)
        b = random.choice(vars_list)
        if a == b:
            continue

        # 偏向跨域
        domains_a = var_domains.get(a, set())
        domains_b = var_domains.get(b, set())
        cross = not domains_a.intersection(domains_b)

        # 生成简短理由
        if cross:
            dom_a = list(domains_a)[:2]
            dom_b = list(domains_b)[:2]
            why = f"跨域关联: {', '.join(dom_a)} 的 {a} 是否影响 {', '.join(dom_b)} 的 {b}?"
        else:
            why = f"同域探索: {a} 和 {b} 是否有未被发现的因果边?"

        speculations.append({
            "src": a,
            "dst": b,
            "why": why,
            "source": "random_cross_domain" if cross else "random_same_domain",
            "confidence_tier": 4,
        })

    return speculations[:n]


def speculate_report() -> str:
    """可读的大胆假设报告"""
    speculations = speculate(10)

    lines = [
        "══════ 大胆假设 (tier 4 · 沙盒) ══════",
        "  以下假说不受任何约束:",
        "  - 可能违反已知物理",
        "  - 可能没有实验验证手段",
        "  - 不会进入因果推导",
        "  - 纯粹探索性编码",
        "",
    ]

    for i, s in enumerate(speculations):
        if s["source"] == "speculative_seed":
            marker = "★"  # 基于物理直觉的种子
        else:
            marker = "·"
        lines.append(f"  {i+1}. {marker} {s['src']} → {s['dst']}")
        lines.append(f"     为何: {s['why'][:120]}")
        lines.append("")

    lines.append(f"  生成: {len(speculations)} 条 | 来源: 种子 {sum(1 for s in speculations if s['source']=='speculative_seed')} + 随机 {sum(1 for s in speculations if s['source']!='speculative_seed')}")
    lines.append("  所有假说均为 tier 4 — 除非经过完整验证循环, 不会升级。")
    return "\n".join(lines)


def speculate_save() -> str:
    """生成并保存到 auto_laws"""
    speculations = speculate(10)

    from data_paths import auto_laws_path; auto_path = auto_laws_path()
    existing = []
    if os.path.exists(auto_path):
        try:
            with open(auto_path) as f:
                existing = json.load(f)
        except Exception:
            pass

    added = 0
    for s in speculations:
        entry = {
            "name": f"Speculation_{s['src']}_{s['dst']}",
            "domain": "speculation",
            "latex": "",
            "inputs": [s["src"]],
            "outputs": [s["dst"]],
            "causal_direction": [[s["src"], s["dst"]]],
            "confidence_tier": 4,
            "_discovery_note": f"[SPECULATE] {s['why']}",
            "_speculation_source": s["source"],
        }
        existing.append(entry)
        added += 1

    with open(auto_path, "w") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    return f"已保存 {added} 条大胆假说到 data/auto_laws.json (全部 tier 4)"
