#!/usr/bin/env python3
"""Enrich sparse papers by fetching arXiv abstracts and extracting more causal edges."""
import json, os, re, time, urllib.request
from xml.etree import ElementTree as ET

DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data')
READING_LIST = os.path.join(DATA_DIR, 'arxiv_reading_list.jsonl')
FEED_QUEUE = os.path.join(DATA_DIR, 'feed_queue.jsonl')

# Papers with <= 2 concepts that need enrichment
ENRICH_IDS = [
    "2608.06224", "2608.06326", "2608.06318",  # 1 concept
    "2608.06319", "2608.06282", "2608.06258", "2608.06244",  # 2 concepts
    "2608.06083", "2608.06067", "2608.06016", "2608.06345",  # 2 concepts
    "2608.06308", "2608.06247", "2608.05923",  # 2 concepts
    "2608.06359",  # 3 concepts but quantum foundations
]

def fetch_abstracts(ids):
    """Fetch abstracts from arXiv API."""
    query = ','.join(ids)
    url = f'https://export.arxiv.org/api/query?search_query=id:{query}&max_results=20'
    with urllib.request.urlopen(url, timeout=20) as resp:
        data = resp.read().decode()
    root = ET.fromstring(data)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    results = {}
    for entry in root.findall('a:entry', ns):
        id_el = entry.find('a:id', ns)
        eid = id_el.text if id_el is not None else ''
        arxiv_id = eid.split('/abs/')[-1].replace('v1', '') if '/abs/' in eid else eid
        title_el = entry.find('a:title', ns)
        title = (title_el.text or '').strip().replace('\n', ' ') if title_el is not None else ''
        summary_el = entry.find('a:summary', ns)
        summary = (summary_el.text or '').strip().replace('\n', ' ') if summary_el is not None else ''
        results[arxiv_id] = {'title': title, 'abstract': summary}
    return results

def extract_edges_from_abstract(arxiv_id, title, abstract):
    """Heuristic extraction of causal concept pairs from abstract text."""
    # Known physics causal patterns
    edges = []
    abstract_lower = abstract.lower()
    
    # Pattern-based extraction - causal connector words
    causal_patterns = [
        (r'(\w[\w\s]+?)\s+(?:leads?\s+to|drives?|causes?|induces?|produces?|generates?|results?\s+in)\s+(\w[\w\s]+?)(?:[.,;]|$)', 0.7),
        (r'(\w[\w\s]+?)\s+(?:affects?|influences?|modifies?|alters?|enhances?|suppresses?)\s+(\w[\w\s]+?)(?:[.,;]|$)', 0.65),
        (r'(\w[\w\s]+?)\s+(?:is\s+found\s+to|is\s+shown\s+to)\s+(?:increase|decrease|correlate|depend|scale)\s+(\w[\w\s]+?)(?:[.,;]|$)', 0.6),
        (r'(\w[\w\s]+?)\s+(?:determines?|controls?|governs?|sets?)\s+(\w[\w\s]+?)(?:[.,;]|$)', 0.7),
    ]
    
    extracted = set()
    for pattern, conf in causal_patterns:
        for m in re.finditer(pattern, abstract_lower):
            src = m.group(1).strip()[:60]
            dst = m.group(2).strip()[:60]
            # Clean up - keep meaningful phrases
            src = re.sub(r'\b(the|a|an|this|our|these|those|we|its|their|some|any|very|new|novel)\b', '', src).strip()
            dst = re.sub(r'\b(the|a|an|this|our|these|those|we|its|their|some|any|very|new|novel)\b', '', dst).strip()
            if len(src.split()) >= 1 and len(dst.split()) >= 1 and src != dst:
                src_key = re.sub(r'[_\s]+', '_', src.lower().strip())[:50]
                dst_key = re.sub(r'[_\s]+', '_', dst.lower().strip())[:50]
                pair = (src_key, dst_key)
                if pair not in extracted:
                    extracted.add(pair)
                    edges.append({'src': src_key, 'dst': dst_key, 'confidence': conf})
    
    # If no patterns found, use domain-specific keyword extraction
    if not edges:
        edges = keyword_causal_extraction(abstract_lower, arxiv_id, title)
    
    return edges[:8]  # max 8 new edges per paper

