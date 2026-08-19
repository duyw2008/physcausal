#!/usr/bin/env python3
"""Inject arXiv causal edges into feed_queue using the proper FeedQueue API."""
import json, sys, os, time

# Add project root
sys.path.insert(0, "/home/duyw/physcausal")
os.chdir("/home/duyw/physcausal")

from meta_cognition.feed_queue import FeedQueue

def main():
    reading_list_path = "data/arxiv_reading_list.jsonl"
    
    # Read all papers
    papers = []
    with open(reading_list_path) as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))
    
    # Take last 32 (newly added)
    new_papers = papers[-32:]
    
    q = FeedQueue()
    
    edges_written = 0
    papers_fed = 0
    
    for paper in new_papers:
        arxiv_id = paper["arxiv_id"]
        title = paper["title"]
        concepts = paper.get("concepts", [])
        
        if not concepts:
            continue
        
        papers_fed += 1
        for c in concepts:
            q.feed_edge(
                src=c["src"],
                dst=c["dst"],
                law=f"arxiv:{arxiv_id}:{c['src']}→{c['dst']}",
                source="arxiv",
                domain="physics_literature",
                initial_s=c["confidence"]
            )
            edges_written += 1
    
    # Also feed some key concept nodes
    key_concepts = set()
    for paper in new_papers:
        for c in paper.get("concepts", []):
            key_concepts.add(c["src"])
            key_concepts.add(c["dst"])
    
    nodes_fed = 0
    for name in key_concepts:
        q.feed_concept(name=name, source="arxiv", domain="physics_literature")
        nodes_fed += 1
    
    # Count queue
    with open(q.queue_path) as f:
        total = sum(1 for _ in f)
    
    print(f"[FEED-INJECT] Papers: {papers_fed} | Edges: {edges_written} | Concept nodes: {nodes_fed}")
    print(f"[FEED-INJECT] Feed queue now has {total} pending items")
    
    return papers_fed, edges_written

if __name__ == "__main__":
    papers, edges = main()
