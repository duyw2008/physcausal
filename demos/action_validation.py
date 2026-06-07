#!/usr/bin/env python3
"""
行动层验证 v2: 轻量版 (不用 bootstrap)

生成随机 3-4 变量 SCM (无物理定律覆盖),
对比:
  1. PC 纯观测 (200 samples, 0 干预)
  2. VOI 主动学习 (4 episodes)
  3. RL Q-Learning (15 episodes)

用原始 PC/GES 算法, 不经过 StructuralPosterior bootstrap。
"""

import sys, os, warnings, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore")

from causal.discovery import pc_algorithm, ges_algorithm
from env.physics_sim import PhysicsEnv


def edges_from_dag(dag):
    return [(v, c) for v in dag.variables for c in dag.children(v)]


def f1(pred, truth):
    sp = set(tuple(e) for e in pred)
    st = set(tuple(e) for e in truth)
    if not sp and not st: return 1.0
    tp = len(sp & st); fp = len(sp - st); fn = len(st - sp)
    p = tp/(tp+fp) if tp+fp>0 else 0; r = tp/(tp+fn) if tp+fn>0 else 0
    return 2*p*r/(p+r) if p+r>0 else 0


def gen_scm(n_vars, seed):
    rng = np.random.RandomState(seed)
    adj = np.zeros((n_vars, n_vars), int); edges = []
    for i in range(n_vars):
        for j in range(i+1, n_vars):
            if rng.random() < 0.4: adj[i,j]=1; edges.append((i,j))
    if len(edges) < n_vars-1:
        for i in range(n_vars-1):
            if adj[i,i+1]==0: adj[i,i+1]=1; edges.append((i,i+1))
    coefs = {}
    for i,j in edges: coefs[(i,j)] = rng.choice([-1,1]) * rng.uniform(0.8, 2.5)
    vn = [f"V{k}" for k in range(n_vars)]
    et = [(vn[i], vn[j]) for i,j in edges]
    def sample(n):
        r = np.random.RandomState(seed+42)
        d = np.zeros((n, n_vars))
        for row in range(n):
            for j in range(n_vars):
                v = r.normal(0, 0.5)
                for ii in range(j):
                    if adj[ii,j]: v += coefs[(ii,j)] * d[row,ii]
                d[row,j] = v
        return d
    return {"edges": et, "vn": vn, "sample": sample, "n_edges": len(et)}


def pc_baseline(scm, n_obs=200):
    data = scm["sample"](n_obs)
    dag = pc_algorithm(data, scm["vn"])
    return f1(edges_from_dag(dag), scm["edges"])


def ges_baseline(scm, n_obs=200):
    data = scm["sample"](n_obs)
    dag = ges_algorithm(data, scm["vn"])
    return f1(edges_from_dag(dag), scm["edges"])


def voi_active(scm, n_ep=4, samples_per_ep=30):
    """VOI 主动学习 (简化版: 不用 bootstrap, 按相关性选干预)"""
    vn = scm["vn"]; nv = len(vn)
    data = [scm["sample"](samples_per_ep)]
    
    for ep in range(n_ep):
        all_d = np.vstack(data)
        corr = np.abs(np.corrcoef(all_d.T))
        # 选与其他变量平均相关最低的变量做干预 (最不确定的)
        mean_corr = corr.sum(axis=1)
        var_idx = np.argmin(mean_corr)
        
        new_d = scm["sample"](samples_per_ep)
        new_d[:, var_idx] = np.random.uniform(-2, 2, samples_per_ep)
        data.append(new_d)
    
    final = np.vstack(data)
    dag = pc_algorithm(final, vn)
    return f1(edges_from_dag(dag), scm["edges"]), len(data) * samples_per_ep


def run():
    np.random.seed(42)
    
    for nv in [3, 4]:
        print(f"\n{'='*50}")
        print(f"  {nv} vars, 8 SCMs, no physics_prior")
        print(f"{'='*50}")
        
        pc_accs, ges_accs, voi_accs = [], [], []
        
        for i in range(8):
            scm = gen_scm(nv, 300 + i)
            truth = scm["edges"]
            
            f_pc = pc_baseline(scm)
            f_ges = ges_baseline(scm)
            f_voi, samp = voi_active(scm)
            
            print(f"  SCM{i+1} ({scm['n_edges']}e): PC={f_pc:.2f} GES={f_ges:.2f} VOI={f_voi:.2f}")
            pc_accs.append(f_pc); ges_accs.append(f_ges); voi_accs.append(f_voi)
        
        print(f"  {'─'*40}")
        for label, accs in [("PC (200 obs)", pc_accs), ("GES (200 obs)", ges_accs), ("VOI AL (4ep)", voi_accs)]:
            print(f"  {label:15s} mean={np.mean(accs):.3f} std={np.std(accs):.3f} min={np.min(accs):.3f} max={np.max(accs):.3f}")


if __name__ == "__main__":
    run()
