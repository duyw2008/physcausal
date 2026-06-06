#!/usr/bin/env python3
"""
压力测试 v2: 从未知中发现 (轻量版, 避开 bootstrap 挂死)
"""
import sys, os, time, warnings
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
warnings.filterwarnings("ignore", category=RuntimeWarning)

from causal.discovery import pc_algorithm, ges_algorithm
from causal.graph import CausalDAG


def f1_score(predicted, truth):
    s_pred = set(tuple(e) for e in predicted)
    s_truth = set(tuple(e) for e in truth)
    if not s_pred and not s_truth:
        return 1.0, 1.0, 1.0, 0, 0, 0
    tp = len(s_pred & s_truth)
    fp = len(s_pred - s_truth)
    fn = len(s_truth - s_pred)
    p = tp / (tp + fp) if (tp + fp) > 0 else 0
    r = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
    return f1, p, r, tp, fp, fn


def generate_scm(n_vars, edge_prob=0.4, seed=None):
    """生成随机线性 DAG 并采样"""
    rng = np.random.RandomState(seed)
    
    # Generate DAG (upper triangular)
    adj = np.zeros((n_vars, n_vars), dtype=int)
    edges = []
    for i in range(n_vars):
        for j in range(i + 1, n_vars):
            if rng.random() < edge_prob:
                adj[i, j] = 1
                edges.append((i, j))
    
    # Ensure connectivity: add edges if needed
    if len(edges) < n_vars - 1:
        for i in range(n_vars - 1):
            if adj[i, i + 1] == 0:
                adj[i, i + 1] = 1
                edges.append((i, i + 1))
    
    # Random coefficients
    coefs = np.zeros((n_vars, n_vars))
    for i, j in edges:
        coefs[i, j] = rng.choice([-1, 1]) * rng.uniform(0.8, 2.5)
    
    var_names = [f"X{i}" for i in range(n_vars)]
    edge_tuples = [(var_names[i], var_names[j]) for i, j in edges]
    
    # Sample
    def sample(n_samples):
        data = np.zeros((n_samples, n_vars))
        for row in range(n_samples):
            for j in range(n_vars):
                val = rng.normal(0, 0.5)
                for i in range(j):
                    if adj[i, j]:
                        val += coefs[i, j] * data[row, i]
                data[row, j] = val
        return data
    
    return {
        "n_vars": n_vars, "edges": edge_tuples, "var_names": var_names,
        "sample": sample, "seed": seed
    }


def test_active_learner(scm, n_episodes=4, samples_per_ep=40):
    """纯数据驱动的主动学习 (无 physics_prior)"""
    from active_experiment.active_learner import ActiveLearner
    from env.physics_sim import PhysicsEnv
    
    class SynthEnv(PhysicsEnv):
        def __init__(self, scm_dict):
            super().__init__(
                name="synth", variables=scm_dict["var_names"],
                ground_truth_edges=scm_dict["edges"], domain="unknown"
            )
            self._scm = scm_dict
        def observe(self):
            return {}
        def intervene(self, var, value):
            data = self._scm["sample"](1)
            return dict(zip(self.variables, data[0]))
        def variable_info(self):
            return {"name":"synth","domain":"unknown","variables":self.variables,"ground_truth":self.ground_truth_edges}
        def step(self, n):
            return self._scm["sample"](n)
        def experiment(self, intervention, n_samples):
            data = self._scm["sample"](n_samples)
            for var, val in intervention.items():
                idx = self.variables.index(var)
                data[:, idx] = val
            return data
        def reset(self):
            pass
    
    env = SynthEnv(scm)
    
    class NoPriorLearner(ActiveLearner):
        def _physics_prior(self, variables):
            return []
    
    learner = NoPriorLearner(env)
    result = learner.run(n_episodes=n_episodes, samples_per_experiment=samples_per_ep,
                         confidence_threshold=0.6, verbose=False)
    return result


