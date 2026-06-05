"""
强化学习 — 因果 MDP + Q-Learning + 策略迁移

将 PhysCausal 环境包装为马尔可夫决策过程:
  State:   当前因果信念 (P(G|D) + 准确率)
  Action:  干预某个变量 do(X=x)
  Reward:  准确率提升 + 发现奖励 + 目标达成
  Transition: 干预后收集新数据 → 更新信念

和主动实验的区别:
  active_experiment/ → 单步 VOI, 每次独立
  reinforcement/     → 多步, 学策略, 累计回报
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


class CausalMDP:
    """
    因果 MDP — 将物理仿真环境包装为 RL 环境。

    State 编码:
      [n_correct, n_total, avg_edge_confidence, entropy]

    Action 空间:
      0..n_vars-1 → 干预对应变量
    """

    def __init__(self, env, max_steps: int = 10):
        self.env = env
        self.max_steps = max_steps
        self.n_vars = len(env.variables)

        # 真实因果结构
        self.true_edges = set(tuple(e) for e in env.variable_info()["ground_truth"])
        self.n_true = len(self.true_edges)

        # 状态
        self.data_history: List[np.ndarray] = []
        self.current_belief: Optional[Dict] = None
        self.step_count = 0
        self.reset()

    def reset(self) -> np.ndarray:
        """重置 MDP"""
        self.env.reset()
        self.data_history = [self.env.step(30)]  # 初始观测
        self.current_belief = None
        self.step_count = 0
        return self._get_state()

    def _get_state(self) -> np.ndarray:
        """编码当前状态"""
        # 准确率
        if self.current_belief and self.current_belief.edge_posteriors:
            discovered = set()
            for ep in self.current_belief.edge_posteriors:
                if ep.probability > 0.5:
                    discovered.add((ep.source, ep.target))
            correct = len(discovered & self.true_edges)
            total = len(discovered)
            avg_conf = np.mean([ep.probability for ep in self.current_belief.edge_posteriors])
        else:
            correct = 0; total = 0; avg_conf = 0.5

        entropy = self.current_belief.entropy if self.current_belief else 1.0

        return np.array([correct / max(self.n_true, 1), avg_conf, entropy, self.step_count / self.max_steps])

    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        """
        执行一步 — 干预变量 action，收集数据，更新信念。

        Returns:
            (next_state, reward, done)
        """
        var_name = self.env.variables[action]
        value = np.random.uniform(0.5, 2.0)

        # 执行干预
        new_data = self.env.experiment({var_name: value}, n_samples=30)
        self.data_history.append(new_data)
        all_data = np.vstack(self.data_history)
        self.step_count += 1

        # 更新信念
        from bayesian.structural import StructuralPosterior
        sp = StructuralPosterior(method="bootstrap", max_cond_size=2)
        phys_edges = self._physics_prior()
        if phys_edges:
            self.current_belief = sp.infer_from_edges(phys_edges, self.env.variables, all_data)
        else:
            self.current_belief = sp.infer(all_data, self.env.variables, n_samples=5)

        # 奖励: 准确率 + 发现奖励 + 效率惩罚
        discovered = set()
        for ep in self.current_belief.edge_posteriors:
            if ep.probability > 0.5:
                discovered.add((ep.source, ep.target))

        correct = len(discovered & self.true_edges)
        false_pos = len(discovered - self.true_edges)
        accuracy = correct / max(self.n_true, 1)

        # 奖励: 改进 vs 上一轮 + 发现奖励
        # 用 edge 置信度变化来判断进步
        prev_correct = self._prev_correct if hasattr(self, '_prev_correct') else 0
        self._prev_correct = correct

        improvement = correct - prev_correct  # +1 = 发现新边, -1 = 丢边
        reward = improvement * 5.0            # 发现奖励 (大)
        reward += accuracy * 2.0              # 准确率 (持续信号)
        reward -= false_pos * 1.0             # 假阳性惩罚 (轻)
        reward -= self.step_count * 0.05      # 步数惩罚 (微小, 鼓励效率)

        # 是否完成
        done = (self.step_count >= self.max_steps or
                (accuracy >= 0.8 and false_pos == 0))

        return self._get_state(), reward, done

    def _physics_prior(self):
        from physics.laws import library
        from shared import ZH_MAP, physics_prior
        return physics_prior(self.env.variables)


class CausalQLearner:
    """
    Q-Learning with causal-aware exploration.

    状态离散化: 将连续状态映射到有限个桶
    Q(s,a) 表: 通过经验更新
    探索: epsilon-greedy + VOI 偏向
    """

    def __init__(self, env, n_bins: int = 5,
                 alpha: float = 0.5, gamma: float = 0.95,
                 epsilon: float = 0.8):
        """
        alpha:   学习率 (0.5 = 快速学习)
        gamma:   折扣因子 (0.95 = 重视长期回报)
        epsilon: 初始探索率 (0.8 = 开始时多探索)
        """
        self.mdp = CausalMDP(env)
        self.n_bins = n_bins
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

        self.n_actions = self.mdp.n_vars
        # Q(s,a) — 状态空间: n_bins^4 (4维状态) × n_actions
        self.Q = np.zeros((n_bins, n_bins, n_bins, n_bins, self.n_actions))
        self.visit_counts = np.zeros_like(self.Q)

    def _discretize(self, state: np.ndarray) -> Tuple[int, int, int, int]:
        """连续状态 → 离散桶索引"""
        # 每个维度: 0-1 → 0..n_bins-1
        idx = [min(self.n_bins - 1, max(0, int(s * self.n_bins))) for s in state[:4]]
        return tuple(idx)

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """epsilon-greedy 选择动作"""
        s = self._discretize(state)
        if training and np.random.random() < self.epsilon:
            # 探索: 随机但偏向低访问次数的动作
            visits = self.visit_counts[s]
            probs = 1.0 / (visits + 1)
            probs = probs / probs.sum()
            return np.random.choice(self.n_actions, p=probs)
        else:
            return np.argmax(self.Q[s])

    def learn(self, state: np.ndarray, action: int,
              reward: float, next_state: np.ndarray, done: bool):
        """Q-Learning 更新"""
        s = self._discretize(state)
        s_next = self._discretize(next_state)

        current_q = self.Q[s][action]

        if done:
            target = reward
        else:
            target = reward + self.gamma * np.max(self.Q[s_next])

        self.Q[s][action] += self.alpha * (target - current_q)
        self.visit_counts[s][action] += 1

    def train(self, n_episodes: int = 50, verbose: bool = True) -> Dict:
        """训练 Q-Learning 策略"""
        episode_rewards = []
        accuracies = []

        for ep in range(n_episodes):
            state = self.mdp.reset()
            done = False
            total_reward = 0.0
            steps = 0

            while not done:
                action = self.select_action(state, training=True)
                next_state, reward, done = self.mdp.step(action)
                self.learn(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
                steps += 1

            episode_rewards.append(total_reward)
            # 最终准确率
            acc = state[0] if len(state) >= 1 else 0.0
            accuracies.append(acc)

            if verbose and (ep + 1) % 20 == 0:
                self.epsilon = max(0.05, self.epsilon * 0.97)  # 慢衰减
                avg_r = np.mean(episode_rewards[-10:])
                avg_acc = np.mean(accuracies[-10:])
                print(f"  Ep {ep+1}: reward={avg_r:.1f}, "
                      f"acc={avg_acc:.0%}, epsilon={self.epsilon:.2f}")

        return {
            "n_episodes": n_episodes,
            "final_reward": np.mean(episode_rewards[-10:]),
            "final_accuracy": np.mean(accuracies[-10:]),
            "converged": np.mean(accuracies[-10:]) > 0.8,
        }

    def save(self, path: str = None):
        """保存 Q-table 和策略到磁盘"""
        import pickle, os
        if path is None:
            path = os.path.expanduser(f"~/.hermes/physcausal_q_{self.mdp.env.name}.pkl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {
            "q_table": self.Q,
            "visits": self.visit_counts,
            "epsilon": self.epsilon,
            "alpha": self.alpha,
            "gamma": self.gamma,
            "env_name": self.mdp.env.name,
            "variables": self.mdp.env.variables,
        }
        with open(path, "wb") as f:
            pickle.dump(data, f)
        return path

    @classmethod
    def load(cls, env, path: str = None):
        """从磁盘加载 Q-table"""
        import pickle, os
        if path is None:
            path = os.path.expanduser(f"~/.hermes/physcausal_q_{env.name}.pkl")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            data = pickle.load(f)
        learner = cls(env, alpha=data["alpha"], gamma=data["gamma"],
                      epsilon=data["epsilon"])
        learner.Q = data["q_table"]
        learner.visit_counts = data["visits"]
        return learner

    def as_skill(self) -> dict:
        """将学到的策略导出为技能格式"""
        best_actions = {}
        for i0 in range(self.n_bins):
            for i1 in range(self.n_bins):
                for i2 in range(self.n_bins):
                    for i3 in range(self.n_bins):
                        if self.visit_counts[i0,i1,i2,i3].max() > 0:
                            a = np.argmax(self.Q[i0,i1,i2,i3])
                            var = self.mdp.env.variables[a]
                            best_actions[f"acc≈{i0/self.n_bins:.1f}"] = var
        return {
            "skill_type": "causal_policy",
            "env": self.mdp.env.name,
            "variables": self.mdp.env.variables,
            "n_states_learned": len(best_actions),
            "best_actions": [{s: a} for s, a in list(best_actions.items())[:5]],
        }

    def policy(self) -> List[str]:
        """提取学习到的策略 — 每个状态对应的最优动作"""
        actions = []
        for i0 in range(self.n_bins):
            for i1 in range(self.n_bins):
                for i2 in range(self.n_bins):
                    for i3 in range(self.n_bins):
                        best = np.argmax(self.Q[i0, i1, i2, i3])
                        if self.visit_counts[i0, i1, i2, i3, best] > 0:
                            var = self.mdp.env.variables[best]
                            actions.append((f"acc≈{i0/self.n_bins:.1f}", var))
        return [f"{state}: do({action})" for state, action in actions[:5]]


class StrategyTransfer:
    """
    策略迁移 — 基于因果骨架同构。

    当两个环境共享骨架时 (如 pendulum～spring),
    将在源环境学到的策略迁移到目标环境。
    """

    def __init__(self):
        from creative.skeleton_library import SkeletonLibrary
        self.skeletons = SkeletonLibrary()

    def transfer(self, source_learner: CausalQLearner,
                       target_env) -> CausalQLearner:
        """
        将源 Q-table 复制到目标环境。

        迁移条件: 两个环境共用同一个因果骨架。
        迁移方式: 直接复制 Q 值 (按变量顺序重排)。
        """
        target = CausalQLearner(target_env)
        # 变量名 → 骨架变量 → 目标变量
        source_vars = source_learner.mdp.env.variables
        target_vars = target_env.variables

        # 简单映射: 按变量位置复制 (只有同构时才正确)
        min_actions = min(len(source_vars), len(target_vars))
        target.Q[:, :, :, :, :min_actions] = source_learner.Q[:, :, :, :, :min_actions]
        target.epsilon = source_learner.epsilon * 0.5  # 更多利用，更少探索
        return target
