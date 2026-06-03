"""
因果模块库 — 可复用的因果结构模板

进化式联想的前提:
  没有素材库, 随机变异无从谈起。
  好的模块库 = 结构化 + 类型签名 + 物理标注。

模块格式:
  {
    "name": "simple_pendulum",
    "domain": "mechanics",
    "variables": {"L": "length", "g": "gravity", "T": "period"},
    "edges": [("L", "T"), ("g", "T")],
    "type_signatures": {"L": "spatial", "g": "acceleration", "T": "temporal"},
    "physics_law": "T = 2π√(L/g)",
    "invariants": ["energy_conservation"]
  }
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import numpy as np


@dataclass
class CausalModule:
    """一个可复用的因果结构单元"""
    name: str
    domain: str                        # mechanics / electromagnetism / ...
    variables: Dict[str, str]          # {var_id: description}
    edges: List[Tuple[str, str]]       # causal edges
    type_signatures: Dict[str, str]    # {var_id: type} — 接口类型
    physics_law: str = ""              # 支配此模块的物理定律 (如果有)
    invariants: List[str] = field(default_factory=list)
    # 例: ["energy_conservation", "momentum_conservation"]


class ModuleLibrary:
    """因果模块库"""

    def __init__(self):
        self.modules: Dict[str, CausalModule] = {}
        self._init_default_library()

    def register(self, module: CausalModule):
        self.modules[module.name] = module

    def get(self, name: str) -> Optional[CausalModule]:
        return self.modules.get(name)

    def list_by_domain(self, domain: str) -> List[CausalModule]:
        return [m for m in self.modules.values() if m.domain == domain]

    def list_all(self) -> List[CausalModule]:
        return list(self.modules.values())

    def compatible_pairs(self) -> List[Tuple[CausalModule, CausalModule, List[str]]]:
        """
        找类型兼容的模块对。

        兼容 = 共享至少一个相同类型的变量。
        共享变量 = 两个模块可以对接的接口。
        """
        pairs = []
        modules = list(self.modules.values())

        for i in range(len(modules)):
            for j in range(i + 1, len(modules)):
                a, b = modules[i], modules[j]
                shared_types = set(a.type_signatures.values()) & set(b.type_signatures.values())
                if shared_types:
                    pairs.append((a, b, list(shared_types)))
        return pairs

    def _init_default_library(self):
        # ── 力学 ──
        self.register(CausalModule(
            name="newton_second",
            domain="mechanics",
            variables={"F": "force", "m": "mass", "a": "acceleration"},
            edges=[("F", "a"), ("m", "a")],
            type_signatures={"F": "force", "m": "scalar", "a": "acceleration"},
            physics_law="F = ma",
            invariants=["momentum_conservation"],
        ))

        self.register(CausalModule(
            name="simple_pendulum",
            domain="mechanics",
            variables={"L": "length", "g": "gravity", "T": "period"},
            edges=[("L", "T"), ("g", "T")],
            type_signatures={"L": "spatial", "g": "acceleration", "T": "temporal"},
            physics_law="T = 2π√(L/g)",
            invariants=["energy_conservation"],
        ))

        self.register(CausalModule(
            name="hooke_spring",
            domain="mechanics",
            variables={"x": "displacement", "k": "stiffness", "F": "restoring_force"},
            edges=[("x", "F"), ("k", "F")],
            type_signatures={"x": "spatial", "k": "scalar", "F": "force"},
            physics_law="F = -kx",
            invariants=["energy_conservation"],
        ))

        self.register(CausalModule(
            name="kinetic_energy",
            domain="mechanics",
            variables={"m": "mass", "v": "velocity", "E_k": "kinetic_energy"},
            edges=[("m", "E_k"), ("v", "E_k")],
            type_signatures={"m": "scalar", "v": "velocity", "E_k": "energy"},
            physics_law="E_k = ½mv²",
        ))

        self.register(CausalModule(
            name="collision_conservation",
            domain="mechanics",
            variables={"m1": "mass", "v1": "velocity", "m2": "mass",
                       "v2": "velocity", "v1'": "velocity", "v2'": "velocity"},
            edges=[("v1", "v1'"), ("v2", "v1'"), ("v1", "v2'"), ("v2", "v2'")],
            type_signatures={"m1": "scalar", "v1": "velocity", "m2": "scalar",
                             "v2": "velocity", "v1'": "velocity", "v2'": "velocity"},
            physics_law="m1v1 + m2v2 = m1v1' + m2v2'",
            invariants=["momentum_conservation", "energy_conservation"],
        ))

        # ── 电磁学 ──
        self.register(CausalModule(
            name="ohm_law",
            domain="electromagnetism",
            variables={"V": "voltage", "I": "current", "R": "resistance"},
            edges=[("V", "I"), ("R", "I")],
            type_signatures={"V": "voltage", "I": "current", "R": "scalar"},
            physics_law="V = IR",
        ))

        self.register(CausalModule(
            name="joule_heating",
            domain="electromagnetism",
            variables={"I": "current", "R": "resistance", "P": "power"},
            edges=[("I", "P"), ("R", "P")],
            type_signatures={"I": "current", "R": "scalar", "P": "power"},
            physics_law="P = I²R",
        ))

        # ── 热力学 ──
        self.register(CausalModule(
            name="ideal_gas",
            domain="thermodynamics",
            variables={"P": "pressure", "V": "volume", "T": "temperature", "n": "amount"},
            edges=[("n", "P"), ("T", "P"), ("V", "P")],
            type_signatures={"P": "pressure", "V": "spatial", "T": "temperature", "n": "scalar"},
            physics_law="PV = nRT",
        ))

        self.register(CausalModule(
            name="thermal_expansion",
            domain="thermodynamics",
            variables={"T": "temperature", "L": "length", "α": "coefficient"},
            edges=[("T", "L"), ("α", "L")],
            type_signatures={"T": "temperature", "L": "spatial", "α": "scalar"},
            physics_law="ΔL = αL₀ΔT",
        ))

        # ── 流体 ──
        self.register(CausalModule(
            name="bernoulli",
            domain="fluids",
            variables={"P": "pressure", "v": "velocity", "h": "height", "ρ": "density"},
            edges=[("v", "P"), ("h", "P"), ("ρ", "P")],
            type_signatures={"P": "pressure", "v": "velocity", "h": "spatial", "ρ": "scalar"},
            physics_law="P + ½ρv² + ρgh = const",
            invariants=["energy_conservation"],
        ))

        # ── 回归 (无物理约束的模板) ──
        self.register(CausalModule(
            name="confounder_template",
            domain="abstract",
            variables={"Z": "confounder", "X": "treatment", "Y": "outcome"},
            edges=[("Z", "X"), ("Z", "Y"), ("X", "Y")],
            type_signatures={"Z": "scalar", "X": "scalar", "Y": "scalar"},
            physics_law="",
        ))

        self.register(CausalModule(
            name="mediator_template",
            domain="abstract",
            variables={"X": "cause", "M": "mediator", "Y": "effect"},
            edges=[("X", "M"), ("M", "Y"), ("X", "Y")],
            type_signatures={"X": "scalar", "M": "scalar", "Y": "scalar"},
            physics_law="",
        ))

        self.register(CausalModule(
            name="collider_template",
            domain="abstract",
            variables={"X": "cause1", "Y": "cause2", "Z": "collider"},
            edges=[("X", "Z"), ("Y", "Z")],
            type_signatures={"X": "scalar", "Y": "scalar", "Z": "scalar"},
            physics_law="",
        ))

    def stats(self) -> Dict:
        domains = {}
        for m in self.modules.values():
            domains[m.domain] = domains.get(m.domain, 0) + 1
        return {
            "total_modules": len(self.modules),
            "domains": domains,
            "compatible_pairs": len(self.compatible_pairs()),
        }
