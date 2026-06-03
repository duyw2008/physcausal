"""
三层过滤 — 物理→BIC→新颖性

随机变异产生候选 → 过滤决定谁是幸存者
过滤是进化式联想中「自然选择」的角色

Tier 0 (硬杀):  物理定律 + 守恒律 + 局域因果 + 拓扑约束
Tier 1 (评分):  BIC 得分 + 简洁性 (Occam)
Tier 2 (筛选):  新颖性 — 太像已知结构的丢弃 (不创新)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


class CausalFilter:
    """
    因果假说过滤器。

    三层过滤:
      Tier 0: 物理硬约束 (violation → 立即丢弃)
      Tier 1: 统计评分 (BIC + 简洁性)
      Tier 2: 新颖性筛选 (与已知库的相似度)
    """

    def __init__(self):
        pass

    def tier0_physics(self,
                      edges: List[Tuple[str, str]],
                      variable_names: List[str],
                      forbidden_edges: Optional[List[Tuple[str, str]]] = None,
                      required_edges: Optional[List[Tuple[str, str]]] = None,
                      ) -> Tuple[bool, str]:
        """
        Tier 0: 物理硬约束。

        违反任何一条 → 直接丢弃。

        Returns:
          (passes, reason_if_failed)
        """
        edge_set = set(edges)

        # 必须包含的边
        if required_edges:
            for e in required_edges:
                if e not in edge_set:
                    return False, f"Missing required edge: {e[0]}→{e[1]}"

        # 禁止的边
        if forbidden_edges:
            for e in forbidden_edges:
                if e in edge_set:
                    return False, f"Forbidden edge present: {e[0]}→{e[1]}"

        # 因果方向约束: 检查是否有时间反向边
        # (简化: 用拓扑序存在性作为代理)
        try:
            from causal.graph import CausalDAG
            CausalDAG(variable_names, edges)
        except Exception as e:
            return False, f"Not a valid DAG: {str(e)}"

        # 局域因果 (如果有时间标签)
        # (当前简化: 只验证 DAG 有效性)

        # 守恒律 (如果有指定的守恒变量)
        # (当前简化: 必须显式指定才检查)

        return True, ""

    def tier1_bic(self,
                  edges: List[Tuple[str, str]],
                  variable_names: List[str],
                  data: np.ndarray,
                  lambda_sparsity: float = 1.0) -> float:
        """
        Tier 1: BIC 得分。

        得分越高越好。
        BIC = log P(D|G) - (k/2) log n
        简洁性: 额外惩罚边数。
        """
        from bayesian.structural import StructuralPosterior

        sp = StructuralPosterior(method="bootstrap")
        bic = sp._bic_score(data, variable_names, edges)

        # 额外的稀疏性惩罚
        n_edges = len(edges)
        n_vars = len(variable_names)
        max_edges = n_vars * (n_vars - 1) / 2
        sparsity_bonus = -lambda_sparsity * n_edges / max(max_edges, 1)

        return bic + sparsity_bonus

    def tier2_novelty(self,
                      edges: List[Tuple[str, str]],
                      variable_names: List[str],
                      known_modules: List,
                      novelty_threshold: float = 0.3) -> Tuple[bool, float]:
        """
        Tier 2: 新颖性筛选。

        与已知模块库比较:
          太相似 (同构) → 已知结构, 不创新 → 丢弃
          不太相似但物理可行 → 候选新发现 → 通过

        Returns:
          (is_novel, similarity_score)
          0.0 = 完全已知, 1.0 = 完全新颖
        """
        if not known_modules:
            return True, 1.0

        n_edges = len(edges)
        if n_edges == 0:
            return True, 1.0

        min_similarity = 1.0

        for module in known_modules:
            if not hasattr(module, 'edges'):
                continue

            known_edges = set(module.edges)
            target_edges = set(edges)

            intersection = len(known_edges & target_edges)
            union = len(known_edges | target_edges)

            if union == 0:
                similarity = 0.0
            else:
                similarity = intersection / union

            min_similarity = min(min_similarity, similarity)

        novelty = 1.0 - min_similarity
        is_novel = novelty >= novelty_threshold

        return is_novel, novelty

    def full_filter(self,
                    edges: List[Tuple[str, str]],
                    variable_names: List[str],
                    data: np.ndarray,
                    known_modules: Optional[List] = None,
                    forbidden_edges: Optional[List] = None,
                    required_edges: Optional[List] = None,
                    novelty_threshold: float = 0.3,
                    lambda_sparsity: float = 1.0,
                    ) -> Dict:
        """
        完整三层过滤。

        Returns:
          {
            "passed": True/False,
            "tier0_pass": bool,
            "tier1_score": float,
            "tier2_novel": bool,
            "tier2_score": float,
            "reason": str (如果失败),
          }
        """
        # Tier 0
        t0_ok, t0_reason = self.tier0_physics(
            edges, variable_names, forbidden_edges, required_edges
        )
        if not t0_ok:
            return {
                "passed": False, "tier": 0,
                "tier0_pass": False, "reason": t0_reason,
            }

        # Tier 1
        bic = self.tier1_bic(edges, variable_names, data, lambda_sparsity)

        # Tier 2
        t2_novel, t2_score = self.tier2_novelty(
            edges, variable_names, known_modules, novelty_threshold
        )

        return {
            "passed": True,
            "tier0_pass": True,
            "tier1_score": bic,
            "tier2_novel": t2_novel,
            "tier2_score": t2_score,
            "reason": "",
        }
