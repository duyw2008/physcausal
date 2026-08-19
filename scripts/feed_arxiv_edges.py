#!/usr/bin/env python3
"""一次性: 将 arxiv_reading_list.jsonl 中新论文的概念对注入 feed_queue.jsonl"""
import json, os, time, sys

def main():
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    reading_path = os.path.join(data_dir, "arxiv_reading_list.jsonl")
    feed_path = os.path.join(data_dir, "feed_queue.jsonl")

    if not os.path.exists(reading_path):
        print("[FEED-ARXIV] no reading list found")
        return

    # 读所有条目, 筛选新条目 (extracted_at > 1786500000, Aug 11 batch)
    entries = []
    with open(reading_path) as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    new_entries = [e for e in entries if e.get("extracted_at", 0) > 1786500000]
    print(f"[FEED-ARXIV] total entries: {len(entries)}, new (Aug 11 batch): {len(new_entries)}")

    edges_written = 0
    papers_with_edges = 0

    os.makedirs(data_dir, exist_ok=True)
    with open(feed_path, "a") as feed_f:
        for entry in new_entries:
            arxiv_id = entry.get("arxiv_id", "?")
            concepts = entry.get("concepts", [])
            seen = set()  # dedup per paper
            paper_edges = 0
            for c in concepts:
                src = c.get("src", "").strip()
                dst = c.get("dst", "").strip()
                if not src or not dst or src == dst:
                    continue
                src_n = src.lower().replace(" ", "_")
                dst_n = dst.lower().replace(" ", "_")
                pair = (src_n, dst_n)
                if pair in seen:
                    continue
                seen.add(pair)
                confidence = c.get("confidence", 0.5)
                initial_s = round(0.02 + confidence * 0.06, 3)

                feed_item = {
                    "source": f"arxiv:{arxiv_id}",
                    "type": "edge",
                    "data": {
                        "src": src_n,
                        "dst": dst_n,
                        "law": f"arxiv:{arxiv_id}",
                        "domain": "arxiv_research",
                        "initial_s": initial_s,
                    },
                    "ts": time.time(),
                }
                feed_f.write(json.dumps(feed_item, ensure_ascii=False) + "\n")
                paper_edges += 1
                edges_written += 1
            if paper_edges > 0:
                papers_with_edges += 1

    print(f"[FEED-ARXIV] papers with edges: {papers_with_edges}")
    print(f"[FEED-ARXIV] total edges written: {edges_written}")

    # 验证
    if os.path.exists(feed_path):
        with open(feed_path) as f:
            feed_lines = sum(1 for _ in f)
        print(f"[FEED-ARXIV] feed_queue.jsonl now: {feed_lines} lines")


if __name__ == "__main__":
    main()
