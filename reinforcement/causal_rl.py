"""
Reinforcement Learning — Causal MDP + Q-Learning + Strategy Transfer

Wraps PhysCausal environments as Markov Decision Processes:
  State:   Current causal belief (P(G|D) + accuracy)
  Action:  Intervene on variable do(X=x)
  Reward:  Accuracy improvement + discovery bonus + goal achievement
  Transition: New data after intervention -> update belief

vs active_experiment:
  active_experiment/ -> single-step VOI, independent each time
  reinforcement/     -> multi-step, learn policy, cumulative reward
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
import numpy as np


class CausalMDP:
    """Causal MDP wrapping a physics simulation environment."""

    def __init__(self, env, max_steps: int = 10):
        self.env = env
        self.max_steps = max_steps
        self.n_vars = len(env.variables)
        self.true_edges = set(tuple(e) for e in env.variable_info()["ground_truth"])
        self.n_true = len(self.true_edges)
        self.data_history: List[np.ndarray] = []
        self.current_belief: Optional[Dict] = None
        self.step_count = 0
        self._prev_correct = 0
        self.reset()

    def reset(self) -> np.ndarray:
        self.env.reset()
        self.data_history = [self.env.step(30)]
        self.current_belief = None
        self.step_count = 0
        self._prev_correct = 0
        return self._get_state()

    def _get_state(self) -> np.ndarray:
        if self.current_belief and self.current_belief.edge_posteriors:
            discovered = set()
            for ep in self.current_belief.edge_posteriors:
                if ep.probability > 0.5:
                    discovered.add((ep.source, ep.target))
            correct = len(discovered & self.true_edges)
            avg_conf = np.mean([ep.probability for ep in self.current_belief.edge_posteriors])
        else:
            correct = 0; avg_conf = 0.5
        entropy = self.current_belief.entropy if self.current_belief else 1.0
        return np.array([correct / max(self.n_true, 1), avg_conf, entropy,
                         self.step_count / self.max_steps])

    def step(self, action: int) -> Tuple[np.ndarray, float, bool]:
        var_name = self.env.variables[action]
        value = np.random.uniform(0.5, 2.0)

        # Collect data: 4 rounds of reset->observe to get variation
        for _ in range(4):
            self.env.reset()
            self.data_history.append(self.env.step(5))

        # Intervene and collect
        self.env.reset()
        self.env.intervene(var_name, value)
        self.data_history.append(self.env.step(10))
        self.env.reset()

        all_data = np.vstack(self.data_history)
        self.step_count += 1

        # Update belief
        from bayesian.structural import StructuralPosterior
        sp = StructuralPosterior(method="bootstrap", max_cond_size=2)
        phys_edges = self._physics_prior()
        if phys_edges:
            self.current_belief = sp.infer_from_edges(phys_edges, self.env.variables, all_data)
        else:
            self.current_belief = sp.infer(all_data, self.env.variables, n_samples=5)

        # Compute reward
        discovered = set()
        for ep in self.current_belief.edge_posteriors:
            if ep.probability > 0.5:
                discovered.add((ep.source, ep.target))
        correct = len(discovered & self.true_edges)
        false_pos = len(discovered - self.true_edges)
        accuracy = correct / max(self.n_true, 1)

        improvement = correct - self._prev_correct
        self._prev_correct = correct

        reward = improvement * 5.0          # discovery bonus (big)
        reward += accuracy * 2.0            # accuracy signal
        reward -= false_pos * 1.0           # false positive penalty (light)
        reward -= self.step_count * 0.05    # step penalty (tiny)

        done = (self.step_count >= self.max_steps or
                (accuracy >= 0.8 and false_pos == 0))

        return self._get_state(), reward, done

    def _physics_prior(self):
        from shared import physics_prior
        return physics_prior(self.env.variables)


class CausalQLearner:
    """Q-Learning with causal-aware exploration."""

    def __init__(self, env, n_bins: int = 5,
                 alpha: float = 0.5, gamma: float = 0.95,
                 epsilon: float = 0.8):
        self.mdp = CausalMDP(env)
        self.n_bins = n_bins
        self.alpha = alpha      # learning rate
        self.gamma = gamma      # discount factor
        self.epsilon = epsilon  # initial exploration
        self.n_actions = self.mdp.n_vars
        self.Q = np.zeros((n_bins, n_bins, n_bins, n_bins, self.n_actions))
        self.visit_counts = np.zeros_like(self.Q)

    def _discretize(self, state: np.ndarray) -> tuple:
        idx = [min(self.n_bins - 1, max(0, int(s * self.n_bins))) for s in state[:4]]
        return tuple(idx)

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        s = self._discretize(state)
        if training and np.random.random() < self.epsilon:
            visits = self.visit_counts[s]
            probs = 1.0 / (visits + 1)
            probs = probs / probs.sum()
            return np.random.choice(self.n_actions, p=probs)
        return int(np.argmax(self.Q[s]))

    def learn(self, state: np.ndarray, action: int,
              reward: float, next_state: np.ndarray, done: bool):
        s = self._discretize(state)
        s_next = self._discretize(next_state)
        current_q = self.Q[s][action]
        target = reward if done else reward + self.gamma * np.max(self.Q[s_next])
        self.Q[s][action] += self.alpha * (target - current_q)
        self.visit_counts[s][action] += 1

    def train(self, n_episodes: int = 50, verbose: bool = True) -> Dict:
        episode_rewards = []
        accuracies = []
        for ep in range(n_episodes):
            state = self.mdp.reset()
            done = False
            total_reward = 0.0
            while not done:
                action = self.select_action(state, training=True)
                next_state, reward, done = self.mdp.step(action)
                self.learn(state, action, reward, next_state, done)
                state = next_state
                total_reward += reward
            episode_rewards.append(total_reward)
            acc = state[0] if len(state) >= 1 else 0.0
            accuracies.append(acc)
            if verbose and (ep + 1) % 20 == 0:
                self.epsilon = max(0.05, self.epsilon * 0.97)
                avg_r = np.mean(episode_rewards[-10:])
                avg_acc = np.mean(accuracies[-10:])
                print(f"  Ep {ep+1}: reward={avg_r:.1f}, acc={avg_acc:.0%}, eps={self.epsilon:.2f}")
        return {
            "n_episodes": n_episodes,
            "final_reward": np.mean(episode_rewards[-10:]),
            "final_accuracy": np.mean(accuracies[-10:]),
            "converged": np.mean(accuracies[-10:]) > 0.8,
        }

    def save(self, path: str = None):
        import pickle, os
        skeleton = self._skeleton_signature()
        if path is None:
            path = os.path.expanduser(f"~/.hermes/physcausal_q_{skeleton}.pkl")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {"q_table": self.Q, "visits": self.visit_counts,
                "epsilon": self.epsilon, "alpha": self.alpha, "gamma": self.gamma,
                "skeleton": skeleton, "env_name": self.mdp.env.name,
                "variables": self.mdp.env.variables}
        with open(path, "wb") as f:
            pickle.dump(data, f)
        return path

    def _skeleton_signature(self) -> str:
        edges = self.mdp.env.variable_info()["ground_truth"]
        in_deg = {}
        for s, d in edges:
            in_deg[d] = in_deg.get(d, 0) + 1
            if s not in in_deg: in_deg[s] = 0
        inputs = sum(1 for v, d in in_deg.items() if d == 0)
        outputs = sum(1 for v in self.mdp.env.variables if v not in in_deg)
        hidden = len(self.mdp.env.variables) - inputs - outputs
        return f"{inputs}in_{hidden}hid_{outputs}out"

    @classmethod
    def load(cls, env, path: str = None):
        import pickle, os
        skeleton = cls._skeleton_static(env)
        if path is None:
            path = os.path.expanduser(f"~/.hermes/physcausal_q_{skeleton}.pkl")
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            data = pickle.load(f)
        learner = cls(env, alpha=data["alpha"], gamma=data["gamma"],
                      epsilon=data["epsilon"] * 0.3)
        learner.Q = data["q_table"]
        learner.visit_counts = data["visits"]
        return learner

    @staticmethod
    def _skeleton_static(env) -> str:
        edges = env.variable_info()["ground_truth"]
        in_deg = {}
        for s, d in edges:
            in_deg[d] = in_deg.get(d, 0) + 1
        inputs = sum(1 for v in env.variables if v not in in_deg)
        outputs = sum(1 for v in env.variables if in_deg.get(v, 0) == 0 and v in [e[1] for e in edges])
        return f"{inputs}in_{len(env.variables)-inputs-outputs}hid_{outputs}out"

    def as_skill(self) -> dict:
        best_actions = {}
        for i0 in range(self.n_bins):
            for i1 in range(self.n_bins):
                for i2 in range(self.n_bins):
                    for i3 in range(self.n_bins):
                        if self.visit_counts[i0,i1,i2,i3].max() > 0:
                            a = int(np.argmax(self.Q[i0,i1,i2,i3]))
                            var = self.mdp.env.variables[a]
                            best_actions[f"acc~{i0/self.n_bins:.1f}"] = var
        return {"skill_type": "causal_policy", "env": self.mdp.env.name,
                "variables": self.mdp.env.variables,
                "n_states_learned": len(best_actions),
                "best_actions": [{s: a} for s, a in list(best_actions.items())[:5]]}

    def policy(self) -> List[str]:
        actions = []
        for i0 in range(self.n_bins):
            for i1 in range(self.n_bins):
                for i2 in range(self.n_bins):
                    for i3 in range(self.n_bins):
                        best = int(np.argmax(self.Q[i0,i1,i2,i3]))
                        if self.visit_counts[i0,i1,i2,i3,best] > 0:
                            var = self.mdp.env.variables[best]
                            actions.append((f"acc~{i0/self.n_bins:.1f}", var))
        return [f"{s}: do({a})" for s, a in actions[:5]]


class StrategyTransfer:
    """Transfer Q-table between skeleton-isomorphic environments."""

    def transfer(self, source_learner: CausalQLearner, target_env) -> CausalQLearner:
        target = CausalQLearner(target_env)
        source_vars = source_learner.mdp.env.variables
        target_vars = target_env.variables
        min_actions = min(len(source_vars), len(target_vars))
        target.Q[:,:,:,:,:min_actions] = source_learner.Q[:,:,:,:,:min_actions]
        target.epsilon = source_learner.epsilon * 0.5
        return target
