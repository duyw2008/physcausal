"""
骨架匹配器 — 无物理先验时的 fallback

给定数据和变量名，在骨架库中找到最相似的已知骨架，
将其因果结构迁移为当前场景的先验边。
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np

from creative.skeleton_library import SkeletonLibrary


class SkeletonMatcher:
    """骨架匹配器: 数据 + 变量名 → 最相似骨架的因果边"""

    def __init__(self):
        self.skeleton_lib = SkeletonLibrary()

    @staticmethod
    def _skeleton_topology(skeleton) -> Tuple[int, int, int]:
        """解析骨架的拓扑: (n_inputs, n_hidden, n_outputs)"""
        edges = skeleton.edges if hasattr(skeleton, 'edges') else []
        
        # 找出所有输入节点 (只作为src, 不作为dst)
        all_srcs = set(e[0] for e in edges)
        all_dsts = set(e[1] for e in edges)
        inputs = all_srcs - all_dsts
        outputs = all_dsts - all_srcs
        all_nodes = all_srcs | all_dsts
        hidden = all_nodes - inputs - outputs
        
        return len(inputs), len(hidden), len(outputs)

    def match(self, data: np.ndarray, var_names: List[str]) -> List[Tuple[str, str]]:
        """
        返回最匹配骨架的因果边 (用当前变量名重新标注)。
        """
        n_vars = len(var_names)
        if n_vars < 2:
            return []

        corr = np.abs(np.corrcoef(data.T))
        
        best_score = -np.inf
        best_skeleton = None
        best_mapping = None

        for name, skeleton in self.skeleton_lib.skeletons.items():
            n_in, n_hid, n_out = self._skeleton_topology(skeleton)
            if n_in + n_hid + n_out != n_vars:
                continue
            
            # 基于方差分配: 输出节点方差最大 (组合了所有输入)
            variance = np.var(data, axis=0)
            ranked = np.argsort(variance)  # 升序: 低方差→输入, 高方差→输出
            
            mapping = {}
            idx = 0
            for i in range(n_in):
                mapping[f"in_{i}"] = int(ranked[idx]); idx += 1
            for i in range(n_hid):
                mapping[f"hid_{i}"] = int(ranked[idx]); idx += 1
            for i in range(n_out):
                mapping[f"out_{i}"] = int(ranked[idx]); idx += 1
            
            # 分数: 输入→输出的平均相关
            in_idx = [mapping[f"in_{i}"] for i in range(n_in)]
            out_idx = [mapping[f"out_{i}"] for i in range(n_out)]
            
            score = 0.0
            count = 0
            for si in in_idx:
                for di in out_idx:
                    score += corr[si, di]
                    count += 1
            score = score / max(count, 1)
            
            if score > best_score:
                best_score = score
                best_skeleton = skeleton
                best_mapping = mapping

        if best_skeleton is None or best_score < 0.3:
            return []

        # 生成边: 从骨架边模板重标注
        edges = []
        skeleton_edges = best_skeleton.edges if hasattr(best_skeleton, 'edges') else []
        
        # 建立节点名→变量索引的映射
        # 骨架节点名: 推断输入/隐藏/输出的名字
        node_to_idx = {}
        for k, v in best_mapping.items():
            node_to_idx[k] = v
        
        # 按骨架边的拓扑生成匹配边
        n_in = len([k for k in best_mapping if k.startswith("in_")])
        n_hid = len([k for k in best_mapping if k.startswith("hid_")])
        
        # 简化: 如果骨架是输入→输出 (无隐藏), 生成全连接
        if n_hid == 0:
            for si in [best_mapping[f"in_{i}"] for i in range(n_in)]:
                for di in [best_mapping[f"out_{i}"] for i in range(len(best_mapping) - n_in)]:
                    if si != di:
                        edges.append((var_names[si], var_names[di]))
        else:
            # 有隐藏: 输入→隐藏, 隐藏→输出
            for si in [best_mapping[f"in_{i}"] for i in range(n_in)]:
                for hi in [best_mapping[f"hid_{i}"] for i in range(n_hid)]:
                    edges.append((var_names[si], var_names[hi]))
            for hi in [best_mapping[f"hid_{i}"] for i in range(n_hid)]:
                for di in [best_mapping[f"out_{i}"] for i in range(len(best_mapping) - n_in - n_hid)]:
                    edges.append((var_names[hi], var_names[di]))

        return edges


# 全局单例
matcher = SkeletonMatcher()