def keyword_causal_extraction(text, arxiv_id, title):
    """Fallback: domain-specific causal relations from keywords."""
    edges = []
    text_lower = text.lower()
    title_lower = title.lower()
    
    # Physics domain knowledge - known causal relationships
    domain_rules = {
        'dark_matter': [
            ('dark_matter_density', 'stellar_structure', 0.7),
            ('dark_matter_halo', 'compact_object_observables', 0.65),
        ],
        'entanglement': [
            ('entanglement_entropy', 'boundary_conformal_field', 0.7),
            ('holographic_entanglement', 'geometry', 0.7),
        ],
        'black_hole': [
            ('black_hole_mass', 'horizon_radius', 0.9),
            ('black_hole_spin', 'ergosphere', 0.8),
        ],
        'quantum_error': [
            ('qubit_count', 'error_threshold', 0.7),
            ('code_distance', 'logical_error_rate', 0.8),
            ('noise_level', 'error_correction_efficacy', 0.65),
        ],
        'inflation': [
            ('inflaton_potential', 'spectral_index', 0.8),
            ('inflation_energy_scale', 'tensor_to_scalar_ratio', 0.7),
        ],
        'quasinormal': [
            ('spacetime_perturbation', 'quasinormal_spectrum', 0.8),
            ('black_hole_parameters', 'ringdown_frequency', 0.75),
        ],
        'quantum': [
            ('quantum_state', 'measurement_outcome', 0.7),
        ],
    }
    
    for keyword, rules in domain_rules.items():
        if keyword in text_lower or keyword in title_lower:
            for src, dst, conf in rules:
                if (src, dst) not in [(e['src'], e['dst']) for e in edges]:
                    edges.append({'src': src, 'dst': dst, 'confidence': conf})
    
    # Also extract from title
    if 'neutron' in title_lower and 'black' in title_lower:
        edges.append({'src': 'dark_matter_halo', 'dst': 'event_horizon_formation', 'confidence': 0.7})
        edges.append({'src': 'anisotropic_dark_matter', 'dst': 'neutron_star_stability', 'confidence': 0.65})
    
    if 'density' in title_lower and 'matrix' in title_lower:
        edges.append({'src': 'quantum_state', 'dst': 'rectification_observable', 'confidence': 0.6})
        edges.append({'src': 'density_matrix', 'dst': 'quantum_geometry', 'confidence': 0.7})
    
    if 'rare' in title_lower and 'quantum' in title_lower:
        edges.append({'src': 'quantum_microphysics', 'dst': 'macroscopic_rare_event', 'confidence': 0.7})
        edges.append({'src': 'quantum_fluctuation', 'dst': 'inflationary_perturbation', 'confidence': 0.65})
    
    if 'compact_boson' in title_lower or 'two_compact' in title_lower:
        edges.append({'src': 'compactification_radius', 'dst': 'partition_function', 'confidence': 0.7})
        edges.append({'src': 'temperature', 'dst': 'phase_diagram', 'confidence': 0.75})
    
    return edges[:8]

def main():
    # Load papers
    with open(READING_LIST) as f:
        papers = [json.loads(line) for line in f if line.strip()]
    new_papers = papers[141:]
    
    # Build lookup
    paper_map = {}
    for p in new_papers:
        pid = p['arxiv_id'].replace('v1', '')
        paper_map[pid] = p
    
    # Fetch abstracts for enrichment targets
    enrich_ids = [eid for eid in ENRICH_IDS if eid in paper_map]
    print(f"[ENRICH] Fetching abstracts for {len(enrich_ids)} sparse papers...")
    
    # Fetch in batches of 5
    new_edges = []
    for i in range(0, len(enrich_ids), 5):
        batch = enrich_ids[i:i+5]
        try:
            abstracts = fetch_abstracts(batch)
            for aid, data in abstracts.items():
                p = paper_map.get(aid)
                if not p:
                    continue
                edges = extract_edges_from_abstract(aid, data['title'], data['abstract'])
                # Filter out edges already in the paper's concepts
                existing = set((c['src'], c['dst']) for c in p.get('concepts', []))
                for e in edges:
                    if (e['src'], e['dst']) not in existing:
                        feed = {
                            "source": f"arxiv_enrich:{p['arxiv_id']}",
                            "type": "edge",
                            "data": {
                                "src": e['src'],
                                "dst": e['dst'],
                                "law": "abstract_extract",
                                "domain": "research",
                                "initial_s": round(e['confidence'] * 0.1, 3),
                                "arxiv_id": p['arxiv_id'],
                                "title": p['title'][:120],
                            },
                            "ts": time.time(),
                        }
                        new_edges.append(feed)
                        existing.add((e['src'], e['dst']))
            if batch:
                print(f"  Batch {i//5+1}: {len(batch)} papers fetched")
        except Exception as e:
            print(f"  Batch {i//5+1} ERROR: {type(e).__name__}: {e}")
    
    # Append to feed_queue
    if new_edges:
        with open(FEED_QUEUE, 'a') as f:
            for item in new_edges:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        print(f"\n[ENRICH] Added {len(new_edges)} additional causal edges from abstract analysis")
        for item in new_edges[:5]:
            d = item['data']
            print(f"  + {d['src']} → {d['dst']} (s={d['initial_s']}) | {d['arxiv_id']}")
        if len(new_edges) > 5:
            print(f"  ... and {len(new_edges)-5} more")
    else:
        print("[ENRICH] No new edges extracted")

    # Final count
    total_edges = 0
    if os.path.exists(FEED_QUEUE):
        with open(FEED_QUEUE) as f:
            total_edges = sum(1 for _ in f)
    print(f"\n[FEED-CRON] Total edges in feed_queue: {total_edges}")

if __name__ == '__main__':
    main()
