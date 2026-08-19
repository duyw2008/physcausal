#!/usr/bin/env python3
"""Enrich sparse arxiv papers by fetching abstracts from arXiv API and extracting extra causal edges."""
import json, urllib.request, xml.etree.ElementTree as ET, time, os, sys

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

# Load sparse papers (<3 edges)
papers = []
with open(os.path.join(data_dir, 'arxiv_reading_list.jsonl')) as f:
    for line in f:
        line = line.strip()
        if line:
            papers.append(json.loads(line))

pending = [p for p in papers if not p.get('promoted', False)]
sparse = [p for p in pending if len(p.get('concepts', [])) < 3]
print(f"Sparse papers to enrich: {len(sparse)}")

# Take batches of 10
batch = sparse[:10]
ids = [p['arxiv_id'].replace('v1','').replace('v2','').replace('v3','') for p in batch]
id_str = ','.join(ids)
print(f"Fetching abstracts for {len(batch)} papers: {id_str}")

try:
    url = f'http://export.arxiv.org/api/query?id_list={id_str}&max_results=10'
    req = urllib.request.Request(url, headers={'User-Agent': 'FeynmanBrain/1.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode('utf-8')
    
    ns = {'atom': 'http://www.w3.org/2005/Atom',
          'arxiv': 'http://arxiv.org/schemas/atom'}
    root = ET.fromstring(raw)
    
    results = {}
    for entry in root.findall('atom:entry', ns):
        aid = entry.find('atom:id', ns).text.strip().split('/abs/')[-1]
        title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
        abstract = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
        results[aid] = {'title': title, 'abstract': abstract}
    
    # Print results for inspection
    for aid, info in results.items():
        print(f"\n=== {aid} ===")
        print(f"TITLE: {info['title'][:150]}")
        print(f"ABSTRACT: {info['abstract'][:800]}")
    
    # Write results to a JSON file for later processing
    out_path = os.path.join(data_dir, 'sparse_abstracts.json')
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} abstracts to {out_path}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
