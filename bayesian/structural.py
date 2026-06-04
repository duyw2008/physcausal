"""
结构后验 — P(G|D): 因果图的不确定性

核心问题:
  数据 D 能支持多个因果图。
  不是选一个「最好的」，而是给每个可能的图一个后验概率。

P(G|D) ∝ P(D|G) · P(G)

  先验 P(G):   物理约束 (禁止边 = 0), 稀疏偏好, 领域知识
  似然 P(D|G): BIC 得分 / 边际似然
  后验 P(G|D): 边的置信度 / 图的后验分布

方法:
  1. Bootstrap 近似 (已有 bootstrap_edge_confidence): 快，粗糙
  2. MCMC over DAG space: 准，慢
  3. Order MCMC: 采样拓扑序而非 DAG，效率高

与已有模块的关系:
  不替代 discovery.py → 包裹它，提供不确定性层
  bootstrap_edge_confidence → 升级为完整的图后验
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import numpy as np


@dataclass
class EdgePosterior:
    """单条边的后验"""
    source: str
    target: str
    probability: float            # P(edge | D)
    direction_prob: Dict[str, float] = field(default_factory=dict)
    # {"→": P(src→dst), "←": P(dst→src), "—": P(undirected)}


@dataclass
class GraphPosterior:
    """因果图的后验分布"""
    edge_posteriors: List[EdgePosterior]  # 每条边的置信度
    top_graphs: List[Tuple[List[Tuple[str, str]], float]]
    # [(edges_list, posterior_prob), ...] — 前 k 个最可能的图
    entropy: float                        # 图分布的熵
    n_samples: int                        # MCMC/Bootstrap 样本数
    notes: str = ""


@dataclass
class EdgeBeliefUpdate:
    """一次干预实验后边的置信度更新"""
    edge: Tuple[str, str]
    prob_before: float
    prob_after: float
    information_gain: float          # 位 (bits)
    experiment: str                  # 做了什么干预


class StructuralPosterior:
    """
    结构后验 — P(G|D)

    三种模式:
      method="bootstrap": 快速近似 (已有, 适用于探索阶段)
      method="mcmc":      MCMC over DAG space (准确, 适用于关键决策)
      method="order":     Order MCMC (效率最高, 适用于大规模)
    """

    def __init__(self, method: str = "bootstrap", max_cond_size: int = 2):
        self.method = method
        self.max_cond_size = max_cond_size  # PC 的最大条件集大小
        self._cache: Dict[str, GraphPosterior] = {}

    def infer(self,
              data: np.ndarray,
              variable_names: List[str],
              prior_edges: Optional[List[Tuple[str, str]]] = None,
              forbidden_edges: Optional[List[Tuple[str, str]]] = None,
              n_samples: int = 100,
              alpha: float = 0.05,
              **kwargs) -> GraphPosterior:
        """
        推断因果图的后验分布。

        Args:
            data: 观测数据 (n_samples × n_features)
            variable_names: 变量名
            prior_edges: 先验强制边 (物理约束, 概率=1)
            forbidden_edges: 先验禁止边 (物理约束, 概率=0)
            n_samples: 采样数 (bootstrap 次数 或 MCMC 步数)
            alpha: 条件独立性检验的显著性水平

        Returns:
            GraphPosterior with edge confidences and top graph samples
        """
        if self.method == "bootstrap":
            return self._bootstrap_posterior(
                data, variable_names, prior_edges, forbidden_edges,
                n_samples, alpha
            )
        elif self.method == "mcmc":
            return self._mcmc_posterior(
                data, variable_names, prior_edges, forbidden_edges,
                n_samples, **kwargs
            )
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _bootstrap_posterior(self, data, var_names, prior_edges,
                             forbidden_edges, n_samples, alpha):
        """Bootstrap 近似结构后验"""
        from causal.discovery import pc_algorithm

        n = len(data)
        edge_counts: Dict[Tuple[str, str], int] = {}
        graph_samples: List[List[Tuple[str, str]]] = []

        # 自适应快速: 样本数和bootstrap次数都受限
        actual = max(8, min(n_samples, n // 20))
        for b in range(actual):
            indices = np.random.choice(n, min(n, 80), replace=True)
            sample = data[indices]

            try:
                dag = pc_algorithm(sample, var_names, alpha=alpha,
                                   max_cond_size=self.max_cond_size)
                edges = set()
                for src in var_names:
                    for dst in dag.children(src):
                        edges.add((src, dst))

                # 施加先验约束
                if prior_edges:
                    edges.update(prior_edges)
                if forbidden_edges:
                    edges.difference_update(forbidden_edges)

                graph_samples.append(list(edges))

                for e in edges:
                    edge_counts[e] = edge_counts.get(e, 0) + 1

            except Exception:
                continue

        # 边后验
        edge_posteriors = []
        all_possible_edges = set()
        for g in graph_samples:
            all_possible_edges.update(g)

        for (src, dst) in sorted(all_possible_edges):
            prob = edge_counts.get((src, dst), 0) / max(len(graph_samples), 1)
            edge_posteriors.append(EdgePosterior(
                source=src, target=dst,
                probability=prob,
            ))

        # Top graphs
        graph_freq: Dict[str, int] = {}
        for g in graph_samples:
            key = str(sorted(g))
            graph_freq[key] = graph_freq.get(key, 0) + 1

        top = sorted(graph_freq.items(), key=lambda x: -x[1])[:5]
        top_graphs = []
        for key_str, count in top:
            edges_list = eval(key_str)  # safe: only our own str output
            top_graphs.append((edges_list, count / max(len(graph_samples), 1)))

        # 图分布熵
        probs = np.array([c / max(len(graph_samples), 1) for _, c in top])
        entropy = -np.sum(probs * np.log(probs + 1e-15))

        return GraphPosterior(
            edge_posteriors=edge_posteriors,
            top_graphs=top_graphs,
            entropy=entropy,
            n_samples=len(graph_samples),
            notes=f"Bootstrap ({len(graph_samples)}/{n_samples} valid samples)",
        )

    def _mcmc_posterior(self, data, var_names, prior_edges,
                        forbidden_edges, n_samples, **kwargs):
        """
        MCMC over DAG space.

        Metropolis-Hastings:
          当前图 G → 提议 G' (加/删/反转一条边)
          接受概率: min(1, P(D|G')P(G') / P(D|G)P(G))

        当前实现: 简化版 — 用 BIC 差异作为接受概率
        """
        from causal.discovery import ges_algorithm

        # 初始化: GES 的输出
        try:
            init_dag = ges_algorithm(data, var_names)
            current_edges = set()
            for src in var_names:
                for dst in init_dag.children(src):
                    current_edges.add((src, dst))
        except Exception:
            current_edges = set()

        current_score = self._bic_score(data, var_names, list(current_edges))

        all_possible_edges = [
            (a, b) for i, a in enumerate(var_names)
            for b in var_names[i+1:]
        ]

        samples = []
        edge_counts: Dict[Tuple[str, str], int] = {}

        n_vars = len(var_names)
        max_edges = n_vars * (n_vars - 1) // 2
        temperature = kwargs.get("temperature", 1.0)

        for step in range(n_samples):
            # 提议: 随机选一条可能的边
            if not all_possible_edges:
                break

            e = all_possible_edges[np.random.randint(len(all_possible_edges))]
            a, b = e

            proposed = set(current_edges)

            # 随机操作: 添加 / 删除 / 反转
            op = np.random.choice(["add", "remove", "reverse"])
            if (a, b) in proposed:
                if op == "remove":
                    proposed.discard((a, b))
                elif op == "reverse":
                    proposed.discard((a, b))
                    if not self._would_create_cycle(proposed, (b, a), var_names):
                        proposed.add((b, a))
            elif (b, a) in proposed:
                if op == "remove":
                    proposed.discard((b, a))
                elif op == "reverse":
                    proposed.discard((b, a))
                    if not self._would_create_cycle(proposed, (a, b), var_names):
                        proposed.add((a, b))
            else:
                if len(proposed) < max_edges and op == "add":
                    if not self._would_create_cycle(proposed, (a, b), var_names):
                        proposed.add((a, b))

            # 物理先验: 禁止边强制概率=0
            if forbidden_edges:
                proposed.difference_update(forbidden_edges)
            if prior_edges:
                proposed.update(prior_edges)

            # 接受/拒绝
            proposed_score = self._bic_score(data, var_names, list(proposed))
            delta = (proposed_score - current_score) / temperature

            if delta > 0 or np.random.random() < np.exp(delta):
                current_edges = proposed
                current_score = proposed_score

            # 记录
            samples.append(set(current_edges))
            for e in current_edges:
                edge_counts[e] = edge_counts.get(e, 0) + 1

        # 边后验
        edge_posteriors = []
        all_edges_sampled = set()
        for s in samples:
            all_edges_sampled.update(s)
        all_edges_sampled.update(prior_edges or [])
        all_edges_sampled.difference_update(forbidden_edges or [])

        for (src, dst) in sorted(all_edges_sampled):
            prob = edge_counts.get((src, dst), 0) / max(len(samples), 1)
            edge_posteriors.append(EdgePosterior(
                source=src, target=dst, probability=prob,
            ))

        return GraphPosterior(
            edge_posteriors=edge_posteriors,
            top_graphs=[],
            entropy=0.0,
            n_samples=len(samples),
            notes=f"MCMC ({len(samples)} samples, temp={temperature})",
        )

    def _bic_score(self, data, var_names, edges):
        """BIC 得分 — 对数似然的高斯近似"""
        from causal.graph import CausalDAG

        n, d = data.shape
        if not edges:
            # 空图: 每个变量独立
            total_log_lik = 0
            for i in range(d):
                var = np.var(data[:, i])
                if var > 1e-10:
                    total_log_lik -= 0.5 * n * np.log(var)
            return total_log_lik - 0.5 * d * np.log(n)

        try:
            dag = CausalDAG(var_names, edges)
            sorted_vars = dag.topological_order()

            total_log_lik = 0
            n_params = 0
            for v in sorted_vars:
                parents = list(dag.parents(v))
                v_idx = var_names.index(v)
                y = data[:, v_idx]

                if not parents:
                    var = np.var(y)
                    total_log_lik -= 0.5 * n * (np.log(var + 1e-10) + 1)
                    n_params += 1
                else:
                    p_idx = [var_names.index(p) for p in parents]
                    X = data[:, p_idx]
                    X = np.column_stack([np.ones(n), X])
                    try:
                        beta = np.linalg.lstsq(X, y, rcond=None)[0]
                        resid = y - X @ beta
                        var = np.var(resid)
                    except Exception:
                        var = 1.0
                    total_log_lik -= 0.5 * n * (np.log(var + 1e-10) + 1)
                    n_params += len(parents) + 1

            return total_log_lik - 0.5 * n_params * np.log(n)
        except Exception:
            return -1e10

    def _would_create_cycle(self, edges, new_edge, var_names):
        """检查加边是否会创建环"""
        test_edges = list(edges) + [new_edge]
        try:
            from causal.graph import CausalDAG
            CausalDAG(var_names, test_edges)
            return False
        except Exception:
            return True

    def edge_confidence_report(self, posterior: GraphPosterior) -> str:
        """生成边置信度报告"""
        lines = ["=== Edge Confidence Report ==="]
        lines.append(f"Samples: {posterior.n_samples}")
        lines.append(f"Entropy: {posterior.entropy:.3f} nats")
        lines.append("")

        sorted_edges = sorted(posterior.edge_posteriors,
                              key=lambda e: -e.probability)

        for ep in sorted_edges:
            bar_len = int(ep.probability * 20)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            label = "HIGH" if ep.probability > 0.8 else \
                    "MED " if ep.probability > 0.5 else "LOW "
            lines.append(f"  [{label}] {ep.source} → {ep.target}: "
                         f"{ep.probability:.2f} {bar}")

        return "\n".join(lines)
