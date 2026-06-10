"""
因果图结构特征提取 — 混合路线的第一步

从因果图中提取每个变量的结构特征,
用于学习因果链的向量表示。

不依赖神经网络, 纯图结构计算。
"""

from __future__ import annotations
from typing import Dict, List, Set, Tuple
from collections import defaultdict
import math


def extract_graph_features() -> Dict[str, List[float]]:
    """
    从因果图中提取每个变量的结构特征向量。

    特征维度 (8):
      - in_degree: 多少个定律以该变量为输出
      - out_degree: 多少个定律以该变量为输入
      - depth_from_root: 从根变量 (无输入) 到该变量的最大深度
      - steps_to_entropy: 到 entropy 的最短路径步数
      - domain_onehot: 所属域 (4位: classical/quantum/geometry/thermo)
      - var_category: 变量类别 (fundamental/geometric/quantum/derived, 4位)
      - branching: 下游分支数
      - root_count: 上游根数

    返回: {variable_name: [feature_vector]}
    """
    from physics.laws import library, classify_variable
    from inference.counterfactual_chain import propagate

    # 构建邻接矩阵
    graph: Dict[str, List[str]] = defaultdict(list)
    reverse_graph: Dict[str, List[str]] = defaultdict(list)
    all_vars = set()

    for law in library.list_all():
        for src, dst in law.causal_direction:
            graph[src].append(dst)
            reverse_graph[dst].append(src)
            all_vars.add(src)
            all_vars.add(dst)

    # 计算每个变量的深度 (BFS 从根开始)
    roots = {v for v in all_vars if v not in reverse_graph or not reverse_graph[v]}
    depth: Dict[str, int] = {}
    for root in roots:
        depth[root] = 0
        queue = [(root, 0)]
        visited = {root}
        while queue:
            node, d = queue.pop(0)
            for child in graph.get(node, []):
                if child not in visited:
                    visited.add(child)
                    depth[child] = max(depth.get(child, 0), d + 1)
                    queue.append((child, d + 1))

    # 到 entropy 的最短路径
    entropy_dist: Dict[str, int] = {}
    for var in all_vars:
        try:
            chain = propagate(var, "变化", max_depth=8)
            dist = 999
            for step in chain:
                if "error" in step:
                    continue
                if "entropy" in step.get("effect_variable", ""):
                    dist = step.get("depth", 999)
                    break
            entropy_dist[var] = dist
        except Exception:
            entropy_dist[var] = 999

    # 构建特征向量
    features = {}
    for var in all_vars:
        cat = classify_variable(var)

        # 1-2. 度
        in_deg = len(reverse_graph.get(var, []))
        out_deg = len(graph.get(var, []))

        # 3. 深度
        d = depth.get(var, 0)

        # 4. 到熵的步数 (归一化)
        e_dist = min(entropy_dist.get(var, 999), 20) / 20.0

        # 5. 域 one-hot
        domains = set()
        for law in library.list_all():
            if var in law.inputs or var in law.outputs:
                dom = law.domain
                if "quantum" in dom.lower() or "量子" in dom:
                    domains.add("quantum")
                elif "relativity" in dom.lower() or "geometry" in dom.lower() or "相对论" in dom or "几何" in dom:
                    domains.add("geometry")
                elif "thermo" in dom.lower() or "热" in dom:
                    domains.add("thermo")
                else:
                    domains.add("classical")
        dom_vec = [
            1.0 if "classical" in domains else 0.0,
            1.0 if "quantum" in domains else 0.0,
            1.0 if "geometry" in domains else 0.0,
            1.0 if "thermo" in domains else 0.0,
        ]

        # 6. 类别 one-hot
        cat_vec = [
            1.0 if cat == "fundamental" else 0.0,
            1.0 if cat == "geometric" else 0.0,
            1.0 if cat == "quantum" else 0.0,
            1.0 if cat == "derived" else 0.0,
        ]

        # 7-8. 分支/根
        branching = len(graph.get(var, []))
        root_c = 1.0 if var in roots else 0.0

        vec = [
            float(in_deg) / 10.0,      # 入度
            float(out_deg) / 10.0,     # 出度
            float(d) / 10.0,           # 深度
            e_dist,                     # 到熵距离
            *dom_vec,                   # 域 (4)
            *cat_vec,                   # 类别 (4)
            float(branching) / 10.0,   # 分支
            root_c,                     # 是根
        ]

        features[var] = vec

    return features


def chain_embedding(chain_vars: List[str],
                    features: Dict[str, List[float]]) -> List[float]:
    """
    将因果链 (变量序列) 嵌入为单个向量。

    策略: 取链上所有变量特征的平均值。
    链长度自带结构信息 — 更长链 = 更复杂的因果路径。
    """
    if not chain_vars:
        return [0.0] * 14  # 默认零向量

    vecs = []
    for var in chain_vars:
        if var in features:
            vecs.append(features[var])
        else:
            vecs.append([0.0] * 14)

    n = len(vecs)
    avg = [sum(v[i] for v in vecs) / n for i in range(14)]

    # 附加: 链长度 (归一化)
    avg.append(min(n / 20.0, 1.0))

    return avg


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """余弦相似度"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def analogy_similarity(var_a: str, var_b: str) -> float:
    """
    基于图结构嵌入计算两个变量的类比相似度。

    比手工 _chain_similarity() 更客观——
    相似度直接来自因果图拓扑, 不依赖人工规则。
    """
    features = extract_graph_features()

    # 获取两个变量的因果链
    from inference.counterfactual_chain import propagate

    def chain_vars(start_var: str) -> List[str]:
        vars_list = [start_var]
        try:
            chain = propagate(start_var, "变化", max_depth=5)
            for step in chain:
                if "error" in step:
                    continue
                eff = step.get("effect_variable", "")
                if eff and eff not in vars_list:
                    vars_list.append(eff)
        except Exception:
            pass
        return vars_list

    va = chain_vars(var_a)
    vb = chain_vars(var_b)

    emb_a = chain_embedding(va, features)
    emb_b = chain_embedding(vb, features)

    return cosine_similarity(emb_a, emb_b)


def compare_analogies(n_pairs: int = 10) -> str:
    """
    对比手工相似度 vs 图嵌入相似度

    用于评估混合路线的第一步效果。
    注意: 这是可选工具, 不导入 causal_analogy 避免循环依赖。
    直接使用 graph_features 自己的相似度。
    """
    # 延迟导入避免循环
    from inference.counterfactual_chain import propagate
    from physics.laws import library, classify_variable
    
    # 直接用 graph_features 的嵌入计算类比
    features = extract_graph_features()
    
    # 选一些跨域变量对
    start_vars = []
    for law in library.list_all():
        for v in law.inputs:
            cat = classify_variable(v)
            if cat in ("fundamental", "geometric", "quantum"):
                start_vars.append(v)
    start_vars = list(set(start_vars))[:n_pairs]
    
    # 计算 pairwise 相似度
    pairs = []
    for i, va in enumerate(start_vars):
        for vb in start_vars[i+1:]:
            sim = analogy_similarity(va, vb)
            if sim >= 0.5:
                pairs.append((va, vb, sim))
    pairs.sort(key=lambda x: x[2], reverse=True)

    print("=== 图嵌入类比发现 (纯图拓扑) ===\n")

    for i, (va, vb, sim) in enumerate(pairs[:8]):
        print(f"  {i+1}. {va} ↔ {vb}: {sim:.0%}")
        print()

    return ""
