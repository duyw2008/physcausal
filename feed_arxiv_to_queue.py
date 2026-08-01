#!/usr/bin/env python3
"""Feed arxiv_reading_list.jsonl concepts into feed_queue.jsonl as edges."""
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from meta_cognition.feed_queue import FeedQueue

def main():
    reading_list_path = os.path.join(os.path.dirname(__file__), 'data', 'arxiv_reading_list.jsonl')
    papers = []
    with open(reading_list_path) as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))

    print(f"Loaded {len(papers)} papers from reading list")

    fq = FeedQueue(os.path.join(os.path.dirname(__file__), 'data'))

    total_edges = 0
    papers_fed = 0

    for paper in papers:
        arxiv_id = paper['arxiv_id']
        title = paper['title']
        concepts = paper.get('concepts', [])

        if not concepts:
            continue

        # Filter for meaningful causal pairs (confidence >= 0.6)
        causal_edges = [c for c in concepts if c.get('confidence', 0) >= 0.6]

        # Skip self-loops (src == dst)
        causal_edges = [c for c in causal_edges if c['src'] != c['dst']]

        if not causal_edges:
            continue

        for c in causal_edges:
            src = c['src']
            dst = c['dst']
            confidence = c.get('confidence', 0.6)
            law = f"arxiv:{arxiv_id}"

            fq.feed_edge(
                src=src,
                dst=dst,
                law=law,
                source=f"arxiv:{arxiv_id}",
                domain="physics_research",
                initial_s=round(confidence * 0.2, 3)
            )

        papers_fed += 1
        total_edges += len(causal_edges)
        print(f"  [{arxiv_id}] {title[:70]}... -> {len(causal_edges)} edges")

    print(f"\nTotal: {papers_fed} papers -> {total_edges} causal edges fed to queue")

if __name__ == '__main__':
    main()
