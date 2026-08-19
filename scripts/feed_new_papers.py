#!/usr/bin/env python3
"""Feed new arXiv papers' causal edges into feed_queue.jsonl for Feynman Brain."""
import json
import os
import sys
import time

def main():
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
    reading_list_path = os.path.join(data_dir, 'arxiv_reading_list.jsonl')
    feed_queue_path = os.path.join(data_dir, 'feed_queue.jsonl')
    
    # Load reading list
    with open(reading_list_path) as f:
        papers = [json.loads(line) for line in f if line.strip()]
    
    # The 31 new papers are at indices 141-171 (0-indexed, lines 142-172)
    new_papers = papers[141:]
    
    total_papers = len(new_papers)
    total_edges = 0
    skipped_papers = 0
    fed_edges = []
    
    for paper in new_papers:
        arxiv_id = paper['arxiv_id']
        title = paper['title']
        concepts = paper.get('concepts', [])
        
        if not concepts:
            skipped_papers += 1
            continue
        
        for c in concepts:
            src = c['src']
            dst = c['dst']
            confidence = c.get('confidence', 0.5)
            
            # Build edge feed item
            feed_item = {
                "source": f"arxiv:{arxiv_id}",
                "type": "edge",
                "data": {
                    "src": src,
                    "dst": dst,
                    "law": "arxiv_feed",
                    "domain": "research",
                    "initial_s": round(confidence * 0.1, 3),  # scale confidence to initial strength
                    "arxiv_id": arxiv_id,
                    "title": title[:120],
                },
                "ts": time.time(),
            }
            fed_edges.append(feed_item)
            total_edges += 1
    
    # Append to feed_queue.jsonl
    os.makedirs(data_dir, exist_ok=True)
    with open(feed_queue_path, 'a') as f:
        for item in fed_edges:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
    
    print(f"[FEED-CRON] Ingested {total_papers} papers → {total_edges} causal edges into feed_queue")
    print(f"[FEED-CRON] Skipped {skipped_papers} papers with no concepts")
    
    # Show sample
    if fed_edges:
        print(f"\n[FEED-CRON] Sample edges:")
        for item in fed_edges[:5]:
            d = item['data']
            print(f"  {d['src']} → {d['dst']}  (s={d['initial_s']})  |  {d['title'][:60]}")
        if len(fed_edges) > 5:
            print(f"  ... and {len(fed_edges)-5} more")

if __name__ == '__main__':
    main()
