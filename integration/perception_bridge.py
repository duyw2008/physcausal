"""
感知→因果桥接 — 从原始感知数据到因果变量

数据流:
  原始数据 (CSV/array/dict)
    → 感知层: SimpleFeatureExtractor → Scene → 变量字典
    → 谱分解: PCA → 降维 + 重要性排序
    → 变量选择: 保留有效秩内的变量
    → 因果层: 输出 causal variables + DataFrame
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np

from perception.encoder import SimpleFeatureExtractor, PerceptualEncoder, Scene, ObjectSlot
from spectral.spectral import SpectralDecomposer


class PerceptionToCausal:
    """
    感知→因果桥接器。

    将原始感知数据转化为因果发现所需的:
      - variable_names: 经谱分解筛选后的变量名
      - data_matrix:   降维后的数据矩阵

    流程:
      1. 感知编码: raw → Scene → 变量字典
      2. 谱分解:   PCA 降维 + 重要性排序
      3. 变量选择: 保留有效秩 (95% 方差) 内的变量
    """

    def __init__(self,
                 encoder: Optional[PerceptualEncoder] = None,
                 variance_threshold: float = 0.95,
                 max_variables: Optional[int] = None):
        self.encoder = encoder or SimpleFeatureExtractor()
        self.decomposer = SpectralDecomposer(variance_threshold=variance_threshold)
        self.max_variables = max_variables
        self.variance_threshold = variance_threshold

    def process(self,
                raw_data: np.ndarray,
                variable_names: Optional[List[str]] = None,
                verbose: bool = False) -> Dict:
        """
        完整处理流程: 感知 → 谱分解 → 因果变量。

        Args:
            raw_data: (n_samples × n_features) 数据矩阵
            variable_names: 变量名列表 (可选, 自动生成)
            verbose: 是否打印详细信息

        Returns:
            {
                "variable_names": [...]      # 筛选后的变量名
                "data": np.ndarray,          # 降维后的数据
                "importance": {...},         # 每个变量的重要性
                "n_original": int,           # 原始变量数
                "n_selected": int,           # 选择后的变量数
                "explained_variance": float, # 保留的方差比例
                "scene": Scene,              # 感知层输出
            }
        """
        if variable_names is None:
            variable_names = [f"V{i}" for i in range(raw_data.shape[1])]

        encoder = SimpleFeatureExtractor(
            variable_names=variable_names
        )
        scene = encoder.encode(raw_data[0]) if raw_data.shape[0] > 0 else Scene()

        # 谱分解
        eigen_result = self.decomposer.pca(raw_data)

        # 变量重要性排序
        importance = self.decomposer.importance_ranking(raw_data, variable_names)
        importance_dict = {name: score for name, score in importance}

        # 变量选择
        n_select = eigen_result.effective_rank
        if self.max_variables and n_select > self.max_variables:
            n_select = self.max_variables

        selected_names = [name for name, _ in importance[:n_select]]
        selected_indices = [variable_names.index(n) for n in selected_names]
        selected_data = raw_data[:, selected_indices]

        if verbose:
            print(f"Perception → Causal Bridge:")
            print(f"  Original: {len(variable_names)} variables")
            print(f"  Selected: {len(selected_names)} variables "
                  f"({eigen_result.cumulative_variance[n_select-1]:.1%} variance)")
            print(f"  Top variables: {', '.join(selected_names[:5])}")

        return {
            "variable_names": selected_names,
            "data": selected_data,
            "importance": importance_dict,
            "n_original": len(variable_names),
            "n_selected": len(selected_names),
            "explained_variance": float(
                eigen_result.cumulative_variance[min(n_select-1, len(eigen_result.cumulative_variance)-1)]
            ),
            "scene": scene,
        }

    def process_with_objects(self,
                              raw_data: np.ndarray,
                              object_groups: Dict[str, List[str]],
                              verbose: bool = False) -> Dict:
        """
        带对象分组感知的处理流程。

        Args:
            raw_data: 数据矩阵
            object_groups: {对象ID: [变量名列表]}

        在谱分解后，额外计算对象级别的重要性。
        """
        result = self.process(raw_data, verbose=verbose)

        # 对象级别重要性
        obj_importance = {}
        for obj_id, var_names in object_groups.items():
            score = sum(result["importance"].get(vn, 0.0) for vn in var_names)
            obj_importance[obj_id] = score

        result["object_importance"] = obj_importance
        return result


class VariableSelector:
    """
    因果变量选择器 — 从高维感知特征中选出值得进入因果图的变量。

    选择策略 (可组合):
      1. spectral:     PCA 特征值排序 → 保留 top-k
      2. variance:     方差阈值过滤
      3. correlation:  移除高度相关的重复变量
    """

    def __init__(self, method: str = "spectral",
                 variance_threshold: float = 0.95,
                 correlation_threshold: float = 0.95,
                 max_variables: int = 20):
        self.method = method
        self.variance_threshold = variance_threshold
        self.correlation_threshold = correlation_threshold
        self.max_variables = max_variables
        self.decomposer = SpectralDecomposer(variance_threshold=variance_threshold)

    def select(self,
               data: np.ndarray,
               variable_names: List[str]) -> Tuple[List[str], np.ndarray]:
        """
        选择变量。

        Returns:
          (selected_names, selected_data)
        """
        if self.method == "spectral":
            return self._spectral_select(data, variable_names)
        elif self.method == "variance":
            return self._variance_select(data, variable_names)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _spectral_select(self, data, names):
        result = self.decomposer.pca(data)
        importance = self.decomposer.importance_ranking(data, names)
        n = min(result.effective_rank, self.max_variables)
        selected = [n for n, _ in importance[:n]]
        indices = [names.index(s) for s in selected]
        return selected, data[:, indices]

    def _variance_select(self, data, names):
        variances = np.var(data, axis=0)
        threshold = np.percentile(variances, (1 - self.variance_threshold) * 100)
        mask = variances >= threshold
        selected = [n for i, n in enumerate(names) if mask[i]]
        return selected, data[:, mask]
