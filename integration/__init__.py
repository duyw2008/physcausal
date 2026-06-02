"""
桥接层 — 连接四层架构的横向管道

perception_bridge:  感知 → 谱分解 → 因果变量
physics_bridge:     物理约束 → 因果图
pipeline:           端到端四层流水线
"""

from integration.perception_bridge import PerceptionToCausal, VariableSelector
from integration.physics_bridge import PhysicsToCausal
from integration.pipeline import PhysCausalPipeline

__all__ = [
    "PerceptionToCausal", "VariableSelector",
    "PhysicsToCausal",
    "PhysCausalPipeline",
]
