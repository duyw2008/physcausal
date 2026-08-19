#!/usr/bin/env python3
"""Batch feed arxiv reading list concepts into feed_queue.jsonl"""
import json, time, os, sys
from collections import Counter

data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

# Read all papers
papers = []
reading_path = os.path.join(data_dir, 'arxiv_reading_list.jsonl')
with open(reading_path) as f:
    for line in f:
        line = line.strip()
        if line:
            papers.append(json.loads(line))

# Find pending (not promoted) papers
pending = [p for p in papers if not p.get('promoted', False)]
print(f"Processing {len(pending)} pending papers...")

feed_items = []
papers_fed = 0
total_edges = 0

for paper in pending:
    concepts = paper.get('concepts', [])
    if not concepts:
        continue
    
    arxiv_id = paper['arxiv_id']
    
    for c in concepts:
        src = c['src']
        dst = c['dst']
        confidence = c.get('confidence', 0.5)
        
        item = {
            "source": f"arxiv:{arxiv_id}",
            "type": "edge",
            "data": {
                "src": src,
                "dst": dst,
                "law": "arxiv_feed",
                "domain": "research",
                "initial_s": round(0.05 * confidence, 4)
            },
            "ts": time.time()
        }
        feed_items.append(item)
        total_edges += 1
    
    papers_fed += 1

# Append to feed_queue.jsonl
queue_path = os.path.join(data_dir, 'feed_queue.jsonl')
with open(queue_path, 'a') as f:
    for item in feed_items:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"DONE: Fed {papers_fed} papers, {total_edges} causal edges into feed_queue.jsonl")

# Show distribution
edge_counts = Counter()
for paper in pending:
    n = len(paper.get('concepts', []))
    edge_counts[f'{n}_edges'] += 1
print(f"Per-paper edge distribution: {dict(sorted(edge_counts.items()))}")

# List sparse papers (<3 edges, need enrichment)
sparse = [(p['arxiv_id'], p['title'], len(p.get('concepts',[]))) 
          for p in pending if len(p.get('concepts',[])) < 3]
print(f"\nSparse papers (<3 edges): {len(sparse)}")
for arx, title, n in sparse[:20]:
    print(f"  {arx} [{n} edges] {title[:70]}")
