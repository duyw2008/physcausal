"""
组合泛化 — 模块接口 + 类型系统 + 自动对接

核心理念:
  每个因果模块拥有类型化的输入/输出端口。
  两个模块类型兼容 → 自动对接 (共享变量) → 新模块。
  组合后可以再做组合 — 无限生长。

范畴论视角:
  模块 = 对象之间的态射
  接口 = 对象的类型标注
  组合 = 态射的复合
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import numpy as np


@dataclass
class TypedPort:
    """类型化端口 — 模块的输入或输出"""
    name: str                  # 变量名
    port_type: str             # 类型: "force", "velocity", "scalar", ...
    direction: str             # "input" or "output"
    description: str = ""


@dataclass
class ModuleInterface:
    """
    模块接口 — 输入/输出端口 + 内部因果图。

    例: Newton II 模块
      inputs:  [force:force, mass:scalar]
      outputs: [acceleration:acceleration]
      internal_edges: [(force, acceleration), (mass, acceleration)]
    """
    name: str
    domain: str
    inputs: List[TypedPort]
    outputs: List[TypedPort]
    internal_edges: List[Tuple[str, str]]
    physics_law: str = ""

    def all_variables(self) -> List[str]:
        return [p.name for p in self.inputs + self.outputs]

    def all_ports(self) -> List[TypedPort]:
        return self.inputs + self.outputs

    def get_port(self, name: str) -> Optional[TypedPort]:
        for p in self.all_ports():
            if p.name == name:
                return p
        return None

    def input_types(self) -> Dict[str, str]:
        return {p.name: p.port_type for p in self.inputs}

    def output_types(self) -> Dict[str, str]:
        return {p.name: p.port_type for p in self.outputs}

    def can_connect_to(self, other: "ModuleInterface") -> List[Tuple[str, str]]:
        """
        检查两个模块可以如何对接。

        对接条件: 模块A的某个输出端口类型 == 模块B的某个输入端口类型
        对接方式: 共享该变量 (两个模块通过它连接)

        Returns:
          [(output_var_A, input_var_B), ...] 候选对接点
        """
        connections = []
        for out in self.outputs:
            for inp in other.inputs:
                if out.port_type == inp.port_type:
                    connections.append((out.name, inp.name))
        return connections

    def compose(self, other: "ModuleInterface",
                connections: List[Tuple[str, str]]) -> "ModuleInterface":
        """
        组合两个模块。

        connections = [(output_A, input_B), ...]
        共享变量被合并，两个模块的边被合并。
        """
        # 收集所有变量 (共享变量去重)
        all_vars = set(self.all_variables())

        # 重命名共享变量
        rename_map = {}
        for out_var, inp_var in connections:
            all_vars.discard(inp_var)  # B 的输入被 A 的输出替代
            rename_map[inp_var] = out_var

        for p in other.all_ports():
            if p.name not in rename_map:
                all_vars.add(p.name)

        # 合并边
        all_edges = list(self.internal_edges)
        for src, dst in other.internal_edges:
            src = rename_map.get(src, src)
            dst = rename_map.get(dst, dst)
            all_edges.append((src, dst))

        # 去重
        all_edges = list(set(all_edges))

        # 组合后的输入输出
        # A 的 inputs + B 的 inputs (去除被 A 输出的那些)
        new_inputs = list(self.inputs)
        for inp in other.inputs:
            if inp.name not in rename_map:
                new_inputs.append(inp)

        # A 的 outputs + B 的 outputs
        new_outputs = list(self.outputs)
        for out in other.outputs:
            renamed = rename_map.get(out.name, out.name)
            if renamed not in {o.name for o in new_outputs}:
                new_outputs.append(TypedPort(
                    name=renamed, port_type=out.port_type,
                    direction="output", description=out.description,
                ))

        return ModuleInterface(
            name=f"{self.name}∘{other.name}",
            domain=f"{self.domain}+{other.domain}",
            inputs=new_inputs,
            outputs=new_outputs,
            internal_edges=all_edges,
            physics_law=" + ".join(filter(None, [self.physics_law, other.physics_law])),
        )


# ═══════════════════════════════════════════════════════════════
# 从 CausalModule 自动生成接口
# ═══════════════════════════════════════════════════════════════

def interface_from_module(module) -> ModuleInterface:
    """
    从 CausalModule 自动生成 ModuleInterface。

    启发式: 没有父节点的变量 = input, 有父节点的 = output/internal。
    简化: 无父节点 → input, 无子节点 → output, 其他 → internal。
    """
    from creative.module_library import CausalModule

    variables = module.variables
    edges = module.edges
    types = module.type_signatures

    # 计算入度和出度
    in_degree = {v: 0 for v in variables}
    out_degree = {v: 0 for v in variables}
    for src, dst in edges:
        in_degree[dst] += 1
        out_degree[src] += 1

    inputs = []
    outputs = []

    for v in variables:
        port_type = types.get(v, "scalar")
        desc = variables.get(v, v)
        if in_degree.get(v, 0) == 0:
            inputs.append(TypedPort(name=v, port_type=port_type,
                                    direction="input", description=desc))
        elif out_degree.get(v, 0) == 0:
            outputs.append(TypedPort(name=v, port_type=port_type,
                                     direction="output", description=desc))
        # 中间节点: 既有输入又有输出 — 内部节点

    return ModuleInterface(
        name=module.name,
        domain=module.domain,
        inputs=inputs,
        outputs=outputs,
        internal_edges=list(edges),
        physics_law=module.physics_law,
    )


# ═══════════════════════════════════════════════════════════════
# 组合发现 — 自动搜索可对接的模块对
# ═══════════════════════════════════════════════════════════════

class CompositionDiscovery:
    """
    组合发现引擎 — 自动搜索可对接的模块对。

    流程:
      1. 扫描模块库，为每个模块生成接口
      2. 检查所有模块对，找类型兼容的对接点
      3. 生成组合候选
      4. 过滤 (物理约束) + 评分 (BIC)
      5. 幸存者入库
    """

    def __init__(self, module_lib=None):
        from creative.module_library import ModuleLibrary
        self.module_lib = module_lib or ModuleLibrary()

    def discover_compositions(self,
                              n_max: int = 10) -> List[ModuleInterface]:
        """发现所有可能的模块组合"""
        modules = self.module_lib.list_all()
        interfaces = [interface_from_module(m) for m in modules]

        compositions = []
        for i in range(len(interfaces)):
            for j in range(len(interfaces)):
                if i == j:
                    continue
                a, b = interfaces[i], interfaces[j]
                connections = a.can_connect_to(b)
                if connections:
                    # 尝试每种连接方式
                    for conn in connections[:2]:  # 最多试2种
                        try:
                            composed = a.compose(b, [conn])
                            if composed not in compositions:
                                compositions.append(composed)
                        except Exception:
                            pass

        # 去重 + 排序 (按规模: 边多的优先)
        seen = set()
        unique = []
        for c in compositions:
            key = frozenset(tuple(e) for e in c.internal_edges)
            if key not in seen:
                seen.add(key)
                unique.append(c)

        unique.sort(key=lambda c: -len(c.internal_edges))
        return unique[:n_max]

    def auto_compose(self, verbose: bool = True) -> Dict:
        """
        自动发现并入库所有可能的新组合。

        Returns:
          {n_discovered, compositions: [...]}
        """
        compositions = self.discover_compositions()

        n_added = 0
        for comp in compositions:
            try:
                from creative.module_library import CausalModule
                # 生成变量描述
                var_desc = {}
                for p in comp.all_ports():
                    var_desc[p.name] = p.description

                mod = CausalModule(
                    name=comp.name,
                    domain=comp.domain,
                    variables=var_desc,
                    edges=comp.internal_edges,
                    type_signatures={p.name: p.port_type for p in comp.all_ports()},
                    physics_law=comp.physics_law,
                )
                self.module_lib.register(mod)
                n_added += 1
                if verbose:
                    print(f"  📦 {comp.name}: {len(comp.inputs)} in → "
                          f"{len(comp.outputs)} out, {len(comp.internal_edges)} edges")
            except Exception:
                pass

        return {
            "n_discovered": len(compositions),
            "n_added": n_added,
            "compositions": [c.name for c in compositions],
        }
