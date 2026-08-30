#!/usr/bin/env python3
"""费曼脑拓扑健康体检：读取最新 evo_snapshot 提取关键指标"""
import json, glob, os, sys, gzip

DATA = os.path.expanduser('~/Agent/physcausal/data')

def load_json(path):
    with gzip.open(path, 'rt', encoding='utf-8') as f:
        return json.load(f)

# 找最新快照
kg_files = sorted(glob.glob(os.path.join(DATA, 'evo_snapshot_gen*_kg.json')))
neural_files = sorted(glob.glob(os.path.join(DATA, 'evo_snapshot_gen*_neural.json')))
latest_kg = kg_files[-1]
latest_neural = neural_files[-1]
gen = latest_kg.split('gen')[1].split('_')[0]
print(f"最新快照: gen {gen}")
print(f"  kg: {latest_kg} ({os.path.getsize(latest_kg)//1024//1024}MB)")
print(f"  neural: {latest_neural} ({os.path.getsize(latest_neural)//1024//1024}MB)")

kg = load_json(latest_kg)
print("\nkg 顶层 keys:", list(kg.keys()) if isinstance(kg, dict) else type(kg))

if isinstance(kg, dict):
    print("\nvs.graph keys:", list(kg['vs.graph'].keys()))
    for k, v in kg['vs.graph'].items():
        if isinstance(v, list):
            print(f"  {k}: list[{len(v)}]", type(v[0]).__name__ if v else '')
        else:
            print(f"  {k}: {type(v).__name__} = {str(v)[:60]}")
    print("\nvs.cache 首元素:")
    first_key = list(kg['vs.cache'].keys())[0]
    print(f"  key={first_key!r}, val type={type(kg['vs.cache'][first_key]).__name__}")
    print(f"  val={str(kg['vs.cache'][first_key])[:200]}")
    print("\nemergent_edges 首元素:", str(kg['emergent_edges'][0])[:300])
    print("emergent_edges 类型:", type(kg['emergent_edges'][0]).__name__)
