"""
主动学习循环 — VOI → 干预 → 数据 → 更新信念 → 重复

PhysCausal + RL 的核心闭环:
  1. 选干预: VOI 最大 (bayesian/active_learning)
  2. 执行:   env.intervene(var, value)
  3. 收集:   env.step(n) → 新数据
  4. 更新:   P(G|D) (bayesian/structural)
  5. 评估:   是否收敛 (所有边置信度 > 阈值)
  6. 扩展:   发现的因果结构 → 模块库 (creative/module_library)

效果:
  短期 — 消除当前场景的因果不确定性
  中期 — 模块库自动增长
  长期 — 跨域骨架自动涌现
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from env.physics_sim import PhysicsEnv, make_env
from bayesian.structural import StructuralPosterior, GraphPosterior
from bayesian.active_learning import ActiveExperimentDesign
from creative.module_library import ModuleLibrary, CausalModule


class ActiveLearner:
    """
    主动学习智能体 — 通过干预实验发现因果结构。

    循环:
      while not converged:
        experiment = pick_best_intervention()
        data += env.experiment(experiment)
        belief = update_posterior(data)
    """

    def __init__(self, env: PhysicsEnv):
        self.env = env
        self.structural = StructuralPosterior(method="bootstrap", max_cond_size=2)
        self.experiment_design = ActiveExperimentDesign()
        self.module_lib = ModuleLibrary()

        # 状态
        self.data_history: List[np.ndarray] = []
        self.posterior: Optional[GraphPosterior] = None
        self.experiments_done: List[str] = []
        self.episode = 0
        self.total_samples = 0
        self._last_inference_samples = 0

    def _physics_prior(self, variables):
        """从物理定律库获取已知因果结构 — 零计算代价"""
        from physics.laws import library
        
        # 中英文变量名映射 (仿真环境用英文缩写)
        ZH_MAP = {
            "V": "voltage", "R": "resistance", "I": "current",
            "L": "length", "g": "gravity", "T": "period",
            "k": "elastic_constant", "m": "mass", "omega": "angular_velocity",
            "m1": "mass", "m2": "mass", "v1": "velocity", "v2": "velocity",
            "v1p": "velocity", "v2p": "velocity",
            "flux_change": "magnetic_flux_change", "coil_turns": "coil_turns",
            "induced_emf": "induced_emf",
            "n1": "refractive_index", "theta1": "incident_angle",
            "n2": "refractive_index", "theta2": "refraction_angle",
            "source_freq": "source_frequency", "source_vel": "source_velocity",
            "observer_vel": "observer_velocity", "observed_freq": "observed_frequency",
        }
        vars_en = [ZH_MAP.get(v, v.lower()) for v in variables]
        
        edges = set()
        for law in library.list_all():
            for src, dst in law.causal_direction:
                if src in vars_en and dst in vars_en:
                    si = vars_en.index(src)
                    di = vars_en.index(dst)
                    edges.add((variables[si], variables[di]))
        if edges:
            return list(edges)
        return []

    def run(self,
            n_episodes: int = 10,
            samples_per_experiment: int = 50,
            confidence_threshold: float = 0.8,
            verbose: bool = True) -> Dict:
        """
        运行主动学习循环。

        Args:
            n_episodes: 最大实验轮数
            samples_per_experiment: 每轮实验收集的样本数
            confidence_threshold: 边置信度阈值，所有边超过此值 → 收敛

        Returns:
            {
                "episodes": n,
                "total_samples": int,
                "converged": bool,
                "discovered_edges": [...],
                "true_edges": [...],
                "accuracy": float,
                "experiments": [...],
                "module_added": bool,
            }
        """
        env_info = self.env.variable_info()
        true_edges = set(tuple(e) for e in env_info["ground_truth"])

        if verbose:
            print(f"Active Learning: {env_info['name']} ({env_info['domain']})")
            print(f"  Variables: {env_info['variables']}")
            print(f"  Ground truth: {len(true_edges)} edges")

        # 初始观测 (无干预)
        initial_data = self.env.step(samples_per_experiment)
        self.data_history.append(initial_data)
        self.total_samples = len(initial_data)

        for ep in range(n_episodes):
            self.episode = ep

            # 更新后验 — 物理优先: 用已知结构, 跳过 PC
            all_data = np.vstack(self.data_history)
            if ep == 0 or self.total_samples - self._last_inference_samples >= 100:
                phys_edges = self._physics_prior(env_info["variables"])
                if phys_edges:
                    posterior = self.structural.infer_from_edges(
                        phys_edges, env_info["variables"], all_data
                    )
                else:
                    posterior = self.structural.infer(
                        all_data, env_info["variables"], n_samples=5
                    )
                self.posterior = posterior
                self._last_inference_samples = self.total_samples

            if verbose:
                high = sum(1 for e in self.posterior.edge_posteriors if e.probability > 0.7)
                total = len(self.posterior.edge_posteriors)
                print(f"\n  Episode {ep+1}: {self.total_samples} samples, "
                      f"{high}/{total} edges high-confidence")

            # 选实验
            plan = self.experiment_design.propose_experiments(
                self.posterior, env_info["variables"], max_candidates=3
            )
            if plan.recommended.variable == "—":
                if verbose:
                    print(f"    No useful experiment → converged")
                break

            experiment_var = plan.recommended.variable
            if experiment_var in self.experiments_done:
                # 避免重复实验
                remaining = [c.variable for c in plan.candidates 
                           if c.variable not in self.experiments_done]
                if remaining:
                    experiment_var = remaining[0]
                else:
                    if verbose: print(f"    All candidate experiments done → converged")
                    break

            # 执行干预
            value = np.random.uniform(0.5, 2.0)
            new_data = self.env.experiment(
                {experiment_var: value}, n_samples=samples_per_experiment
            )
            self.data_history.append(new_data)
            self.total_samples += len(new_data)
            self.experiments_done.append(experiment_var)

            if verbose:
                edges_affected = len(plan.recommended.affected_edges)
                print(f"    do({experiment_var}={value:.1f}) → "
                      f"+{len(new_data)} samples, affects {edges_affected} edges")

            # 收敛检查
            converged = self._check_convergence(confidence_threshold)
            if converged:
                if verbose: print(f"    All edges above {confidence_threshold} → converged!")
                break

        # 最终评估
        final_posterior = self.structural.infer(
            np.vstack(self.data_history), env_info["variables"], n_samples=50
        )
        discovered = set()
        for ep_post in final_posterior.edge_posteriors:
            if ep_post.probability > 0.5:
                discovered.add((ep_post.source, ep_post.target))

        correct = len(discovered & true_edges)
        false_pos = len(discovered - true_edges)
        missed = len(true_edges - discovered)

        # 尝试加入模块库
        module_added = False
        if correct >= len(true_edges) * 0.7:
            try:
                mod = CausalModule(
                    name=f"{env_info['name']}_discovered",
                    domain=env_info['domain'],
                    variables={v: v for v in env_info['variables']},
                    edges=list(discovered),
                    type_signatures={v: "scalar" for v in env_info['variables']},
                )
                self.module_lib.register(mod)
                module_added = True
                if verbose:
                    print(f"\n  ✓ Module added: {mod.name}")
            except Exception:
                pass

        accuracy = correct / len(true_edges) if true_edges else 1.0

        result = {
            "episodes": self.episode + 1,
            "total_samples": self.total_samples,
            "converged": self._check_convergence(confidence_threshold),
            "discovered_edges": list(discovered),
            "true_edges": list(true_edges),
            "correct": correct,
            "false_positives": false_pos,
            "missed": missed,
            "accuracy": accuracy,
            "experiments": self.experiments_done,
            "module_added": module_added,
        }

        if verbose:
            print(f"\n  Final: {correct}/{len(true_edges)} correct, "
                  f"{false_pos} false+, {missed} missed "
                  f"({accuracy:.0%} accuracy, {self.total_samples} total samples)")

        return result

    def _check_convergence(self, threshold: float) -> bool:
        if not self.posterior or not self.posterior.edge_posteriors:
            return False
        for ep in self.posterior.edge_posteriors:
            if ep.probability < threshold and ep.probability > (1 - threshold):
                return False
        return True

    def run_all_envs(self, env_names: Optional[List[str]] = None,
                     n_episodes: int = 10,
                     verbose: bool = True) -> Dict[str, Dict]:
        """在所有环境中运行主动学习"""
        if env_names is None:
            env_names = list(ENV_REGISTRY.keys())
        
        results = {}
        for name in env_names:
            if verbose:
                print(f"\n{'='*50}")
            env = make_env(name)
            learner = ActiveLearner(env)
            results[name] = learner.run(n_episodes=n_episodes, verbose=verbose)
            env.reset()

        if verbose:
            self._summary(results)

        return results

    def _summary(self, results: Dict[str, Dict]):
        print(f"\n{'='*60}")
        print("  Active Learning Summary")
        print(f"{'='*60}")
        total_correct = 0
        total_edges = 0
        for name, r in results.items():
            acc = r["accuracy"]
            samples = r["total_samples"]
            exp_count = len(r["experiments"])
            bar = "█" * int(acc * 20) + "░" * (20 - int(acc * 20))
            print(f"  {name:12s}  {bar}  {acc:.0%}  "
                  f"{r['correct']}/{len(r['true_edges'])} edges  "
                  f"{samples} samples  {exp_count} exps  "
                  f"{'📦' if r['module_added'] else '  '}")
            total_correct += r["correct"]
            total_edges += len(r["true_edges"])
        print(f"  {'─'*50}")
        print(f"  TOTAL: {total_correct}/{total_edges} edges "
              f"({total_correct/total_edges:.0%})")
        print(f"  Module library: {ModuleLibrary().stats()['total_modules']} modules")


# Import for run_all_envs
from env.physics_sim import ENV_REGISTRY
