"""
进化主循环 — 生成 → 过滤 → 保留

创造性联想的执行引擎:
  每一轮:
    1. 从模块库或骨架库中选父代
    2. 随机变异 (加权采样)
    3. 三层过滤 (物理→BIC→新颖性)
    4. 幸存者入库
    5. 重复

涌现的条件:
  模块库越大 → 变异素材越多 → 偶然出现有意义的组合 → 这就是创新
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np

from creative.module_library import CausalModule, ModuleLibrary
from creative.skeleton_library import SkeletonLibrary
from creative.mutation import CausalMutator
from creative.filter import CausalFilter


class CreativeEvolution:
    """
    进化式联想引擎。

    不是随机试错 — 是有方向的结构探索:
      模块库 + 骨架库 = 素材
      加权变异 = 生成 (偏向有意义的邻域)
      三层过滤 = 选择 (物理/统计/新颖性)
      幸存者 = 新知识
    """

    def __init__(self,
                 module_lib: Optional[ModuleLibrary] = None,
                 skeleton_lib: Optional[SkeletonLibrary] = None):
        self.module_lib = module_lib or ModuleLibrary()
        self.skeleton_lib = skeleton_lib or SkeletonLibrary()
        self.mutator = CausalMutator(self.module_lib, self.skeleton_lib)
        self.filter = CausalFilter()
        self.generation = 0
        self.discoveries: List[Dict] = []
        self.history: List[Dict] = []

    def evolve(self,
               data: np.ndarray,
               variable_names: List[str],
               type_signatures: Optional[Dict[str, str]] = None,
               n_generations: int = 100,
               population_size: int = 20,
               forbidden_edges: Optional[List[Tuple[str, str]]] = None,
               required_edges: Optional[List[Tuple[str, str]]] = None,
               novelty_threshold: float = 0.3,
               verbose: bool = True) -> Dict:
        """
        运行进化循环 — 模拟退火 + 精英保留 + 种群多样性。

        Args:
            data: 观测数据
            variable_names: 变量名
            type_signatures: 变量类型签名
            n_generations: 进化代数
            population_size: 每代个体数
            forbidden_edges: 物理禁止边
            required_edges: 物理强制边
            novelty_threshold: 新颖性阈值

        Returns:
            {generations, total_candidates, survivors, discoveries, best_graph}
        """
        # 初始化
        population = self._init_population(variable_names, population_size)
        known_modules = list(self.module_lib.list_all())

        best_graph = None
        best_score = -float("inf")
        total_candidates = 0
        survivors = 0
        elite_size = max(2, population_size // 5)

        # 模拟退火温度
        T_start = 1.0
        T_end = 0.01

        for gen in range(n_generations):
            self.generation = gen

            # 温度衰减
            T = T_start * (T_end / T_start) ** (gen / max(n_generations - 1, 1))

            # 评估当前种群
            scored = []
            for edges in population:
                result = self.filter.full_filter(
                    list(edges), variable_names, data,
                    known_modules=known_modules,
                    forbidden_edges=forbidden_edges,
                    required_edges=required_edges,
                    novelty_threshold=novelty_threshold,
                )
                scored.append((edges, result.get("tier1_score", -999), result.get("tier2_novel", False)))

            # 精英保留 — 得分最高的前 20%
            scored.sort(key=lambda x: -x[1])
            elites = [s[0] for s in scored[:elite_size]]
            best_current_score = scored[0][1]
            if best_current_score > best_score:
                best_score = best_current_score
                best_graph = list(scored[0][0])

            # 多样性维护 — 对不同结构的个体也保留
            diverse = []
            seen_structures = set()
            for edges_set, score, novel in scored:
                key = frozenset(tuple(e) for e in edges_set)
                if key not in seen_structures:
                    seen_structures.add(key)
                    diverse.append(edges_set)
                if len(diverse) >= population_size // 2:
                    break

            # 新一代
            new_population = list(elites)

            while len(new_population) < population_size:
                # 选父代: 锦标赛选择 (从精英+diverse中)
                pool = elites + diverse[:population_size]
                if len(pool) < 2:
                    pool = list(population)
                i1, i2 = np.random.choice(len(pool), 2, replace=False)
                parent = pool[i1] if scored[min(i1, len(scored)-1)][1] > scored[min(i2, len(scored)-1)][1] else pool[i2]

                # 变异 (模拟退火: 高温→大变异, 低温→小变异)
                n_mutations = max(1, int(3 * T))
                mutated = self.mutator.mutate(
                    list(parent), variable_names, type_signatures, n_mutations=n_mutations
                )
                total_candidates += 1

                # 过滤 (退火: 高温时接受较差的解)
                result = self.filter.full_filter(
                    mutated, variable_names, data,
                    known_modules=known_modules,
                    forbidden_edges=forbidden_edges,
                    required_edges=required_edges,
                    novelty_threshold=novelty_threshold,
                )

                if result["passed"]:
                    new_population.append(set(mutated))
                    survivors += 1

                    if result.get("tier2_novel", False):
                        skeleton = self.skeleton_lib.suggest_skeleton(mutated, len(variable_names))
                        self.discoveries.append({
                            "generation": gen, "edges": list(mutated),
                            "score": result["tier1_score"],
                            "novelty": result["tier2_score"],
                            "skeleton": skeleton,
                        })
                elif T > 0.3:
                    # 高温时偶尔接受次优解 (保持多样性)
                    if np.random.random() < 0.1:
                        new_population.append(set(mutated))

            population = new_population[:population_size]

            # 收敛检查
            if gen > 20 and len(self.discoveries) > 5:
                recent = [d["score"] for d in self.discoveries[-5:]]
                if max(recent) - min(recent) < 0.001:
                    if verbose:
                        print(f"  Converged at gen {gen} (T={T:.3f})")
                    break

            if verbose and gen % 20 == 0:
                print(f"  Gen {gen}: pop={len(population)}, T={T:.3f}, "
                      f"best_score={best_score:.1f}, discoveries={len(self.discoveries)}")

        return {
            "generations": self.generation + 1,
            "total_candidates": total_candidates,
            "survivors": survivors,
            "survival_rate": survivors / max(total_candidates, 1),
            "discoveries": self.discoveries,
            "best_graph": (best_graph, best_score) if best_graph else None,
        }

    def _init_population(self, variables, size):
        """初始化种群 — PC引导 + 随机扰动"""
        pop = []
        n = len(variables)

        # 尝试用 PC 算法做初始种子
        try:
            from causal.discovery import pc_algorithm
            # 生成一些引导数据 (纯随机，只为了获取 PC 的结构)
            seed_data = np.random.randn(200, n)
            dag = pc_algorithm(seed_data, variables, alpha=0.2)
            pc_edges = set()
            for v in variables:
                for c in dag.children(v):
                    pc_edges.add((v, c))
            if pc_edges:
                pop.append(pc_edges)
        except Exception:
            pc_edges = set()

        # 填充剩余个体: 从 PC 骨架变异
        for _ in range(size - len(pop)):
            edges = set(pc_edges) if pc_edges else set()
            # 随机扰动: 加/删/反转 1-2 条边
            for __ in range(3):
                if edges and np.random.random() < 0.5:
                    e = list(edges)[np.random.randint(len(edges))]
                    edges.discard(e)
                i, j = np.random.choice(n, 2, replace=False)
                a, b = variables[i], variables[j]
                if np.random.random() < 0.3:
                    if not self.mutator._would_create_cycle(edges, (a, b), variables):
                        edges.add((a, b))
            try:
                from causal.graph import CausalDAG
                CausalDAG(variables, list(edges))
                pop.append(edges)
            except Exception:
                pop.append(set())

        return pop

    def cross_domain_discover(self,
                              source_module_name: str,
                              target_variables: List[str],
                              target_types: Dict[str, str],
                              data: np.ndarray,
                              forbidden_edges: Optional[List] = None,
                              required_edges: Optional[List] = None,
                              ) -> Dict:
        """
        跨域骨架迁移 → 发现新领域的因果结构。

        这是「创造性联想」的端到端演示:
          力学 F=ma → 提取骨架 → 实例化到电磁学 → V=IR
        """
        source = self.module_lib.get(source_module_name)
        if not source:
            return {"success": False, "reason": f"Module not found: {source_module_name}"}

        # 跨域变异
        candidate = self.mutator.cross_domain_mutate(
            source, target_variables, target_types
        )

        if not candidate:
            return {"success": False, "reason": "No compatible instantiation found"}

        # 过滤
        result = self.filter.full_filter(
            candidate, target_variables, data,
            forbidden_edges=forbidden_edges,
            required_edges=required_edges,
        )

        if result["passed"]:
            skeleton = self.skeleton_lib.suggest_skeleton(candidate, len(target_variables))
            return {
                "success": True,
                "discovered_edges": candidate,
                "source_module": source_module_name,
                "skeleton": skeleton,
                "score": result["tier1_score"],
                "novelty": result.get("tier2_score", 1.0),
            }
        else:
            return {
                "success": False,
                "reason": f"Failed at Tier {result.get('tier', '?')}: {result.get('reason', '')}",
            }

    def report(self, result: Dict) -> str:
        """生成进化报告"""
        lines = ["=== Creative Evolution Report ==="]
        lines.append(f"Generations: {result['generations']}")
        lines.append(f"Candidates: {result['total_candidates']}")
        lines.append(f"Survivors: {result['survivors']} "
                     f"({result['survival_rate']:.1%})")
        lines.append(f"Discoveries: {len(result['discoveries'])}")

        if result["best_graph"]:
            edges, score = result["best_graph"]
            lines.append(f"\nBest graph ({score:.1f}):")
            for s, d in edges:
                lines.append(f"  {s} → {d}")

        if result["discoveries"]:
            lines.append("\nTop discoveries:")
            for d in result["discoveries"][-3:]:
                sk = d.get("skeleton", "?")
                lines.append(f"  Gen {d['generation']}: "
                             f"score={d['score']:.1f}, "
                             f"novelty={d['novelty']:.2f}, "
                             f"skeleton={sk}")

        return "\n".join(lines)
