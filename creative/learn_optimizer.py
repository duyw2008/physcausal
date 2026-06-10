"""
学习优化器 — 从因果图结构中学习类比权重

混合路线第二步: 替代手工相似度规则,
用已知物理类比做正样本, 学习最优特征权重。
"""

from __future__ import annotations
from typing import Dict, List, Tuple
import json, os, math, random
from collections import defaultdict


# ── 已知物理类比 (正样本) ──

KNOWN_ANALOGIES = [
    # Kaluza-Klein 系列
    ("compact_dimension", "current"),
    ("higher_d_metric", "current"),
    ("momentum", "compact_dimension"),
    ("gauge_field", "spacetime_curvature"),
    # 耗散统一
    ("kinetic_energy_loss", "mixed_state"),
    ("phase_coherence", "kinetic_energy"),
    ("entropy", "information_loss"),
    # Wheeler 几何同一性
    ("geodesic_path", "gauge_field"),
    ("spacetime_curvature", "gauge_field"),
    # 量子-经典对应
    ("wavelength", "gauge_field"),
    ("frequency", "spacetime_curvature"),
]


def _build_training_data(n_negative: int = 20) -> Tuple[List, List]:
    """构建训练数据: 正样本 = 已知类比, 负样本 = 随机跨域对"""
    from creative.graph_features import extract_graph_features, chain_embedding
    from inference.counterfactual_chain import propagate

    features = extract_graph_features()
    all_vars = list(features.keys())

    def chain_vars(start):
        vars_list = [start]
        try:
            chain = propagate(start, "变化", max_depth=5)
            for step in chain:
                if "error" in step:
                    continue
                eff = step.get("effect_variable", "")
                if eff and eff not in vars_list:
                    vars_list.append(eff)
        except:
            pass
        return vars_list

    # 正样本
    X_pos = []
    for a, b in KNOWN_ANALOGIES:
        va = chain_vars(a)
        vb = chain_vars(b)
        emb_a = chain_embedding(va, features)
        emb_b = chain_embedding(vb, features)
        diff = [abs(x - y) for x, y in zip(emb_a, emb_b)]
        X_pos.append(diff)

    # 负样本: 随机跨域对
    from physics.laws import classify_variable
    X_neg = []
    for _ in range(n_negative):
        while True:
            a = random.choice(all_vars)
            b = random.choice(all_vars)
            if a == b:
                continue
            # 确保跨域 (不同类别)
            if classify_variable(a) != classify_variable(b):
                # 排除已知类比
                if (a, b) not in KNOWN_ANALOGIES and (b, a) not in KNOWN_ANALOGIES:
                    break
        va = chain_vars(a)
        vb = chain_vars(b)
        emb_a = chain_embedding(va, features)
        emb_b = chain_embedding(vb, features)
        diff = [abs(x - y) for x, y in zip(emb_a, emb_b)]
        X_neg.append(diff)

    return X_pos, X_neg


def learn_weights(learning_rate: float = 0.01, epochs: int = 100) -> List[float]:
    """
    学习特征权重向量。

    目标: 正样本的加权距离小, 负样本的加权距离大。
    等效于: 学习哪些特征维度对类比检测最重要。
    """
    X_pos, X_neg = _build_training_data()

    if not X_pos:
        return [1.0] * 15  # 默认均匀权重

    n_features = len(X_pos[0])
    weights = [1.0] * n_features

    for epoch in range(epochs):
        # 梯度: 减小正样本距离, 增大负样本距离
        grad = [0.0] * n_features
        
        # 正样本梯度 (应减小距离)
        for x in X_pos:
            dist = sum(w * d for w, d in zip(weights, x))
            if dist > 0:
                for i in range(n_features):
                    grad[i] -= x[i] / max(dist, 0.01)

        # 负样本梯度 (应增大距离)
        for x in X_neg:
            dist = sum(w * d for w, d in zip(weights, x))
            if dist < 10:  # 上限
                for i in range(n_features):
                    grad[i] += x[i] / max(10 - dist, 0.01)

        # 更新权重
        for i in range(n_features):
            weights[i] = max(0.01, weights[i] + learning_rate * grad[i] / max(len(X_pos), 1))

        # L2 归一化
        norm = math.sqrt(sum(w*w for w in weights))
        if norm > 0:
            weights = [w / norm for w in weights]

    return weights


def learned_similarity(var_a: str, var_b: str, weights: Optional[List[float]] = None) -> float:
    """
    使用学习到的权重计算类比相似度。
    与 analogy_similarity() 的区别: 特征维度被学习到的权重重新加权。
    """
    from creative.graph_features import extract_graph_features, chain_embedding
    from inference.counterfactual_chain import propagate

    if weights is None:
        weights_path = os.path.expanduser("~/.hermes/physcausal_learned_weights.json")
        try:
            with open(weights_path) as f:
                weights = json.load(f)
        except:
            # 回退到学习
            weights = learn_weights()
            try:
                os.makedirs(os.path.dirname(weights_path), exist_ok=True)
                with open(weights_path, "w") as f:
                    json.dump(weights, f)
            except:
                pass

    features = extract_graph_features()

    def chain_vars(start):
        vars_list = [start]
        try:
            chain = propagate(start, "变化", max_depth=5)
            for step in chain:
                if "error" in step:
                    continue
                eff = step.get("effect_variable", "")
                if eff and eff not in vars_list:
                    vars_list.append(eff)
        except:
            pass
        return vars_list

    emb_a = chain_embedding(chain_vars(var_a), features)
    emb_b = chain_embedding(chain_vars(var_b), features)

    # 加权欧氏距离 → 相似度
    dist = math.sqrt(sum(w * (a-b)**2 for w, a, b in zip(weights, emb_a, emb_b)))
    return 1.0 / (1.0 + dist)  # Sigmoid-like


def train_and_report() -> str:
    """训练并报告学习结果"""
    weights = learn_weights()

    # 特征名称
    feature_names = [
        "in_deg", "out_deg", "depth", "entropy_dist",
        "dom:classical", "dom:quantum", "dom:geometry", "dom:thermo",
        "cat:fundamental", "cat:geometric", "cat:quantum", "cat:derived",
        "branching", "is_root", "chain_length",
    ]

    lines = ["═══ 学习优化器 ═══"]
    lines.append(f"  已知类比: {len(KNOWN_ANALOGIES)} 对")
    lines.append(f"  训练轮数: 100")
    lines.append("")
    lines.append("  特征权重 (高→重要):")
    
    ranked = sorted(zip(feature_names, weights), key=lambda x: x[1], reverse=True)
    for name, w in ranked:
        bar = "█" * int(w * 20) + "░" * (20 - int(w * 20))
        lines.append(f"    {name:<20s} {w:.3f} {bar}")

    # 测试
    lines.append("")
    lines.append("  测试类比:")
    test_pairs = [
        ("compact_dimension", "current"),
        ("momentum", "compact_dimension"),
        ("kinetic_energy", "temperature"),  # 不应是类比 (同域)
    ]
    for a, b in test_pairs:
        sim = learned_similarity(a, b, weights)
        lines.append(f"    {a} ↔ {b}: {sim:.0%}")

    return "\n".join(lines)
