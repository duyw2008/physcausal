#!/usr/bin/env python3
"""Feed fresh arXiv papers (glance_count==0) into feed_queue as edge-type items."""
import json, time, os, sys

def main():
    reading_list_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'arxiv_reading_list.jsonl')
    feed_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'feed_queue.jsonl')
    
    with open(reading_list_path) as f:
        papers = [json.loads(l) for l in f if l.strip()]
    
    # Filter: glance_count == 0, has concepts > 0
    fresh = [p for p in papers if p.get('glance_count', 0) == 0 and len(p.get('concepts', [])) > 0]
    
    print(f"Processing {len(fresh)} fresh papers with concepts...")
    
    os.makedirs(os.path.dirname(feed_path), exist_ok=True)
    
    total_edges = 0
    paper_count = 0
    
    with open(feed_path, 'a') as fout:
        for p in fresh:
            arxiv_id = p['arxiv_id']
            concepts = p['concepts']
            
            edges_written = 0
            for c in concepts:
                src = c['src']
                dst = c['dst']
                confidence = c.get('confidence', 0.5)
                
                if confidence < 0.5:
                    continue
                
                edge_item = {
                    "source": f"arxiv:{arxiv_id}",
                    "type": "edge",
                    "data": {
                        "src": src,
                        "dst": dst,
                        "law": "arxiv_feed",
                        "domain": "physics",
                        "initial_s": round(confidence * 0.1, 3)
                    },
                    "ts": time.time()
                }
                fout.write(json.dumps(edge_item, ensure_ascii=False) + '\n')
                edges_written += 1
            
            if edges_written > 0:
                paper_count += 1
                total_edges += edges_written
                print(f"  {arxiv_id}: {edges_written} edges")
    
    print(f"\nDone: {paper_count} papers → {total_edges} causal edges → data/feed_queue.jsonl")
    return paper_count, total_edges

if __name__ == '__main__':
    main()
