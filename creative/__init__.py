"""
创造性联想层 (Creative) — 进化式结构发现

不是均匀随机试错 — 是在结构相容的空间中做加权变异 + 确定性过滤。

核心模块:
  module_library.py    — 可复用因果模块库 (14个预置模块)
  skeleton_library.py  — 跨领域因果骨架库 (8个预置骨架)
  mutation.py          — 结构变异算子 (加权采样, 偏向有意义的邻域)
  filter.py            — 三层过滤 (Tier0:物理 → Tier1:BIC → Tier2:新颖性)
  evolution.py         — 进化主循环 (生成→过滤→保留→重复)

核心理念:
  不同领域的底层规律共享相同的因果拓扑骨架。
  创造性联想 = 提取骨架 → 跨域实例化 → 过滤验证。
  骨架是「灵感」的数学形式。
"""

from creative.module_library import CausalModule, ModuleLibrary
from creative.skeleton_library import CausalSkeleton, SkeletonLibrary
from creative.mutation import CausalMutator
from creative.filter import CausalFilter
from creative.evolution import CreativeEvolution

__all__ = [
    "CausalModule", "ModuleLibrary",
    "CausalSkeleton", "SkeletonLibrary",
    "CausalMutator",
    "CausalFilter",
    "CreativeEvolution",
]
