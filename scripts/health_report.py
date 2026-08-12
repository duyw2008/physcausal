#!/usr/bin/env python3
"""
费曼脑能力评级 — 10维认知仪表盘
用法: python3 scripts/health_report.py [snapshot_path]
"""
import json, glob, sys
from collections import Counter, defaultdict, deque

def load(snap_path):
    with open(snap_path) as f:
        return json.load(f)

def tier_pyramid(tiers):
    """tier 金字塔分布"""
    dist = Counter(tiers.values())
    total = sum(dist.values())
    return {t: dist.get(t, 0) for t in range(5)}, total

def noise_rate(tiers, acts):
    """各 tier hyp/abs/碎片/自环 占比"""
    noise = {t: 0 for t in range(5)}
    counts = {t: 0 for t in range(5)}
    for k, tier in tiers.items():
        counts[tier] = counts.get(tier, 0) + 1
        parts = k.split('|||')
        s, d = parts if len(parts) == 2 else ('', '')
        if s.startswith(('hyp:', 'abs:')) or d.startswith(('hyp:', 'abs:')):
            noise[tier] = noise.get(tier, 0) + 1
        elif s == d:
            noise[tier] = noise.get(tier, 0) + 1
        elif len(s) > 35 and s.count('_') > 5:
            noise[tier] = noise.get(tier, 0) + 1
        elif len(d) > 35 and d.count('_') > 5:
            noise[tier] = noise.get(tier, 0) + 1
    return {t: (noise[t], counts[t], noise[t]/counts[t]*100 if counts[t] else 0) for t in range(5) if counts[t] > 0}

def multi_neuron_stats(tiers, acts):
    """multi-neuron 率和 max_n"""
    multi = 0; total = 0; max_n = 0; n_vals = []
    for k, tier in tiers.items():
        if tier > 2: continue
        total += 1
        a = acts.get(k, {})
        n = a.get('n', 0)
        nn = len(n) if isinstance(n, (set, list)) else (n if isinstance(n, int) else 0)
        n_vals.append(nn)
        if nn >= 2: multi += 1
        if nn > max_n: max_n = nn
    n_vals.sort()
    p90_n = n_vals[int(len(n_vals)*0.9)] if n_vals else 0
    return multi, total, max_n, p90_n

