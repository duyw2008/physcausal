import warnings, numpy as np, time, sys
warnings.filterwarnings("ignore")

sys.path.insert(0, "/home/duyw/physcausal")
from causal.discovery import pc_algorithm, ges_algorithm

def f1_score(pred, truth):
    sp = set(tuple(e) for e in pred); st = set(tuple(e) for e in truth)
    if not sp and not st: return 1.0, 1.0, 1.0, 0, 0, 0
    tp = len(sp & st); fp = len(sp - st); fn = len(st - sp)
    pr = tp/(tp+fp) if tp+fp>0 else 0
    rc = tp/(tp+fn) if tp+fn>0 else 0
    f = 2*pr*rc/(pr+rc) if pr+rc>0 else 0
    return f, pr, rc, tp, fp, fn

def gen_scm(nv, seed):
    rng = np.random.RandomState(seed)
    adj = np.zeros((nv, nv), int); edges = []
    for i in range(nv):
        for j in range(i+1, nv):
            if rng.random() < 0.4: adj[i,j] = 1; edges.append((i,j))
    if len(edges) < nv-1:
        for i in range(nv-1):
            if adj[i,i+1]==0: adj[i,i+1]=1; edges.append((i,i+1))
    coefs = {}
    for i,j in edges: coefs[(i,j)] = rng.choice([-1,1]) * rng.uniform(0.8, 2.5)
    vn = [f"X{k}" for k in range(nv)]
    et = [(vn[i], vn[j]) for i,j in edges]
    def sample(n):
        r = np.random.RandomState(seed+42)
        d = np.zeros((n, nv))
        for row in range(n):
            for j in range(nv):
                v = r.normal(0, 0.5)
                for ii in range(j):
                    if adj[ii,j]: v += coefs[(ii,j)] * d[row,ii]
                d[row,j] = v
        return d
    return {"edges": et, "vn": vn, "sample": sample, "n_edges": len(et)}

n_scms = 10
results = []

for i in range(n_scms):
    scm = gen_scm(3, 100+i)
    data = scm["sample"](200)
    truth = scm["edges"]

    sys.stdout.write(f"SCM #{i+1:2d} ({scm['n_edges']} edges)... "); sys.stdout.flush()
    
    t0 = time.time()
    pc_dag = pc_algorithm(data, scm["vn"])
    pc_raw = [(v,c) for v in pc_dag.variables for c in pc_dag.children(v)]
    f_pc, p_pc, r_pc, tp_pc, fp_pc, fn_pc = f1_score(pc_raw, truth)
    t_pc = time.time() - t0
    sys.stdout.write(f"PC F1={f_pc:.2f} ({t_pc:.1f}s)  "); sys.stdout.flush()

    t0 = time.time()
    ges_dag = ges_algorithm(data, scm["vn"])
    ges_raw = [(v,c) for v in ges_dag.variables for c in ges_dag.children(v)]
    f_ges, p_ges, r_ges, tp_ges, fp_ges, fn_ges = f1_score(ges_raw, truth)
    t_ges = time.time() - t0
    print(f"GES F1={f_ges:.2f} ({t_ges:.1f}s)")
    
    results.append({
        "pc_f1":f_pc, "ges_f1":f_ges,
        "pc_tp":tp_pc,"pc_fp":fp_pc,"pc_fn":fn_pc,
        "ges_tp":tp_ges,"ges_fp":fp_ges,"ges_fn":fn_ges,
    })

print()
print("=" * 60)
print("PRESSURE TEST: Causal Discovery from Unknown SCMs (no prior)")
print("=" * 60)
pc = [r["pc_f1"] for r in results]
ges = [r["ges_f1"] for r in results]
tp_pc = sum(r["pc_tp"] for r in results)
fp_pc = sum(r["pc_fp"] for r in results)
fn_pc = sum(r["pc_fn"] for r in results)
tp_ges = sum(r["ges_tp"] for r in results)
fp_ges = sum(r["ges_fp"] for r in results)
fn_ges = sum(r["ges_fn"] for r in results)
total = tp_pc + fn_pc
print(f"Total true edges across {n_scms} SCMs: {total}")
print(f"")
print(f"{'Method':15s} {'Mean F1':>8s} {'Std':>8s} {'Precision':>10s} {'Recall':>10s} {'tp/fp/fn':>15s}")
print("-" * 60)
pc_p = tp_pc/(tp_pc+fp_pc) if tp_pc+fp_pc>0 else 0
pc_r = tp_pc/(tp_pc+fn_pc) if tp_pc+fn_pc>0 else 0
ges_p = tp_ges/(tp_ges+fp_ges) if tp_ges+fp_ges>0 else 0
ges_r = tp_ges/(tp_ges+fn_ges) if tp_ges+fn_ges>0 else 0
print(f"{'PC bootstrap':15s} {np.mean(pc):8.3f} {np.std(pc):8.3f} {pc_p:10.3f} {pc_r:10.3f} {f'{tp_pc}/{fp_pc}/{fn_pc}':>15s}")
print(f"{'GES':15s} {np.mean(ges):8.3f} {np.std(ges):8.3f} {ges_p:10.3f} {ges_r:10.3f} {f'{tp_ges}/{fp_ges}/{fn_ges}':>15s}")
print(f"")
print(f"GES - PC delta: {np.mean(ges)-np.mean(pc):+.3f}")

# How many perfect recoveries?
pc_perfect = sum(1 for r in results if r["pc_f1"] >= 0.99)
ges_perfect = sum(1 for r in results if r["ges_f1"] >= 0.99)
print(f"Perfect recoveries: PC={pc_perfect}/{n_scms}, GES={ges_perfect}/{n_scms}")
