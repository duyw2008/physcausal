#!/usr/bin/env python3
"""Inject the 31 newest papers' concept pairs into feed_queue.jsonl as edges."""
import json, time, os, sys

READING_LIST = os.path.join(os.path.dirname(__file__), "data", "arxiv_reading_list.jsonl")
FEED_QUEUE = os.path.join(os.path.dirname(__file__), "data", "feed_queue.jsonl")

def main():
    # Read all papers
    papers = []
    with open(READING_LIST, "r") as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))

    # Sort by extracted_at descending
    papers.sort(key=lambda p: p.get("extracted_at", 0), reverse=True)

    # Take 31 most recent
    new_papers = papers[:31]

    now = time.time()
    total_edges = 0
    new_feed_entries = []

    for paper in new_papers:
        arxiv_id = paper["arxiv_id"]
        title = paper["title"]
        concepts = paper.get("concepts", [])

        for concept in concepts:
            edge = {
                "source": "arxiv",
                "type": "edge",
                "data": {
                    "src": concept["src"],
                    "dst": concept["dst"],
                    "law": f"arxiv:{arxiv_id}:{concept['src']}→{concept['dst']}",
                    "domain": "physics",
                    "initial_s": round(concept.get("confidence", 0.5), 2),
                    "arxiv_id": arxiv_id,
                    "title": title,
                },
                "ts": now,
            }
            new_feed_entries.append(edge)
            total_edges += 1

    # Write to feed_queue (append)
    with open(FEED_QUEUE, "a") as f:
        for entry in new_feed_entries:
            f.write(json.dumps(entry) + "\n")

    print(f"[INJECT] Written {total_edges} edges from {len(new_papers)} papers to feed_queue.jsonl")
    for p in new_papers[:5]:
        print(f"  {p['arxiv_id']}: {p['title'][:70]}...")

if __name__ == "__main__":
    main()
