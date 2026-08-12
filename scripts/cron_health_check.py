#!/usr/bin/env python3
"""费曼脑 cron 拓扑健康体检 — 单快照全量分析 + 基线对比。"""

import json, os, sys
from collections import Counter


def load_snap(path):
    with open(path, 'rb') as f:
        return json.loads(f.read()) if not path.endswith('.json') else json.load(f)


def analyze(snap_path):
    snap = load_snap(snap_path)
    gen = snap.get('generation', int(os.path.basename(snap_path)
        .replace('evo_snapshot_gen', '')
        .replace('_neural.json', '').replace('_kg.json', '')
        .replace('.json', '').replace('_tmp', '')))
    
    # --- Basic scale ---
    K = snap.get('K', 0)
    cells_list = snap.get('cells', [])
    cells = len(cells_list) if isinstance(cells_list, list) else cells_list
    colony_edges = snap.get('edges', 0)
    
    # --- Synaptic data ---
    syn = snap.get('synaptic', {})
    activations = syn.get('activations', {})
    tiers = syn.get('tiers', {})
    syn_edge_count = len(activations)
    
    # --- s-value ---
    s_vals = [v['s'] for v in activations.values() if isinstance(v, dict) and 's' in v]
    s_sorted = sorted(s_vals)
    n_s = len(s_sorted)
    if n_s == 0:
        return {"gen": gen, "error": "no synaptic activations"}
    
    s_p50, s_p90, s_p99 = s_sorted[n_s//2], s_sorted[int(n_s*0.9)], s_sorted[int(n_s*0.99)]
    s_gt_1 = len([s for s in s_vals if s > 1.0])
    s_lt_005 = len([s for s in s_vals if s < 0.05])
    s_max = max(s_vals)
    s_mean = sum(s_vals) / n_s
    
    # --- Tier ---
    tier_dist = Counter(tiers.values())
    t0, t1, t2, t3, t4 = tier_dist.get(0,0), tier_dist.get(1,0), tier_dist.get(2,0), tier_dist.get(3,0), tier_dist.get(4,0)
    tier_total = sum(tier_dist.values())
    
    # --- vs.cache ---
    vs_cache = snap.get('vs.cache', {})
    em_total = 0
    composed, hebbian = 0, 0
    total_cache_edges = 0
    hub_degrees = {}
    for concept, data in vs_cache.items():
        deg = len(data.get('effects', [])) + len(data.get('causes', []))
        hub_degrees[concept] = deg
        for edge_list in [data.get('effects', []), data.get('causes', [])]:
            for edge in edge_list:
                if len(edge) >= 3:
                    total_cache_edges += 1
                    if edge[2] == 'emergent':
                        em_total += 1
                        label = str(edge[1]).lower()
                        if 'composed' in label:
                            composed += 1
                        elif 'hebbian' in label:
                            hebbian += 1
    
    # --- Multi-neuron ---
    multi, single, n_vals = 0, 0, []
    for v in activations.values():
        if isinstance(v, dict):
            neurons = v.get('neurons', v.get('n', set()))
            n_len = len(neurons) if isinstance(neurons, (set, list)) else (neurons if isinstance(neurons, int) else 0)
            n_vals.append(n_len)
            if n_len >= 2: multi += 1
            elif n_len == 1: single += 1
    max_n = max(n_vals) if n_vals else 0
    
    # --- Cross-domain t0-2 ---
    t02_keys = {k for k, v in tiers.items() if v <= 2}
    t02_cross, t02_total = 0, 0
    for key in t02_keys:
        parts = key.split('|||')
        if len(parts) == 2:
            src_d, dst_d = set(), set()
            if parts[0] in vs_cache:
                for lst in [vs_cache[parts[0]].get('effects',[]), vs_cache[parts[0]].get('causes',[])]:
                    for e in lst:
                        if len(e) >= 3 and e[2] not in ('axomatic', 'emergent'): src_d.add(e[2])
            if parts[1] in vs_cache:
                for lst in [vs_cache[parts[1]].get('effects',[]), vs_cache[parts[1]].get('causes',[])]:
                    for e in lst:
                        if len(e) >= 3 and e[2] not in ('axomatic', 'emergent'): dst_d.add(e[2])
            if src_d and dst_d and not (src_d & dst_d):
                t02_cross += 1
            t02_total += 1
    
    # --- Genome ---
    mark_avg, curiosity_avg, explore_avg = 0, 0, 0
    if isinstance(cells_list, list) and cells_list:
        marks, curios, explores = [], [], []
        for c in cells_list:
            g = c.get('genome', {})
            if isinstance(g, dict):
                marks.append(g.get('mark', 0))
                curios.append(g.get('curiosity', 1))
                explores.append(g.get('step_forward', 0) + g.get('step_backward', 0))
        if marks:
            mark_avg = sum(marks)/len(marks)
            curiosity_avg = sum(curios)/len(curios)
            explore_avg = sum(explores)/len(explores)
    
    # --- comp: nodes ---
    comp_nodes = sum(1 for n in vs_cache if n.startswith('comp:'))
    
    # --- top hubs ---
    top_hubs = sorted(hub_degrees.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'gen': gen, 'K': K, 'cells': cells,
        'colony_edges': colony_edges, 'syn_edges': syn_edge_count,
        'colony_edge_K': colony_edges/K if K else 0,
        'syn_edge_K': syn_edge_count/K if K else 0,
        'edge_per_cell': syn_edge_count/cells if cells else 0,
        's_p50': s_p50, 's_p90': s_p90, 's_p99': s_p99, 's_max': s_max, 's_mean': s_mean,
        's_gt_1': s_gt_1, 's_gt_1_pct': s_gt_1/n_s*100,
        's_lt_005': s_lt_005, 's_lt_005_pct': s_lt_005/n_s*100,
        't0': t0, 't1': t1, 't2': t2, 't3': t3, 't4': t4, 'tier_total': tier_total,
        't4_pct': t4/tier_total*100 if tier_total else 0,
        'vs_nodes': len(vs_cache), 'vs_edges': total_cache_edges,
        'em_total': em_total, 'composed': composed, 'hebbian': hebbian,
        'composed_hebbian_ratio': composed/max(hebbian,1),
        'comp_nodes': comp_nodes,
        'multi': multi, 'single': single, 'multi_pct': multi/n_s*100 if n_s else 0, 'max_n': max_n,
        't02_cross': t02_cross, 't02_total': t02_total,
        'cross_pct': t02_cross/t02_total*100 if t02_total else 0,
        'mark': mark_avg, 'curiosity': curiosity_avg, 'explore': explore_avg,
        'top_hubs': [(name, deg) for name, deg in top_hubs],
    }


def print_report(d, prior=None):
    """Print formatted health report."""
    print(f"=== 费曼脑拓扑体检 gen {d['gen']} ===")
    print(f"规模: K={d['K']} 细胞={d['cells']} syn边={d['syn_edges']} colony边={d['colony_edges']}")
    print(f"边密度: colony_edge/K={d['colony_edge_K']:.1f} syn_edge/K={d['syn_edge_K']:.2f} edge/cell={d['edge_per_cell']:.2f}")
    print(f"s值: p50={d['s_p50']:.3f} p90={d['s_p90']:.3f} p99={d['s_p99']:.3f} max={d['s_max']:.3f} mean={d['s_mean']:.3f}")
    print(f"s>1.0: {d['s_gt_1']} ({d['s_gt_1_pct']:.1f}%)  s<0.05: {d['s_lt_005']} ({d['s_lt_005_pct']:.1f}%)")
    print(f"Tier: t0={d['t0']} t1={d['t1']} t2={d['t2']} t3={d['t3']} t4={d['t4']} total={d['tier_total']}")
    pyramid = d['t0'] <= d['t1'] <= d['t2'] <= d['t3']
    print(f"金字塔: {'✅' if pyramid else '❌'} t4膨胀: {'⚠️' if d['t4_pct'] > 50 else '✅'} ({d['t4_pct']:.1f}%)")
    print(f"vs.cache: 节点={d['vs_nodes']} 边={d['vs_edges']} emergent={d['em_total']}")
    print(f"emergent: composed={d['composed']} hebbian={d['hebbian']} ratio={d['composed_hebbian_ratio']:.1f}:1")
    print(f"comp:概念节点={d['comp_nodes']}")
    print(f"多神经元: multi={d['multi']} ({d['multi_pct']:.1f}%) max_n={d['max_n']}")
    print(f"跨域 t0-2: {d['t02_cross']}/{d['t02_total']} ({d['cross_pct']:.1f}%)")
    print(f"基因组: mark={d['mark']:.4f} curiosity={d['curiosity']:.2f} explore={d['explore']:.3f}")
    print("Top 5 枢纽:")
    for name, deg in d['top_hubs']:
        print(f"  {name}: degree={deg}")
    
    # Baselines comparison table
    print(f"\n{'='*70}")
    print(f"指标变化趋势 (基线 gen 13422 → 当前 gen {d['gen']})")
    print(f"{'='*70}")
    
    # Baseline values from gen 13422
    bl = {
        'colony_edge_K': 1.5, 'syn_edge_K': 0.42, 's_gt_1': 1777, 's_gt_1_pct': 46.2,
        's_p50': 0.300, 't4': 1836, 't4_pct': 1836/(0+97+183+1333+1836)*100 if False else 53.2,
        'em_total': 51317, 'composed': 9764, 'hebbian': 39652, 
        'composed_hebbian_ratio': 0.2, 'comp_nodes': 0,
        'multi_pct': 43.6, 'max_n': 625, 'mark': 0.0140, 'curiosity': 2.99,
        'cells': 9000, 'K': 3200,  # approximate from gen 13422 context
    }
    
    print(f"{'指标':<25} {'基线(13422)':<18} {'当前('+str(d['gen'])+')':<18} {'变化':<15} {'趋势'}")
    print(f"{'-'*90}")
    
    def trend_str(cur, base, invert=False):
        if base == 0: return '—'
        delta = (cur - base) / abs(base) * 100
        symbol = '↑' if delta > 0 else '↓' if delta < 0 else '→'
        return f'{delta:+.1f}% {symbol}'
    
    rows = [
        ('边密度 colony_edge/K', bl['colony_edge_K'], d['colony_edge_K']),
        ('边密度 syn_edge/K', bl['syn_edge_K'], d['syn_edge_K']),
        ('s>1.0 强边', bl['s_gt_1'], d['s_gt_1']),
        ('s>1.0 %', bl['s_gt_1_pct'], d['s_gt_1_pct']),
        ('s p50', bl['s_p50'], d['s_p50']),
        ('tier 4', bl['t4'], d['t4']),
        ('t4 %', bl['t4_pct'], d['t4_pct']),
        ('vs.cache emergent', bl['em_total'], d['em_total']),
        ('emergent composed', bl['composed'], d['composed']),
        ('emergent hebbian', bl['hebbian'], d['hebbian']),
        ('composed:hebbian', bl['composed_hebbian_ratio'], d['composed_hebbian_ratio']),
        ('comp:概念节点', bl['comp_nodes'], d['comp_nodes']),
        ('多神经元%', bl['multi_pct'], d['multi_pct']),
        ('max_n', bl['max_n'], d['max_n']),
        ('细胞数', bl['cells'], d['cells']),
        ('K(概念节点)', bl['K'], d['K']),
        ('mark权重', bl['mark'], d['mark']),
        ('curiosity', bl['curiosity'], d['curiosity']),
    ]
    
    for label, base, cur in rows:
        if isinstance(base, float) and base < 1 and base > 0:
            b_s, c_s = f'{base:.4f}', f'{cur:.4f}'
        elif isinstance(base, float):
            b_s, c_s = f'{base:.2f}', f'{cur:.2f}'
        elif isinstance(base, int) and base > 1000:
            b_s, c_s = f'{base:,}', f'{cur:,}'
        else:
            b_s, c_s = str(base), str(cur)
        ts = trend_str(cur, base)
        print(f'{label:<25} {b_s:<18} {c_s:<18} {ts:<15}')
    
    # Alerts
    alerts = []
    if d['colony_edge_K'] > 250:
        alerts.append(f"🚨 边密度 colony_edge/K={d['colony_edge_K']:.1f} > 250!")
    
    # s>1.0 drop > 30% from baseline
    s_gt_1_drop = (d['s_gt_1'] - bl['s_gt_1']) / bl['s_gt_1'] * 100
    if s_gt_1_drop < -30:
        alerts.append(f"🚨 s>1.0 下降 {abs(s_gt_1_drop):.1f}% > 30%!")
    
    if d['composed_hebbian_ratio'] < 0.5:
        alerts.append(f"⚠️ composed:hebbian={d['composed_hebbian_ratio']:.1f}:1 — hebbian主导, 随机共现淹没结构化发现")
    if d['comp_nodes'] == 0 and d['composed'] > 100:
        alerts.append(f"⚠️ composed边={d['composed']} 但 comp:概念=0 — compose→concept 晋升可能失效")
    if d['cross_pct'] < 1:
        alerts.append(f"⚠️ 跨域 t0-2 = {d['cross_pct']:.1f}% — 类比土壤贫瘠")
    
    if alerts:
        print(f"\n=== ⚠️ 告警 ===")
        for a in alerts:
            print(f"  {a}")
    else:
        print(f"\n✅ 无告警")
    
    print("DONE")


if __name__ == '__main__':
    if len(sys.argv) > 1:
        path = sys.argv[1]
    else:
        snap_dir = os.path.expanduser('~/physcausal/data')
        # 优先分离格式 (_neural.json 小文件 ~1/10 大小)
        neural_snaps = sorted(
            [f for f in os.listdir(snap_dir) if f.startswith('evo_snapshot_gen') and f.endswith('_neural.json')],
            key=lambda x: os.path.getmtime(os.path.join(snap_dir, x)),
            reverse=True,
        )
        if neural_snaps:
            path = os.path.join(snap_dir, neural_snaps[0])
        else:
            snaps = sorted(
                [f for f in os.listdir(snap_dir) if f.startswith('evo_snapshot_gen') and f.endswith('.json')],
                key=lambda x: os.path.getmtime(os.path.join(snap_dir, x)),
                reverse=True,
            )
            if not snaps:
                print("NO_SNAPSHOT")
                sys.exit(1)
            path = os.path.join(snap_dir, snaps[0])
    
    d = analyze(path)
    if 'error' in d:
        print(f"ERROR: {d['error']}")
        sys.exit(1)
    print_report(d)