def run():
    np.random.seed(42)
    n_scms = 8
    n_vars = 4
    n_obs = 200
    
    results = []
    
    for i in range(n_scms):
        scm = generate_scm(n_vars, edge_prob=0.4, seed=100 + i)
        truth = scm["edges"]
        var_names = scm["var_names"]
        data_obs = scm["sample"](n_obs)
        
        print(f"\n{'─'*50}")
        print(f"SCM #{i+1}: {n_vars} vars, {len(truth)} edges  seed={100+i}")
        print(f"  Truth: {truth}")
        
        # A) PC
        t0 = time.time()
        pc_edges = pc_algorithm(data_obs, var_names)
        pc_raw = [(e[0], e[1]) for e in pc_edges.edges] if hasattr(pc_edges, 'edges') else []
        f1_a, p_a, r_a, tp_a, fp_a, fn_a = f1_score(pc_raw, truth)
        t_a = time.time() - t0
        print(f"  A) PC       F1={f1_a:.2f} P={p_a:.2f} R={r_a:.2f} tp={tp_a} fp={fp_a} fn={fn_a} ({t_a:.1f}s)")
        
        # B) VOI active learning
        t0 = time.time()
        try:
            al_result = test_active_learner(scm, n_episodes=3, samples_per_ep=30)
            voiedges = al_result["discovered_edges"]
            f1_b, p_b, r_b, tp_b, fp_b, fn_b = f1_score(voiedges, truth)
            t_b = time.time() - t0
            print(f"  B) VOI AL   F1={f1_b:.2f} P={p_b:.2f} R={r_b:.2f} tp={tp_b} fp={fp_b} fn={fn_b} "
                  f"samples={al_result['total_samples']} ({t_b:.1f}s)")
        except Exception as e:
            f1_b, t_b = 0.0, time.time() - t0
            print(f"  B) VOI AL   FAILED: {e}")
        
        # C) GES
        t0 = time.time()
        ges_edges = ges_algorithm(data_obs, var_names)
        f1_c, p_c, r_c, tp_c, fp_c, fn_c = f1_score(ges_edges, truth)
        t_c = time.time() - t0
        print(f"  C) GES      F1={f1_c:.2f} P={p_c:.2f} R={r_c:.2f} tp={tp_c} fp={fp_c} fn={fn_c} ({t_c:.1f}s)")
        
        results.append({
            "scm": i+1, "n_edges": len(truth),
            "pc_f1": f1_a, "pc_t": t_a,
            "voi_f1": f1_b, "voi_t": t_b if 't_b' in dir() else 0,
            "ges_f1": f1_c, "ges_t": t_c,
        })
    
    # Summary
    print(f"\n{'='*55}")
    print("SUMMARY")
    print(f"{'='*55}")
    methods = [
        ("A) PC (200 obs)", "pc_f1", "pc_t"),
        ("B) VOI AL (3ep)", "voi_f1", "voi_t"),
        ("C) GES (200 obs)", "ges_f1", "ges_t"),
    ]
    
    print(f"{'Method':20s} {'Mean F1':>8s} {'Std':>8s} {'Min':>8s} {'Max':>8s} {'Time':>8s}")
    print("-" * 60)
    for label, f1_key, t_key in methods:
        vals = [r[f1_key] for r in results]
        times = [r[t_key] for r in results]
        print(f"{label:20s} {np.mean(vals):8.3f} {np.std(vals):8.3f} {np.min(vals):8.3f} {np.max(vals):8.3f} {np.mean(times):7.2f}s")
    
    # Key deltas
    pc_vals = [r["pc_f1"] for r in results]
    ges_vals = [r["ges_f1"] for r in results]
    voi_vals = [r["voi_f1"] for r in results]
    print(f"\nVOI - PC delta:  {np.mean([v-p for v,p in zip(voi_vals, pc_vals)]):+.3f}")
    print(f"GES - PC delta:  {np.mean([g-p for g,p in zip(ges_vals, pc_vals)]):+.3f}")


if __name__ == "__main__":
    run()
