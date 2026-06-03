"""
因果骨架库 — 跨领域的不变结构

核心洞察:
  不同领域的底层规律共享相同的因果拓扑骨架。
  骨架 = 纯结构，不含变量语义。
  发现新领域规律 = 找到已知骨架在该领域的外延。

骨架示例:
  Chain (链):        X → M → Y         (中介, 热传导, 信号传播)
  Fork (叉):         X ← Z → Y         (混淆, 共同原因)
  Collider (对撞):   X → Z ← Y         (选择偏差, 量子对撞)
  Feedback (反馈):   X → Y → X         (恒温器, RC电路, 生态)
  ThreeBody (三体):  三个变量共享守恒量  (动量守恒, Kirchhoff)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class CausalSkeleton:
    """
    因果骨架 — 跨领域的不变结构。

    不含具体变量名，只有拓扑结构 + 类型约束。
    例: Chain(nodes=3, edges=[(0,1),(1,2)]) 可以外显为:
      - 力学: Force → Acceleration → Position
      - 电磁: Voltage → Current → Power
      - 热学: Temperature → HeatFlow → Expansion
    """
    name: str
    description: str
    n_nodes: int
    edges: List[Tuple[int, int]]          # 节点索引 (0-based)
    type_constraints: Dict[int, str]      # {node_idx: required_type}
    # 例: {0: "force", 1: "acceleration"}
    # "" = 无类型约束 (任意变量都可以)
    physics_invariants: List[str] = field(default_factory=list)
    # 例: ["energy_conservation"]
    real_world_examples: List[str] = field(default_factory=list)
    # 例: ["F=ma", "V=IR", "Heat conduction"]


class SkeletonLibrary:
    """因果骨架库"""

    def __init__(self):
        self.skeletons: Dict[str, CausalSkeleton] = {}
        self._init_skeletons()

    def _init_skeletons(self):
        # ── 基础三元骨架 ──

        self.register(CausalSkeleton(
            name="chain",
            description="线性因果链: 原因→中介→结果",
            n_nodes=3, edges=[(0, 1), (1, 2)],
            type_constraints={},
            real_world_examples=[
                "Force → Acceleration → Position",
                "Voltage → Current → Power",
                "Temperature → Expansion → Stress",
            ],
        ))

        self.register(CausalSkeleton(
            name="fork",
            description="共同原因 (混淆): 一个原因同时影响两个结果",
            n_nodes=3, edges=[(2, 0), (2, 1)],
            type_constraints={},
            real_world_examples=[
                "SES → Education, SES → Income",
                "Temperature → IceCream, Temperature → Drowning",
            ],
        ))

        self.register(CausalSkeleton(
            name="collider",
            description="对撞结构: 两个原因汇聚到一个结果",
            n_nodes=3, edges=[(0, 2), (1, 2)],
            type_constraints={},
            real_world_examples=[
                "Talent → Success ← Luck",
                "Mutation → Cancer ← Environment",
            ],
        ))

        # ── 物理骨架 ──

        self.register(CausalSkeleton(
            name="proportional_response",
            description="比例响应: 多个因子按权重贡献到一个结果",
            n_nodes=4, edges=[(0, 3), (1, 3), (2, 3)],
            type_constraints={3: "response"},
            physics_invariants=["superposition"],
            real_world_examples=[
                "F=ma (Force+Mass→Acceleration)",
                "V=IR (Voltage+Resistance→Current)",
                "PV=nRT (n+T+V→Pressure)",
            ],
        ))

        self.register(CausalSkeleton(
            name="harmonic_oscillation",
            description="谐振: 恢复力与位移成正比, 导致周期运动",
            n_nodes=3, edges=[(0, 1), (1, 2), (2, 0)],
            type_constraints={0: "displacement", 1: "force", 2: "acceleration"},
            physics_invariants=["energy_conservation"],
            real_world_examples=[
                "Spring: x→F, F→a, a→x",
                "LC Circuit: Q→V, V→I, I→Q",
                "Population: Prey→Predator→Prey",
            ],
        ))

        self.register(CausalSkeleton(
            name="conservation_constraint",
            description="守恒约束: 多个量之和保持不变",
            n_nodes=4,
            edges=[(0, 1), (1, 3), (2, 3)],
            type_constraints={3: "conserved_quantity"},
            physics_invariants=["conservation"],
            real_world_examples=[
                "m1v1 + m2v2 = m1v1' + m2v2' (动量守恒)",
                "I_in = I_out (Kirchhoff 电流定律)",
                "Mass_in = Mass_out (质量守恒)",
            ],
        ))

        # ── 反馈骨架 ──

        self.register(CausalSkeleton(
            name="negative_feedback",
            description="负反馈: 输出抑制输入，趋向稳态",
            n_nodes=3,
            edges=[(0, 1), (1, 2), (2, 0)],
            type_constraints={2: "inhibitor"},
            real_world_examples=[
                "Thermostat: Temp→Heater→Heat→Temp (负)",
                "Population: Prey→Food→Prey (负密度依赖)",
            ],
        ))

        self.register(CausalSkeleton(
            name="positive_feedback",
            description="正反馈: 输出增强输入，指数增长",
            n_nodes=3,
            edges=[(0, 1), (1, 2), (2, 0)],
            type_constraints={2: "activator"},
            real_world_examples=[
                "Compound Interest: Money→Interest→Money",
                "Nuclear Chain Reaction: Neutron→Fission→Neutron",
                "Microphone Feedback: Sound→Amp→Sound",
            ],
        ))

        # ── 信息骨架 ──

        self.register(CausalSkeleton(
            name="information_bottleneck",
            description="信息瓶颈: 感知→压缩→推理",
            n_nodes=4,
            edges=[(0, 1), (1, 2), (2, 3)],
            type_constraints={0: "high_dim", 2: "low_dim", 3: "prediction"},
            real_world_examples=[
                "Pixel → PCA → DAG → ATE",
                "Raw Data → Encoder → Latent → Decoder",
            ],
        ))

    def register(self, skeleton: CausalSkeleton):
        self.skeletons[skeleton.name] = skeleton

    def get(self, name: str) -> Optional[CausalSkeleton]:
        return self.skeletons.get(name)

    def list_all(self) -> List[CausalSkeleton]:
        return list(self.skeletons.values())

    def find_by_topology(self, n_nodes: int,
                         n_edges: int) -> List[CausalSkeleton]:
        """按节点数和边数搜索骨架"""
        return [
            s for s in self.skeletons.values()
            if s.n_nodes == n_nodes and len(s.edges) == n_edges
        ]

    def find_by_invariant(self, invariant: str) -> List[CausalSkeleton]:
        """按物理不变量搜索骨架"""
        return [
            s for s in self.skeletons.values()
            if invariant in s.physics_invariants
        ]

    def instantiate(self, skeleton_name: str,
                    variable_names: List[str],
                    domain: str = "") -> Dict:
        """
        将骨架实例化为具体领域的因果模块。

        skeleton_name "chain" + variable_names ["V","I","P"]
        → {edges: [("V","I"), ("I","P")], domain: "electromagnetism"}
        """
        sk = self.skeletons.get(skeleton_name)
        if not sk:
            raise ValueError(f"Unknown skeleton: {skeleton_name}")

        if len(variable_names) != sk.n_nodes:
            raise ValueError(
                f"Skeleton {skeleton_name} needs {sk.n_nodes} vars, "
                f"got {len(variable_names)}"
            )

        edges = []
        for src_idx, dst_idx in sk.edges:
            edges.append((variable_names[src_idx], variable_names[dst_idx]))

        return {
            "name": f"{skeleton_name}_{domain}" if domain else skeleton_name,
            "skeleton": skeleton_name,
            "domain": domain,
            "variables": variable_names,
            "edges": edges,
            "invariants": sk.physics_invariants,
        }

    def cross_domain_analogies(self) -> List[Dict]:
        """
        发现跨域类比。

        对每个骨架，列出它在不同领域的外显。
        这些就是「联想」的原材料。
        """
        analogies = []
        for sk in self.skeletons.values():
            if sk.real_world_examples:
                analogies.append({
                    "skeleton": sk.name,
                    "description": sk.description,
                    "examples": sk.real_world_examples,
                    "invariants": sk.physics_invariants,
                })
        return analogies

    def suggest_skeleton(self,
                         edges: List[Tuple[str, str]],
                         n_variables: int) -> Optional[str]:
        """
        给定一个因果图，匹配最接近的骨架。

        用于「识别这个图的抽象结构是什么」。
        """
        n_edges = len(edges)
        candidates = self.find_by_topology(n_variables, n_edges)

        if not candidates:
            return None

        # 找拓扑最接近的 (当前用最简单的: 边数 + 节点数匹配)
        return candidates[0].name
