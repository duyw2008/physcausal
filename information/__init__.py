"""
信息层 (Information) — 横切数学基础设施

与 spectral/ 平级，提供所有层都能用的信息度量工具。

模块:
  shannon.py     — Shannon 熵 / 互信息 / KL / JS / 传递熵
  bottleneck.py  — 信息瓶颈 (感知压缩的理论基础)
  jaynes.py      — 最大熵原理 (连接概率与物理)

核心张力: 熵增 vs 熵减

  世界 (不可控):     ΔS ≥ 0     熵永远在增加 — 这是 Tier 1 的铁律，不是目标
  智能体 (可控):     降低局部熵   压缩 = 理解     — 这是智能体存在的意义

  每一层的熵流:
    感知层     ↘ 熵减   像素(H高) → 语义变量(H低)
    谱分解     ↘ 熵减   PCA 筛掉低方差维度
    信息瓶颈   ↘ 熵减   minimize I(T;X) — 丢掉冗余、保留相关
    因果发现   ↘ 熵减   稠密关联图 → 稀疏 DAG
    SCM 拟合   ↘ 熵减   n 数据点 → n_params 参数
    ────────────────────────────────────────────
    元物理约束  ↗ 熵增   宇宙收的「税」— Landauer 极限: 1 bit ≥ kT ln 2

  智能体 = 局域熵减机器 — 用能量和信息为代价，把噪声提炼为结构。
  净效果: ΔS_宇宙 > 0 (永远满足第二定律) — 智能体减少的熵 < 环境增加的熵。
"""

from information.shannon import ShannonEntropy, BoltzmannBridge
from information.bottleneck import InformationBottleneck, CompressionReport
from information.jaynes import MaxEnt

__all__ = [
    "ShannonEntropy", "BoltzmannBridge",
    "InformationBottleneck", "CompressionReport",
    "MaxEnt",
]
