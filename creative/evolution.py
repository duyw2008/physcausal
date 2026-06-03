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
        运行进化循环。

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
            {
                "generations": n,
                "total_candidates": int,
                "survivors": int,
                "discoveries": [...],
                "best_graph": (edges, score),
            }
        """
        # 初始化: 随机图
        population = self._init_population(
            variable_names, population_size
        )

        best_graph = None
        best_score = -float("inf")
        known_modules = list(self.module_lib.list_all())

        total_candidates = 0
        survivors = 0

        for gen in range(n_generations):
            self.generation = gen
            new_population = []

            for i in range(population_size):
                # 选父代: 精英选择
                parent = population[i % len(population)]

                # 变异
                mutated = self.mutator.mutate(
                    list(parent), variable_names, type_signatures, n_mutations=2
                )
                total_candidates += 1

                # 过滤
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

                    score = result["tier1_score"]
                    if score > best_score:
                        best_score = score
                        best_graph = list(mutated)

                    # 足够新颖 → 记录为发现
                    if result.get("tier2_novel", False):
                        skeleton = self.skeleton_lib.suggest_skeleton(
                            mutated, len(variable_names)
                        )
                        discovery = {
                            "generation": gen,
                            "edges": list(mutated),
                            "score": score,
                            "novelty": result["tier2_score"],
                            "skeleton": skeleton,
                        }
                        self.discoveries.append(discovery)

                        if verbose and len(self.discoveries) % 5 == 0:
                            print(f"  Gen {gen}: Discovery! "
                                  f"edges={len(mutated)}, score={score:.1f}, "
                                  f"novelty={result['tier2_score']:.2f}")

            # 保持种群大小
            population = new_population[:population_size] if new_population else population

            # 收敛检查
            if len(self.discoveries) > 10 and gen > 50:
                recent = self.discoveries[-5:]
                scores = [d["score"] for d in recent]
                if max(scores) - min(scores) < 0.01:
                    if verbose:
                        print(f"  Converged at gen {gen}")
                    break

        return {
            "generations": self.generation + 1,
            "total_candidates": total_candidates,
            "survivors": survivors,
            "survival_rate": survivors / max(total_candidates, 1),
            "discoveries": self.discoveries,
            "best_graph": (best_graph, best_score) if best_graph else None,
        }

    def _init_population(self, variables, size):
        """初始化种群 — 随机稀疏图"""
        pop = []
        n = len(variables)
        for _ in range(size):
            edges = set()
            for i in range(n):
                for j in range(i + 1, n):
                    if np.random.random() < 0.3:  # 30% 密度
                        if np.random.random() < 0.5:
                            edges.add((variables[i], variables[j]))
                        else:
                            edges.add((variables[j], variables[i]))
            # 只保留有效的 DAG
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
