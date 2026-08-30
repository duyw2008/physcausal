#!/usr/bin/env python3
"""拓扑健康体检:读取最新 evo_snapshot 计算关键指标。"""
import json, gzip, glob, os, sys

data_dir = os.path.expanduser('~/Agent/physcausal/data')

def load(path):
    with open(path, 'rb') as f:
        raw = f.read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw)

# 最新快照
kg_files = sorted(glob.glob(os.path.join(data_dir, 'evo_snapshot_gen*_kg.json')))
neural_files = sorted(glob.glob(os.path.join(data_dir, 'evo_snapshot_gen*_neural.json')))
latest_kg = kg_files[-1]
latest_nn = neural_files[-1]
print(f"latest_kg : {os.path.basename(latest_kg)}")
print(f"latest_nn : {os.path.basename(latest_nn)}")

kg = load(latest_kg)
nn = load(latest_nn)

print("KG top-level keys:", list(kg.keys())[:30])
print("NN top-level keys:", list(nn.keys())[:30])

# 探查结构
for k, v in kg.items():
    if isinstance(v, (int, float, str, bool)):
        print(f"  KG scalar {k} = {v}")
    elif isinstance(v, list):
        print(f"  KG list {k}: len={len(v)} sample={v[0] if v else None}")
    elif isinstance(v, dict):
        print(f"  KG dict {k}: keys={list(v.keys())[:8]}")
for k, v in nn.items():
    if isinstance(v, (int, float, str, bool)):
        print(f"  NN scalar {k} = {v}")
    elif isinstance(v, list):
        print(f"  NN list {k}: len={len(v)} sample={v[0] if v else None}")
    elif isinstance(v, dict):
        print(f"  NN dict {k}: keys={list(v.keys())[:8]}")
