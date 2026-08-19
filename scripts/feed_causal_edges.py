#!/usr/bin/env python3
"""
Extract causal edges from arXiv paper abstracts and feed into Feynman Brain feed_queue.
Reads abstract XML, uses LLM-extracted causal pairs, writes via FeedQueue.
"""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from meta_cognition.feed_queue import FeedQueue

# Load abstract data
import xml.etree.ElementTree as ET
tree = ET.parse('/tmp/arxiv_abstracts.xml')
ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}

papers = []
for entry in tree.findall('atom:entry', ns):
    arxiv_id_full = entry.find('atom:id', ns).text.strip().split('/')[-1]
    title = entry.find('atom:title', ns).text.strip().replace('\n', ' ').replace('  ', ' ')
    abstract = entry.find('atom:summary', ns).text.strip().replace('\n', ' ').replace('  ', ' ')
    papers.append({'arxiv_id': arxiv_id_full, 'title': title, 'abstract': abstract})

# Load reading list to check which are pending
with open('data/arxiv_reading_list.jsonl') as f:
    lines = [json.loads(l) for l in f if l.strip()]
pending_ids = set()
for l in lines:
    if l.get('promoted') != True:
        base = l['arxiv_id'].replace('v1','').replace('v2','').replace('v3','').replace('v4','')
        pending_ids.add(base)

# Filter papers to only pending ones
papers_to_process = []
for p in papers:
    base_id = p['arxiv_id']
    if 'v' in base_id:
        base_id = base_id[:base_id.rindex('v')]
    if base_id in pending_ids:
        papers_to_process.append(p)

print(f"Papers in XML: {len(papers)}, pending: {len(papers_to_process)}")

# Load pre-extracted causal edges from the reading list
with open('data/arxiv_reading_list.jsonl') as f:
    reading_list = [json.loads(l) for l in f if l.strip()]

# Build a map from arxiv_id to pre-extracted concepts
concept_map = {}
for entry in reading_list:
    base_id = entry['arxiv_id']
    if 'v' in base_id:
        base_id = base_id[:base_id.rindex('v')]
    if entry.get('concepts'):
        concept_map[base_id] = entry['concepts']

# Now write all edges to feed queue
q = FeedQueue()
total_papers = 0
total_edges = 0

for p in papers_to_process:
    base_id = p['arxiv_id']
    if 'v' in base_id:
        base_id = base_id[:base_id.rindex('v')]
    
    concepts = concept_map.get(base_id, [])
    if not concepts:
        continue
    
    paper_edges = 0
    for c in concepts:
        src = c.get('src', '')
        dst = c.get('dst', '')
        confidence = c.get('confidence', 0.5)
        if src and dst:
            q.feed_edge(
                src=src, dst=dst,
                law=f"arxiv:{base_id}",
                source="arxiv_feed",
                domain="research",
                initial_s=min(0.15, confidence * 0.15)
            )
            paper_edges += 1
            total_edges += 1
    
    if paper_edges > 0:
        total_papers += 1
        print(f"  {base_id}: {paper_edges} edges → {p['title'][:60]}")

print(f"\nDone: {total_papers} papers, {total_edges} causal edges fed")
