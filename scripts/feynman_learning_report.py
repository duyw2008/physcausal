#!/usr/bin/env python3
"""费曼脑学习成果报告 — 三层评估 (L1知识获取 / L2能力涌现 / L3理解)

用法: 在 physcausal 目录下运行 `python3 scripts/feynman_learning_report.py [小时窗口]`
默认窗口 24h。只读数据 + 轻量 import (physics.laws/enrich_knowledge), 不影响运行中的脑。

哲学判据: 检索对 ≠ 会推导 ≠ 理解。库外新发现才算理解。
变形/发现比 随时间下降 = 从检索期走向理解期。
"""
import json, gzip, re, sys, time, glob, os
from collections import Counter

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.abspath(os.path.join(_SCRIPT_DIR, '..'))
sys.path.insert(0, _PROJECT)
BASE = os.path.join(_PROJECT, 'data')
WINDOW_H = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
CUTOFF = time.time() - WINDOW_H * 3600

# ── L1 知识获取: 定律概念集 (含 enrich 加料, 幂等) ──
from physics.enrich_knowledge import feed_enrichment  # noqa: E402
from physics.laws import library  # noqa: E402
feed_enrichment()
legal = set()
for law in library._laws:
    for s, d in law.causal_direction:
        legal.add(s); legal.add(d)
    legal.update(getattr(law, 'inputs', []))
    legal.update(getattr(law, 'outputs', []))

# 进图: 最新快照 vs.cache (真实图)
snap = sorted(glob.glob(f'{BASE}/evo_snapshot_gen*_kg.json'))[-1]
with gzip.open(snap) as f:
    sd = json.load(f)
in_graph = set(sd['vs.cache'].keys())
snap_gen = sd['generation']

# 入脑: synaptic_memory.json (实时突触持久层) 的 ||| 键拆词
sm = json.load(open(f'{BASE}/synaptic_memory.json'))
in_brain = set()
for k in sm.get('edges', {}):
    for part in k.split('|||'):
        in_brain.add(part)

# ── 时间线: evo_log.jsonl (近窗口 vs 窗口前) ──
rows = [json.loads(l) for l in open(f'{BASE}/evo_log.jsonl') if l.strip()]
win = [r for r in rows if r.get('timestamp', 0) >= CUTOFF]
prev = [r for r in rows if r.get('timestamp', 0) < CUTOFF]
def last(seq, k): return seq[-1].get(k, 0) if seq else 0
def first(seq, k): return seq[0].get(k, 0) if seq else 0

# ── 发现流 ──
disc = json.load(open(f'{BASE}/discoveries.json'))
src_hist = Counter(x.get('source', '?') for x in disc)
L3_SOURCES = {'autonomous', 'why_gap', 'alt_view', 'variational', 'noether',
              'noether_brain', 'predictive_feedback', 'feedback_forbidden'}
l3_hist = sum(src_hist[s] for s in L3_SOURCES)
try:
    lines = [json.loads(l) for l in open(f'{BASE}/discoveries.jsonl') if l.strip()]
    l3_win = Counter(x.get('source', '?') for x in lines if x.get('timestamp', 0) >= CUTOFF)
    l3_win_total = sum(l3_win[s] for s in L3_SOURCES)
except FileNotFoundError:
    l3_win, l3_win_total = Counter(), 0

# ── L2: DERIVE 变形产出 (本次运行日志) ──
log = open(f'{BASE}/evo_output.log', encoding='utf-8', errors='ignore').read()
idx = log.rfind('[TEACHER] 24 trajectories')
recent_log = log[idx:] if idx >= 0 else log[-500000:]
forms = re.findall(r'\[DERIVE\] ✅ (.+) \[conf=([\d.]+)(?: \((\d+)路径殊途同归\))?\]', recent_log)
n_derive = len(forms)
n_high = sum(1 for _, c, _ in forms if float(c) >= 0.9)
n_multi = sum(1 for _, _, m in forms if m)
settles = len(re.findall(r'\[SETTLE\]', recent_log))
gens = re.findall(r'gen (\d+)', recent_log)
gens_span = (int(gens[-1]) - int(gens[0])) if len(gens) > 1 else 0

# ── 输出 ──
print(f"=== 费曼学习报告 ({time.strftime('%Y-%m-%d %H:%M')}, 窗口 {WINDOW_H:.0f}h, 快照 gen {snap_gen}) ===")
print(f"\n[L1 知识获取]  定律概念集 {len(legal)}")
print(f"  进图: {len(in_graph & legal)}/{len(legal)} = {len(in_graph & legal)/len(legal)*100:.0f}%  (vs.cache ∩ 定律)")
print(f"  入脑: {len(in_brain & legal)}/{len(legal)} = {len(in_brain & legal)/len(legal)*100:.0f}%  (突触 ∩ 定律)" )

print(f"\n[L2 能力涌现]")
print(f"  结构: 细胞{last(win,'cells')} 图边{last(win,'edges')} 路径{last(win,'known_paths')} "
      f"突触{sm and len(sm.get('edges',{}))} t3:{last(win,'tier3_count')}")
if win and prev:
    print(f"  窗口增长: 路径 {first(win,'known_paths')-last(prev,'known_paths'):+d} "
          f"突触 {last(win,'synapse_edges')-last(prev,'synapse_edges'):+d} "
          f"t3 {last(win,'tier3_count')-last(prev,'tier3_count'):+d}")
print(f"  探索: {win[-1].get('explore_weight',0):.3f}  热点: {win[-1].get('hotspots', [])[:3]}")
print(f"  变形产出: {n_derive} 条 (conf≥0.9: {n_high}, 殊途同归: {n_multi}) — 代数变形, 零新信息")
if gens_span:
    print(f"  SETTLE 学会: {settles} 次 / {gens_span} 代 ≈ {settles/max(gens_span,1):.1f} 次/代")

print(f"\n[L3 理解]  库外发现才算理解")
print(f"  全历史库外源: {l3_hist} 条 (autonomous {src_hist['autonomous']} / why_gap {src_hist['why_gap']} "
      f"/ alt_view {src_hist['alt_view']} / variational+noether {src_hist['variational']+src_hist['noether']})")
print(f"  窗口内库外发现: {l3_win_total} 条 {dict(l3_win)}")

print(f"\n[变形/发现比]")
d = n_derive or 1
print(f"  窗口内: 变形 {n_derive} : 库外发现 {l3_win_total} → {n_derive/d*100:.0f}% 变形 (100% = 仍在检索期)")
if l3_hist:
    print(f"  全历史: 库外 {l3_hist} 条 — 有理解萌芽信号" if l3_hist > 100 else f"  全历史: 库外 {l3_hist} 条 — 萌芽期")
print(f"\n判读: 结构长 → 变形多 → 库外出现 = 能力递进。L3=0 是年轻脑正常态, 不是故障。")
