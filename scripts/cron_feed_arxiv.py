#!/usr/bin/env python3
"""Cron job: push arXiv extracted concepts into feed_queue.jsonl as edge feeds."""
import json
import os
import sys
import time

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
READING_LIST = os.path.join(DATA_DIR, "arxiv_reading_list.jsonl")
FEED_QUEUE = os.path.join(DATA_DIR, "feed_queue.jsonl")
# Track which arxiv_ids have already been fed (simple state file)
FED_STATE = os.path.join(DATA_DIR, ".arxiv_fed_state.json")


def load_fed_state():
    if os.path.exists(FED_STATE):
        with open(FED_STATE) as f:
            return set(json.load(f))
    return set()


def save_fed_state(fed_ids):
    with open(FED_STATE, "w") as f:
        json.dump(sorted(fed_ids), f)


def main():
    if not os.path.exists(READING_LIST):
        print("[CRON-FEED] No reading list found.")
        return

    fed_ids = load_fed_state()

    papers = []
    with open(READING_LIST) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                papers.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    # Find papers not yet fed
    new_papers = [p for p in papers if p["arxiv_id"] not in fed_ids]

    if not new_papers:
        print("[CRON-FEED] No new papers to feed.")
        return

    total_edges = 0
    total_papers = 0

    with open(FEED_QUEUE, "a") as fq:
        for paper in new_papers:
            arxiv_id = paper["arxiv_id"]
            title = paper.get("title", "")
            concepts = paper.get("concepts", [])

            if not concepts:
                continue

            # Derive a short domain label from the arxiv_id + title
            domain = "arxiv"
            law_prefix = f"arxiv:{arxiv_id}"

            fed_this_paper = 0
            for c in concepts:
                src = c.get("src", "")
                dst = c.get("dst", "")
                confidence = c.get("confidence", 0.5)
                if not src or not dst:
                    continue

                feed_item = {
                    "source": "arxiv_cron",
                    "type": "edge",
                    "data": {
                        "src": src,
                        "dst": dst,
                        "law": f"{law_prefix}:{src}→{dst}",
                        "domain": domain,
                        "initial_s": round(confidence * 0.15, 3),
                    },
                    "ts": time.time(),
                }
                fq.write(json.dumps(feed_item, ensure_ascii=False) + "\n")
                fed_this_paper += 1

            if fed_this_paper > 0:
                fed_ids.add(arxiv_id)
                total_papers += 1
                total_edges += fed_this_paper

    save_fed_state(fed_ids)
    print(f"[CRON-FEED] Fed {total_papers} papers → {total_edges} causal edges into feed_queue.jsonl")


if __name__ == "__main__":
    main()
