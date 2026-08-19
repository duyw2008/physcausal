#!/usr/bin/env python3
"""Feed extracted causal edges into feed_queue.jsonl (edge type).

Usage: python3 scripts/_feed_edges.py --paper <arxiv_id> --edges <json_file>
Or:    python3 scripts/_feed_edges.py --paper <arxiv_id> --edges-inline '<json array>'
"""
import json, os, sys, time

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
DATA = os.path.join(ROOT, "data")
QUEUE = os.path.join(DATA, "feed_queue.jsonl")
FED_STATE = os.path.join(DATA, ".arxiv_fed_state.json")


def load_fed():
    if os.path.exists(FED_STATE):
        try:
            return set(json.load(open(FED_STATE)))
        except Exception:
            return set()
    return set()


def save_fed(s):
    with open(FED_STATE, "w") as f:
        json.dump(sorted(s), f)


def append_edges(arxiv_id, edges):
    """edges: list of dicts {src, dst, confidence}"""
    n = 0
    with open(QUEUE, "a") as f:
        for e in edges:
            src = e.get("src", "").strip()
            dst = e.get("dst", "").strip()
            conf = float(e.get("confidence", 0.6))
            if not src or not dst or src == dst:
                continue
            item = {
                "source": "arxiv_feed",
                "type": "edge",
                "data": {
                    "src": src,
                    "dst": dst,
                    "law": f"arxiv:{arxiv_id}",
                    "domain": "physics_research",
                    "initial_s": round(conf * 0.2, 3),
                },
                "ts": time.time(),
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            n += 1
    return n


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--paper", required=True)
    ap.add_argument("--edges-file", default=None)
    ap.add_argument("--edges-inline", default=None)
    ap.add_argument("--mark-fed", action="store_true",
                    help="mark paper as fed in state file")
    args = ap.parse_args()

    if args.edges_inline:
        edges = json.loads(args.edges_inline)
    elif args.edges_file:
        edges = json.load(open(args.edges_file))
    else:
        edges = []

    n = append_edges(args.paper, edges)
    if args.mark_fed:
        fed = load_fed()
        fed.add(args.paper)
        save_fed(fed)
    print(f"fed {args.paper}: {n} edges")
