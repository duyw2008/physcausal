#!/usr/bin/env python3
"""evo_log 突触/事件轨迹分析"""
import json, os, sys

DATA = os.path.expanduser('~/Agent/physcausal/data')

rows = []
with open(os.path.join(DATA, 'evo_log.jsonl')) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass

print('evo_log rows:', len(rows))

# 收集所有 key 统计哪些字段含突触信息
from collections import Counter
keycount = Counter()
for r in rows:
    for k in r:
        keycount[k] += 1
print('keys:', dict(keycount.most_common(20)))

# 尝试找突触/事件字段
syn_key = None
for cand in ('synapses', 'syn', 'synapse_act', 'total_synapses', 'n_syn', 'synaptic', 'synapse_edges'):
    if cand in keycount:
        syn_key = cand
        break
ev_key = None
for cand in ('event', 'type', 'kind', 'tag'):
    if cand in keycount:
        ev_key = cand
        break
print('syn_key:', syn_key, 'ev_key:', ev_key)

if syn_key:
    gen_key = 'generation' if 'generation' in keycount else 'gen'
    seq = [(r.get(gen_key), r.get(syn_key), r.get(ev_key), r.get('tier3_count')) for r in rows if r.get(syn_key) is not None]
    print('syn 事件数:', len(seq))
    print('--- 每 400 代采样 ---')
    last = None
    for g, s, ev, t3 in seq:
        if last is None or (g is not None and last is not None and g - last >= 400):
            print(g, s, str(ev)[:70], f't3={t3}')
            last = g
    print('--- 最后 20 条 ---')
    for g, s, ev, t3 in seq[-20:]:
        print(g, s, str(ev)[:70], f't3={t3}')

# 最近的事件类型分布
if ev_key:
    recent = rows[-200:]
    ec = Counter(str(r.get(ev_key))[:40] for r in recent)
    print('--- 最近 200 条事件类型 ---')
    for k, v in ec.most_common(12):
        print(f'  {k}: {v}')
