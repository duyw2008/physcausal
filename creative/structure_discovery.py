"""
结构发现 — 自动发现跨领域因果结构的同构关系

核心: 扫描模块库, 将因果图结构相同的模块分组,
      每组自动生成一个骨架, 实现无监督的跨域联想。

三步骤:
  1. 拓扑签名 — 为每个模块计算度分布签名
  2. 同构分组 — 相同签名的模块归入一组
  3. 骨架生成 — 每组生成一个骨架模板
"""

from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Set, Tuple

from creative.module_library import ModuleLibrary, CausalModule


def _topology_signature(edges: List[Tuple[str, str]]) -> str:
    """
    计算因果图的拓扑签名。

    签名 = 节点度数分布 + 边密度。
    两个签名相同的图是同构候选 (足够小图时等价于同构)。
    """
    if not edges:
        return "empty"

    in_deg = defaultdict(int)
    out_deg = defaultdict(int)
    nodes = set()
    for src, dst in edges:
        out_deg[src] += 1
        in_deg[dst] += 1
        nodes.add(src)
        nodes.add(dst)

    # 度数分布: 按 (in, out) 排序
    degree_pattern = sorted((in_deg[n], out_deg[n]) for n in nodes)

    # 签名: n节点_d1_d2_d3_e边数
    sig_parts = [str(len(nodes))]
    sig_parts.append(str(len(edges)))
    sig_parts.extend(f"{i}{o}" for i, o in degree_pattern)
    return "_".join(sig_parts)


class StructureDiscovery:
    """自动结构发现引擎"""

    def __init__(self):
        self.module_lib = ModuleLibrary()
        self.groups: Dict[str, List[str]] = {}  # signature -> [module_names]

    def scan(self) -> Dict[str, List[str]]:
        """扫描模块库, 发现同构组"""
        self.groups = defaultdict(list)

        for mod in self.module_lib.list_all():
            sig = _topology_signature(mod.edges)
            self.groups[sig].append(mod.name)

        # 只保留有 2+ 成员的组
        self.groups = {k: v for k, v in self.groups.items() if len(v) >= 2}
        return dict(self.groups)

    def associate(self, module_name: str) -> List[Dict]:
        """
        给定一个模块名, 返回与其同构的所有模块。
        
        Returns:
            [{name, domain, edges, shared_pattern}, ...]
        """
        mod = self.module_lib.get(module_name)
        if not mod:
            return []

        sig = _topology_signature(mod.edges)
        group = self.groups.get(sig, [mod.name])

        results = []
        for name in group:
            if name == module_name:
                continue
            other = self.module_lib.get(name)
            if other:
                results.append({
                    "name": other.name,
                    "domain": other.domain,
                    "edges": other.edges,
                    "shared_pattern": f"同构({sig}): 相同因果拓扑",
                })
        return results

    def generate_skeletons(self) -> List[Dict]:
        """从同构组自动生成骨架"""
        from creative.skeleton_library import SkeletonLibrary

        self.scan()
        skeleton_lib = SkeletonLibrary()
        new_skeletons = []

        for sig, module_names in self.groups.items():
            # 用第一个模块的结构作为骨架模板
            first_mod = self.module_lib.get(module_names[0])
            if not first_mod:
                continue

            # 构造骨架: 用编号替代变量名
            var_map = {}
            next_id = 0
            renamed_edges = []
            for src, dst in first_mod.edges:
                if src not in var_map:
                    var_map[src] = next_id
                    next_id += 1
                if dst not in var_map:
                    var_map[dst] = next_id
                    next_id += 1
                renamed_edges.append((var_map[src], var_map[dst]))

            # 检查是否已有相同结构的骨架
            skeleton_name = f"auto_{sig}"
            new_skeletons.append({
                "name": skeleton_name,
                "n_nodes": len(var_map),
                "edges": renamed_edges,
                "member_modules": module_names,
                "signature": sig,
            })

        return new_skeletons

    def summary(self) -> str:
        """人类可读的联想报告"""
        self.scan()
        lines = ["=== 结构联想 (Structure Discovery) ==="]
        lines.append(f"发现 {len(self.groups)} 个同构组:")
        lines.append("")

        for sig, names in sorted(self.groups.items()):
            # 获取代表模块
            rep = self.module_lib.get(names[0])
            if not rep:
                continue
            edges_str = ", ".join(f"{s}→{d}" for s, d in rep.edges)
            n_inputs = len(set(s for s, _ in rep.edges) - set(d for _, d in rep.edges))
            n_outputs = len(set(d for _, d in rep.edges) - set(s for s, _ in rep.edges))

            lines.append(f"  骨架 [{n_inputs}→{n_outputs}]: {edges_str}")
            lines.append(f"    成员 ({len(names)}): {', '.join(names)}")
            lines.append("")
        
        return "\n".join(lines)


# 全局单例
discovery = StructureDiscovery()