def s_value_stats(tiers, acts):
    """s 值分布"""
    s_by_tier = defaultdict(list)
    for k, tier in tiers.items():
        a = acts.get(k, {})
        sv = a.get('s', 0)
        s_by_tier[tier].append(sv)
    result = {}
    for t in sorted(s_by_tier):
        vals = sorted(s_by_tier[t])
        if vals:
            result[t] = {
                'p50': vals[len(vals)//2],
                'p90': vals[int(len(vals)*0.9)] if len(vals) > 1 else vals[0],
                'max': max(vals),
            }
    return result

def cross_domain_stats(tiers, cache):
    """跨域连接 + 桥节点"""
    node_d = {}
    for nid, nd in cache.items():
        doms = set()
        for e in nd.get('effects', []):
            if len(e) > 2 and e[2] not in ('axomatic', 'emergent'): doms.add(e[2])
        for c in nd.get('causes', []):
            if len(c) > 2 and c[2] not in ('axomatic', 'emergent'): doms.add(c[2])
        if doms: node_d[nid] = doms
    
    cross = 0; unknown = 0; total = 0
    bridge_nodes = 0
    for k, tier in tiers.items():
        if tier > 2: continue
        total += 1
        parts = k.split('|||')
        s, d = parts if len(parts) == 2 else ('?', '?')
        ds = node_d.get(s); dd = node_d.get(d)
        if ds is None or dd is None:
            unknown += 1
        elif not (ds & dd):
            cross += 1
    
    for nid, doms in node_d.items():
        if len(doms) >= 3:
            bridge_nodes += 1
    
    return cross, total, unknown, bridge_nodes, len(node_d)

def hub_stats(tiers):
    """枢纽集中度"""
    indeg = Counter(); outdeg = Counter()
    for k, tier in tiers.items():
        if tier > 2: continue
        parts = k.split('|||')
        s, d = parts if len(parts) == 2 else ('?', '?')
        outdeg[s] += 1; indeg[d] += 1
    
    top_in = indeg.most_common(5)
    top_out = outdeg.most_common(5)
    return top_in, top_out, indeg, outdeg

def depth_stats(tiers):
    """深度层级: 迭代BFS从无入边节点开始"""
    indeg = Counter()
    edges = defaultdict(list)
    for k, tier in tiers.items():
        if tier > 2: continue
        parts = k.split('|||')
        s, d = parts if len(parts) == 2 else ('?', '?')
        indeg[d] += 1
        edges[s].append(d)
    
    # BFS from roots
    roots = [n for n in set(list(indeg.keys()) + list(edges.keys())) if indeg[n] == 0]
    if not roots:
        roots = list(edges.keys())[:10]
    
    depth = {}
    from collections import deque
    for r in roots[:50]:
        q = deque([(r, 0)])
        visited = {r}
        while q:
            n, d = q.popleft()
            depth[n] = max(depth.get(n, 0), d)
            for nb in edges.get(n, []):
                if nb not in visited and d < 10:
                    visited.add(nb)
                    q.append((nb, d+1))
    
    if depth:
        depths = sorted(depth.values())
        return max(depths), depths[int(len(depths)*0.9)] if len(depths) > 1 else max(depths), len(depth)
    return 0, 0, 0

def promote_rate(tiers_prev, tiers_curr):
    """晋升速率: t3→t2, t2→t1"""
    t3_to_t2 = 0; t2_to_t1 = 0
    for k, t_curr in tiers_curr.items():
        t_prev = tiers_prev.get(k, 4)
        if t_prev == 3 and t_curr == 2: t3_to_t2 += 1
        if t_prev == 2 and t_curr == 1: t2_to_t1 += 1
    return t2_to_t1, t3_to_t2

def comp_hyp_stats(tiers, acts, cache):
    """compose/hyp 统计: comp概念数 + hyp边中多神经元存活数"""
    comp_count = sum(1 for n in cache if n.startswith('comp:'))
    # 有 hyp: 节点的边中，多神经元边数 (存活标志)
    hyp_total = 0; hyp_surviving = 0
    for k, tier in tiers.items():
        parts = k.split('|||')
        s, d = parts if len(parts) == 2 else ('', '')
        if not (s.startswith('hyp:') or d.startswith('hyp:')):
            continue
        hyp_total += 1
        a = acts.get(k, {})
        n = a.get('n', 0)
        nn = len(n) if isinstance(n, (set, list)) else (n if isinstance(n, int) else 0)
        if nn >= 2:
            hyp_surviving += 1
    return comp_count, hyp_total, hyp_surviving

def rate_grade(value, thresholds):
    """评级: thresholds = [(A_min, B_min, C_min)]"""
    if value >= thresholds[0]: return 'A'
    if value >= thresholds[1]: return 'B'
    if value >= thresholds[2]: return 'C'
    return 'D'

# ═══════ 主报告 ═══════
def report(snap_path, prev_snap_path=None):
    snap = load(snap_path)
    tiers = snap['synaptic']['tiers']
    acts = snap['synaptic']['activations']
    cache = snap.get('vs.cache', {})
    gen = snap.get('generation', '?')
    
    prev_tiers = {}
    if prev_snap_path:
        prev_tiers = load(prev_snap_path)['synaptic']['tiers']
    
    # ── 结构 ──
    pyramid, total_edges = tier_pyramid(tiers)
    noise = noise_rate(tiers, acts)
    t2_to_t1, t3_to_t2 = promote_rate(prev_tiers, tiers) if prev_tiers else (0, 0)
    
    # ── 共识 ──
    multi, t01_total, max_n, p90_n = multi_neuron_stats(tiers, acts)
    multi_pct = multi / t01_total * 100 if t01_total else 0
    
    # ── 拓扑 ──
    cross, cross_total, cross_unk, bridge_nodes, node_count = cross_domain_stats(tiers, cache)
    cross_pct = cross / cross_total * 100 if cross_total else 0
    top_in, top_out, indeg, outdeg = hub_stats(tiers)
    max_depth, p90_depth, depth_nodes = depth_stats(tiers)
    
    # ── s值 ──
    s_stats = s_value_stats(tiers, acts)
    
    # ── compose/hyp ──
    comp_count, hyp_total, hyp_surviving = comp_hyp_stats(tiers, acts, cache)
    
    # ── 噪声整体 ──
    t012_total = pyramid[0] + pyramid[1] + pyramid[2]
    t012_noise = sum(noise[t][0] for t in (0,1,2) if t in noise)
    t012_noise_pct = t012_noise / t012_total * 100 if t012_total else 0
    
    t3_total = pyramid[3]
    t3_noise = noise.get(3, (0,0,0))[0]
    t3_noise_pct = t3_noise / t3_total * 100 if t3_total else 0
    
    # ═══════ 评级 ═══════
    grades = {}
    
    # 1. 联想: t3 cross-domain + 桥节点活跃度
    cross_grade = rate_grade(cross_pct, [10, 5, 1])
    # 2. 想象: compose概念 + hyp边多神经元存活
    hyp_survival_pct = hyp_surviving / hyp_total * 100 if hyp_total else 0
    imagination_score = comp_count * 2 + hyp_surviving
    imagination_grade = rate_grade(imagination_score, [30, 10, 3])
    
    # 3. 推理: 可追溯至 action 的节点比例 (BFS反向沿causes)
    action_nodes = {n for n in cache if 'action' in n.lower()}
    traceable = 0; traceable_total = len(cache)
    if action_nodes:
        rev_graph = defaultdict(list)
        for nid, nd in cache.items():
            for e in nd.get('effects', []):
                if len(e) > 1: rev_graph[e[1]].append(nid)
        all_traceable = set()
        for root in action_nodes:
            if root not in rev_graph and root not in cache:
                continue
            visited = {root}
            q = deque([root])
            while q:
                n = q.popleft()
                for nb in rev_graph.get(n, []):
                    if nb not in visited and len(all_traceable) < 2000:
                        visited.add(nb)
                        q.append(nb)
            all_traceable |= visited
        traceable = len(all_traceable)
    traceable_pct = traceable / traceable_total * 100 if traceable_total else 0
    reason_grade = rate_grade(traceable_pct, [15, 5, 1])
    
    # 4. 对比: INTERVENE 活跃度 (用晋升增量 + tier变化近似)
    compare_grade = rate_grade(t2_to_t1 + t3_to_t2, [15, 5, 1])
    
    # 关联: 跨域比例 + 桥节点
    connect_grade = rate_grade(cross_pct, [5, 2, 0.5])
    
    # 验证: 金字塔形 + 噪声率
    is_pyramid = pyramid[4] >= pyramid[3] >= pyramid[2] >= pyramid[1]
    verify_grade = 'A' if is_pyramid and t012_noise_pct < 5 else \
                   'B' if t012_noise_pct < 15 else \
                   'C' if t012_noise_pct < 30 else 'D'
    
    # 信念: multi-neuron + s值
    s_t1 = s_stats.get(1, {}).get('p50', 0)
    belief_grade = rate_grade(multi_pct, [90, 80, 50])
    
    # 好奇: 新节点发现 (t4 大小)
    curiosity_grade = rate_grade(pyramid[4], [2000, 1000, 300])
    
    # 记忆: 跨快照存活率 (简化: 用一致性近似)
    memory_grade = rate_grade(max_n, [500, 200, 50])
    
    # 抽象: 深度 + 枢纽
    hub_ratio = sum(x[1] for x in top_out[:5]) / sum(outdeg.values()) * 100 if outdeg else 0
    abstract_grade = rate_grade(max_depth * 10 + hub_ratio, [50, 30, 15])
    
    # ═══════ 输出 ═══════
    print(f"══════════ 费曼脑能力评级 gen {gen} ═══════════")
    print(f"联想 {cross_grade}  │ 想象 {imagination_grade}  │ 推理 {reason_grade}  │ 对比 {compare_grade}  │ 关联 {connect_grade}")
    print(f"验证 {verify_grade}  │ 信念 {belief_grade}   │ 好奇 {curiosity_grade}  │ 记忆 {memory_grade}  │ 抽象 {abstract_grade}")
    
    grade_counts = Counter([cross_grade, imagination_grade, reason_grade, compare_grade,
                           connect_grade, verify_grade, belief_grade, curiosity_grade,
                           memory_grade, abstract_grade])
    score = grade_counts['A']*4 + grade_counts['B']*3 + grade_counts['C']*2 + grade_counts['D']*1
    overall = 'A' if score >= 35 else 'B' if score >= 28 else 'C' if score >= 20 else 'D'
    print(f"────────────────────────────────────────────────")
    print(f"综合: {overall}  ({grade_counts['A']}A {grade_counts['B']}B {grade_counts['C']}C {grade_counts['D']}D)  score={score}/40")
    print(f"────────────────────────────────────────────────")
    
    # 数据明细
    print(f"\n═══ 结构 ═══")
    print(f"tier: 0={pyramid[0]} 1={pyramid[1]} 2={pyramid[2]} 3={pyramid[3]} 4={pyramid[4]} 总={total_edges}")
    print(f"金字塔: {'✅' if is_pyramid else '⚠️ 逆金字塔'}")
    print(f"晋升: t2→t1 +{t2_to_t1}  t3→t2 +{t3_to_t2}")
    print(f"噪声: t0-2={t012_noise_pct:.0f}%  t3={t3_noise_pct:.0f}%")
    
    print(f"\n═══ 共识 ═══")
    print(f"multi-neuron: {multi}/{t01_total} ({multi_pct:.0f}%)  max_n={max_n}  p90_n={p90_n}")
    for t in sorted(s_stats):
        st = s_stats[t]
        print(f"s值 t{t}: p50={st['p50']:.2f} p90={st['p90']:.2f} max={st['max']:.2f}")
    
    print(f"\n═══ 拓扑 ═══")
    print(f"跨域: {cross}/{cross_total} ({cross_pct:.1f}%) 桥节点(≥3域)={bridge_nodes}  节点总数={node_count}")
    print(f"深度: max={max_depth} p90={p90_depth} nodes={depth_nodes}")
    print(f"枢纽入度: {' '.join(f'{n}({c})' for n,c in top_in)}")
    print(f"枢纽出度: {' '.join(f'{n}({c})' for n,c in top_out)}")
    
    print(f"\n═══ 涌现 ═══")
    print(f"compose概念: {comp_count}  hyp边: {hyp_total}(存活{hyp_surviving} {hyp_survival_pct:.0f}%)")
    print(f"可追溯至action: {traceable}/{traceable_total}节点 ({traceable_pct:.1f}%)")
    
    # 短板提示
    print(f"\n═══ 诊断 ═══")
    issues = []
    if cross_grade in ('C', 'D'): issues.append("跨域连接极低 → 类比土壤贫瘠")
    if reason_grade in ('C', 'D'): issues.append("因果深度不足 → WHY链未形成")
    if imagination_grade in ('C', 'D'): issues.append("compose/hyp产出少 → 想象力待激活")
    if verify_grade in ('C', 'D'): issues.append("噪声率高或金字塔逆 → 质量门需加强")
    if t012_noise_pct > 5: issues.append(f"t0-2噪声={t012_noise_pct:.0f}% → hyp/abs碎片混入")
    if cross_pct < 1: issues.append("跨域率<1% → '只给容量'已到位，等脑自己走")
    if not issues:
        print("无显著短板 ✓")
    else:
        for i in issues:
            print(f"  ⚠ {i}")

if __name__ == '__main__':
    # 优先读神经层快照 (小文件, ~1/10 大小), 不指定路径时自动发现
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        # 自动发现: 优先分离格式 (_neural.json), 回退统一格式
        neural_snaps = sorted(glob.glob('/home/duyw/physcausal/data/evo_snapshot_gen*_neural.json'))
        if neural_snaps:
            target = neural_snaps[-1]
        else:
            snaps = sorted(glob.glob('/home/duyw/physcausal/data/evo_snapshot_gen*.json'))
            target = snaps[-1] if snaps else None

    if target is None:
        print("未找到快照文件")
        sys.exit(1)

    # 找上一份快照 (优先分离格式)
    all_snaps = sorted(glob.glob('/home/duyw/physcausal/data/evo_snapshot_gen*_neural.json'))
    if not all_snaps:
        all_snaps = sorted(glob.glob('/home/duyw/physcausal/data/evo_snapshot_gen*.json'))
    try:
        idx = all_snaps.index(target)
        prev = all_snaps[idx - 1] if idx > 0 else None
    except ValueError:
        prev = None
    report(target, prev)
