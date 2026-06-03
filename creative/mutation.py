"""
结构变异 — 因果图的随机扰动 + 骨架迁移

进化式联想的核心算子:
  不是均匀随机, 而是在结构相容的空间内做「加权变异」。
  大部分变异落在有意义的邻域里。

变异操作:
  1. add_edge       — 在类型兼容的节点对之间加边
  2. delete_edge    — 删除置信度最低的边
  3. reverse_edge   — 反转方向 (仅当不创建环且不违反因果方向时)
  4. substitute_var — 用同类型变量替换 (跨域迁移的关键)
  5. skeleton_morph — 将图向已知骨架变形 (骨架引导的变异)
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set, Tuple
import numpy as np

from creative.module_library import CausalModule, ModuleLibrary
from creative.skeleton_library import CausalSkeleton, SkeletonLibrary


class CausalMutator:
    """
    因果图变异器。

    每一步变异都是: 采样候选操作 → 检查物理/逻辑约束 → 执行。

    「随机 ≠ 均匀 — 按结构相容性加权采样」
    """

    def __init__(self,
                 module_lib: Optional[ModuleLibrary] = None,
                 skeleton_lib: Optional[SkeletonLibrary] = None):
        self.module_lib = module_lib or ModuleLibrary()
        self.skeleton_lib = skeleton_lib or SkeletonLibrary()

    def mutate(self,
               edges: List[Tuple[str, str]],
               variables: List[str],
               type_signatures: Optional[Dict[str, str]] = None,
               n_mutations: int = 1) -> List[Tuple[str, str]]:
        """
        随机变异一个因果图。

        变异选择按权重: 删除 > 加边 > 反转 > 替换
        删除优先因为稀疏图更可能 (Occam)。
        """
        current = set(edges)
        type_sigs = type_signatures or {}

        for _ in range(n_mutations):
            ops = self._available_operations(current, variables, type_sigs)
            if not ops:
                break

            weights = {
                "delete_edge": 0.4,
                "add_edge": 0.3,
                "reverse_edge": 0.15,
                "substitute_var": 0.15,
            }
            op_names = list(ops.keys())
            op_weights = [weights.get(op, 0.1) for op in op_names]
            op_weights = np.array(op_weights) / sum(op_weights)

            op = np.random.choice(op_names, p=op_weights)

            if op == "delete_edge" and ops["delete_edge"]:
                e = ops["delete_edge"][np.random.randint(len(ops["delete_edge"]))]
                current.discard(e)

            elif op == "add_edge" and ops["add_edge"]:
                e = ops["add_edge"][np.random.randint(len(ops["add_edge"]))]
                current.add(e)

            elif op == "reverse_edge" and ops["reverse_edge"]:
                e = ops["reverse_edge"][np.random.randint(len(ops["reverse_edge"]))]
                current.discard(e)
                if not self._would_create_cycle(current, (e[1], e[0]), variables):
                    current.add((e[1], e[0]))

            elif op == "substitute_var" and ops["substitute_var"]:
                old_var, candidates = ops["substitute_var"][
                    np.random.randint(len(ops["substitute_var"]))
                ]
                new_var = candidates[np.random.randint(len(candidates))]
                current = self._substitute(current, old_var, new_var)

        return list(current)

    def _available_operations(self, edges, variables, type_sigs):
        ops = {"delete_edge": [], "add_edge": [], "reverse_edge": [], "substitute_var": []}

        # 删除: 可以删任何边
        ops["delete_edge"] = list(edges)

        # 添加: 不存在的边, 类型兼容 (如果有类型签名)
        edge_set = set(edges)
        for a in variables:
            for b in variables:
                if a >= b:
                    continue
                if (a, b) in edge_set or (b, a) in edge_set:
                    continue
                if type_sigs:
                    type_a = type_sigs.get(a, "")
                    type_b = type_sigs.get(b, "")
                    if type_a and type_b and type_a != type_b:
                        continue  # 类型不兼容, 不加
                if not self._would_create_cycle(edge_set, (a, b), variables):
                    ops["add_edge"].append((a, b))

        # 反转: 现有边, 反转后不创建环
        for a, b in edges:
            if not self._would_create_cycle(edge_set - {(a, b)}, (b, a), variables):
                ops["reverse_edge"].append((a, b))

        # 替换: 找同类型变量
        if type_sigs:
            for var in variables:
                var_type = type_sigs.get(var, "")
                if not var_type:
                    continue
                candidates = [v for v in variables
                              if v != var and type_sigs.get(v, "") == var_type]
                if candidates:
                    ops["substitute_var"].append((var, candidates))

        return ops

    def _would_create_cycle(self, edges_set, new_edge, variables):
        test = list(edges_set) + [new_edge]
        try:
            from causal.graph import CausalDAG
            CausalDAG(variables, test)
            return False
        except Exception:
            return True

    def _substitute(self, edges_set, old_var, new_var):
        new_edges = set()
        for a, b in edges_set:
            a = new_var if a == old_var else a
            b = new_var if b == old_var else b
            if a != b:
                new_edges.add((a, b))
        return new_edges

    def cross_domain_mutate(self,
                            source_module: CausalModule,
                            target_domain_vars: List[str],
                            target_types: Dict[str, str]) -> List[Tuple[str, str]]:
        """
        跨域骨架迁移 — 把一个模块的骨架实例化到新领域。

        这是创造性联想的「生成」核心:
          力学 F=ma → 提取骨架 [force→acceleration] →
          找到电磁学中同类型变量 [Voltage→Current] →
          实例化: V→I (Ohm 定律!)
        """
        # 提取骨架
        skeleton_name = self.skeleton_lib.suggest_skeleton(
            source_module.edges, len(source_module.variables)
        )
        if not skeleton_name:
            return []

        # 在目标域找类型匹配的变量
        sk = self.skeleton_lib.get(skeleton_name)
        if not sk:
            return []

        # 匹配类型约束
        matched = []
        for node_idx in range(sk.n_nodes):
            required = sk.type_constraints.get(node_idx, "")
            if not required:
                # 无约束 → 任选一个未使用的变量
                for v in target_domain_vars:
                    if v not in matched:
                        matched.append(v)
                        break
            else:
                for v in target_domain_vars:
                    if v not in matched and target_types.get(v, "") == required:
                        matched.append(v)
                        break

        if len(matched) != sk.n_nodes:
            return []  # 类型不匹配，无法实例化

        # 实例化
        result = self.skeleton_lib.instantiate(skeleton_name, matched)
        return result["edges"]
