"""
Meta-Learning — 跨域策略迁移

从多个环境的训练经验中提取可泛化的干预策略，
加速新环境上的因果发现。

核心循环:
  1. 在源 envs 上训练 Q-learner → 记录经验
  2. 提取骨架 → 干预策略映射
  3. 提取领域 → 变量角色先验
  4. 在新 env 上，用元策略初始化 Q-table
  5. 测量迁移效率: with_meta vs from_scratch
"""

from __future__ import annotations
import json, os, pickle, time
from typing import Dict, List, Optional, Tuple
import numpy as np


class MetaLearner:
    """从多环境经验中学习通用的因果干预策略"""

    META_FILE = os.path.expanduser("~/.hermes/physcausal_meta.pkl")

    def __init__(self):
        self.experiences: List[Dict] = []       # 每段训练经验
        self.skeleton_strategies: Dict[str, Dict] = {}  # skeleton → 策略
        self.domain_priors: Dict[str, Dict] = {}        # domain → 先验
        self.n_envs_trained = 0

    # ═══ 训练 & 记录 ═══

    def train_and_record(
        self, q_learner, env_name: str, n_episodes: int = 60, verbose: bool = True
    ) -> Dict:
        """训练一个 Q-learner 并记录经验"""
        from reinforcement.causal_rl import CausalQLearner

        result = q_learner.train(n_episodes=n_episodes, verbose=verbose)

        # 提取经验特征
        env = q_learner.mdp.env
        skeleton = q_learner._skeleton_signature()
        variables = env.variables
        true_edges = env.variable_info()["ground_truth"]

        # 分析动作偏好: 哪些变量最常被选为干预目标
        action_counts = np.zeros(len(variables))
        for i0 in range(q_learner.n_bins):
            for i1 in range(q_learner.n_bins):
                for i2 in range(q_learner.n_bins):
                    for i3 in range(q_learner.n_bins):
                        if q_learner.visit_counts[i0,i1,i2,i3].max() > 0:
                            best = int(np.argmax(q_learner.Q[i0,i1,i2,i3]))
                            action_counts[best] += 1

        # 归一化
        total = action_counts.sum()
        action_prefs = {variables[i]: action_counts[i] / total
                        for i in range(len(variables)) if total > 0}

        # 变量角色: input (不依赖其他), output (不被依赖), intermediate
        in_deg = {}
        for s, d in true_edges:
            in_deg[d] = in_deg.get(d, 0) + 1
            if s not in in_deg:
                in_deg[s] = 0
        roles = {}
        for v in variables:
            if in_deg.get(v, 0) == 0 and any(e[1] == v for e in true_edges):
                roles[v] = "pure_input"
            elif in_deg.get(v, 0) == 0 and not any(e[1] == v for e in true_edges):
                roles[v] = "isolated"
            elif not any(e[1] == v for e in true_edges):
                roles[v] = "pure_output"
            elif any(e[0] == v for e in true_edges) and any(e[1] == v for e in true_edges):
                roles[v] = "intermediate"
            else:
                roles[v] = "endpoint"

        exp = {
            "env_name": env_name,
            "skeleton": skeleton,
            "domain": getattr(env, 'domain', 'unknown'),
            "variables": variables,
            "n_vars": len(variables),
            "true_edges": true_edges,
            "result": result,
            "action_prefs": action_prefs,
            "variable_roles": roles,
            "trained_at": time.time(),
        }
        self.experiences.append(exp)
        self.n_envs_trained += 1

        # 增量更新骨架策略
        self._update_skeleton_strategy(exp)
        self._update_domain_prior(exp)

        return result

    # ═══ 特征提取 ═══

    def _update_skeleton_strategy(self, exp: Dict):
        """从经验中提取此骨架的最佳干预顺序"""
        skeleton = exp["skeleton"]
        if skeleton not in self.skeleton_strategies:
            self.skeleton_strategies[skeleton] = {
                "count": 0,
                "action_preferences": {},
                "best_first_actions": [],
                "example_envs": [],
            }
        strat = self.skeleton_strategies[skeleton]
        strat["count"] += 1
        strat["example_envs"].append(exp["env_name"])

        # 累积动作偏好
        for var, pref in exp["action_prefs"].items():
            if var not in strat["action_preferences"]:
                strat["action_preferences"][var] = []
            strat["action_preferences"][var].append(pref)

        # 平均偏好
        avg_prefs = {v: np.mean(prefs) for v, prefs in strat["action_preferences"].items()}
        sorted_vars = sorted(avg_prefs, key=avg_prefs.get, reverse=True)
        strat["best_first_actions"] = sorted_vars
        strat["avg_preferences"] = avg_prefs

    def _update_domain_prior(self, exp: Dict):
        """从经验中提取领域特定的变量角色先验"""
        domain = exp.get("domain", "unknown")
        if domain not in self.domain_priors:
            self.domain_priors[domain] = {
                "count": 0,
                "common_inputs": {},
                "common_outputs": {},
            }
        prior = self.domain_priors[domain]
        prior["count"] += 1

        for var, role in exp.get("variable_roles", {}).items():
            if role == "pure_input":
                prior["common_inputs"][var] = prior["common_inputs"].get(var, 0) + 1
            elif role == "pure_output":
                prior["common_outputs"][var] = prior["common_outputs"].get(var, 0) + 1

    # ═══ 迁移 ═══

    def bootstrap(self, target_env, alpha: float = 0.5, gamma: float = 0.95) -> "CausalQLearner":
        """用元策略初始化新 env 的 Q-learner"""
        from reinforcement.causal_rl import CausalQLearner

        learner = CausalQLearner(target_env, alpha=alpha, gamma=gamma, epsilon=0.3)

        skeleton = learner._skeleton_signature()
        variables = target_env.variables

        # 策略 1: 骨架匹配 — 如果见过同样的骨架，用已学策略初始化
        if skeleton in self.skeleton_strategies:
            strat = self.skeleton_strategies[skeleton]
            best_actions = strat.get("best_first_actions", [])
            if best_actions:
                # 映射变量名: 在 target env 中找到对应的变量索引
                for var_name in best_actions:
                    if var_name in variables:
                        action_idx = variables.index(var_name)
                        # 给这个 action 在所有状态下加一个正向偏置
                        learner.Q[:, :, :, :, action_idx] += 0.5
                # 降低探索率: 知道该做什么
                learner.epsilon = 0.15

        # 策略 2: 领域先验 — 如果是已知领域，给常见输入变量加偏置
        domain = getattr(target_env, 'domain', 'unknown')
        if domain in self.domain_priors:
            prior = self.domain_priors[domain]
            common_inputs = prior.get("common_inputs", {})
            for var_name, count in common_inputs.items():
                if var_name in variables and count >= 1:
                    action_idx = variables.index(var_name)
                    prior_strength = min(0.3, count * 0.1)
                    learner.Q[:, :, :, :, action_idx] += prior_strength

        return learner

    def transfer_efficiency(
        self, target_env, n_episodes: int = 40
    ) -> Dict:
        """测量迁移效率: with_meta vs from_scratch"""
        from reinforcement.causal_rl import CausalQLearner

        # From scratch
        baseline = CausalQLearner(target_env)
        result_baseline = baseline.train(n_episodes=n_episodes, verbose=False)

        # With meta
        meta_learner = self.bootstrap(target_env)
        result_meta = meta_learner.train(n_episodes=n_episodes, verbose=False)

        speedup = (
            result_meta["final_accuracy"] - result_baseline["final_accuracy"]
        )

        return {
            "env": target_env.name,
            "baseline_accuracy": result_baseline["final_accuracy"],
            "meta_accuracy": result_meta["final_accuracy"],
            "speedup": speedup,
            "baseline_converged": result_baseline["converged"],
            "meta_converged": result_meta["converged"],
        }

    # ═══ 查询 ═══

    def summary(self) -> str:
        """人类可读的元学习报告"""
        lines = ["=== Meta-Learning Summary ==="]
        lines.append(f"Environments trained: {self.n_envs_trained}")
        lines.append(f"Skeletons learned: {len(self.skeleton_strategies)}")
        lines.append(f"Domains covered: {len(self.domain_priors)}")
        lines.append("")

        for skeleton, strat in self.skeleton_strategies.items():
            lines.append(f"  Skeleton {skeleton} ({strat['count']} envs):")
            lines.append(f"    Examples: {', '.join(strat['example_envs'][:3])}")
            best = strat.get("best_first_actions", [])
            if best:
                lines.append(f"    Best interventions: {' → '.join(best[:3])}")
            lines.append("")

        for domain, prior in self.domain_priors.items():
            lines.append(f"  Domain '{domain}' ({prior['count']} envs):")
            inputs = sorted(prior["common_inputs"], key=prior["common_inputs"].get, reverse=True)
            outputs = sorted(prior["common_outputs"], key=prior["common_outputs"].get, reverse=True)
            if inputs:
                lines.append(f"    Common inputs: {', '.join(inputs[:4])}")
            if outputs:
                lines.append(f"    Common outputs: {', '.join(outputs[:4])}")
            lines.append("")

        return "\n".join(lines)

    # ═══ 持久化 ═══

    def save(self):
        os.makedirs(os.path.dirname(self.META_FILE), exist_ok=True)
        data = {
            "experiences": [
                {k: v for k, v in e.items() if k != "result"}
                for e in self.experiences
            ],
            "skeleton_strategies": self.skeleton_strategies,
            "domain_priors": self.domain_priors,
            "n_envs_trained": self.n_envs_trained,
        }
        # 转换 numpy 类型
        def convert(obj):
            if isinstance(obj, np.floating):
                return float(obj)
            if isinstance(obj, np.integer):
                return int(obj)
            if isinstance(obj, dict):
                return {k: convert(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [convert(v) for v in obj]
            return obj
        with open(self.META_FILE, "wb") as f:
            pickle.dump(convert(data), f)

    def load(self) -> bool:
        if not os.path.exists(self.META_FILE):
            return False
        try:
            with open(self.META_FILE, "rb") as f:
                data = pickle.load(f)
            self.experiences = data.get("experiences", [])
            self.skeleton_strategies = data.get("skeleton_strategies", {})
            self.domain_priors = data.get("domain_priors", {})
            self.n_envs_trained = data.get("n_envs_trained", 0)
            return True
        except Exception:
            return False


# 全局单例
meta = MetaLearner()
meta.load()
