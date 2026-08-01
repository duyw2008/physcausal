"""Feed existing arxiv_reading_list.jsonl concepts into feed_queue.jsonl as edges."""
import json, os, sys, time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from meta_cognition.feed_queue import FeedQueue

data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
reading_list_path = os.path.join(data_dir, "arxiv_reading_list.jsonl")

if not os.path.exists(reading_list_path):
    print("No reading list found.")
    sys.exit(0)

fq = FeedQueue(data_dir)

papers_fed = 0
edges_fed = 0

with open(reading_list_path) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            paper = json.loads(line)
        except json.JSONDecodeError:
            continue

        arxiv_id = paper.get("arxiv_id", "unknown")
        title = paper.get("title", "")
        concepts = paper.get("concepts", [])

        if not concepts:
            continue

        for c in concepts:
            src = c.get("src", "")
            dst = c.get("dst", "")
            if not src or not dst:
                continue
            fq.feed_edge(
                src=src,
                dst=dst,
                law=f"arxiv:{arxiv_id}",
                source="arxiv",
                domain="physics",
                initial_s=max(0.03, c.get("confidence", 0.5) * 0.1)
            )
            edges_fed += 1

        papers_fed += 1

print(f"Fed {papers_fed} papers → {edges_fed} edges into feed_queue.jsonl")
