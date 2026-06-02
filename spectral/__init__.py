"""
特征谱层 (Spectral) — 元物理原则的数学语言（横切基础设施）

本征向量 = 信息空间的骨架方向
本征值   = 每个方向上的重要性

这是元物理层和上层之间的横向桥梁。
所有元物理原则最终都通过特征分解来表达和计算。

模块:
  spectral.py — SpectralDecomposer (PCA/SVD/谱图) + KoopmanSpectral + ObservableMeasurement
"""

from spectral.spectral import (
    EigenResult,
    SpectralGraph,
    SpectralDecomposer,
    ObservableMeasurement,
    KoopmanSpectral,
)

__all__ = [
    "EigenResult", "SpectralGraph", "SpectralDecomposer",
    "ObservableMeasurement", "KoopmanSpectral",
]
