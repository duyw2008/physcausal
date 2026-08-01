#!/usr/bin/env python3
"""
费曼脑 feed_queue 注入器 — 从 arxiv_reading_list.jsonl 提取因果边 → feed_queue.jsonl

输出格式对齐 meta_cognition/feed_queue.py 的 _consume_one() 期望:
  { source, type: "edge", data: { src, dst, law, domain, initial_s }, ts }

用法: cron 定时运行, 把新论文的概念对转为 "edge" 类型 feed,
      让费曼脑突触有新鲜数据可学习。
"""
from __future__ import annotations
import json, os, sys, time

READING_LIST = os.path.join(os.path.dirname(__file__), "data", "arxiv_reading_list.jsonl")
FEED_QUEUE = os.path.join(os.path.dirname(__file__), "data", "feed_queue.jsonl")
PROCESSED_DIR = os.path.join(os.path.dirname(__file__), "data", "feed_processed")

OLD_BATCH_TS = 1785430000  # 旧批次时间戳分界线


def load_new_papers() -> list[dict]:
    """加载 extract_at > OLD_BATCH_TS 的新论文"""
    papers = []
    if not os.path.exists(READING_LIST):
        return papers
    with open(READING_LIST) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                if entry.get("extracted_at", 0) > OLD_BATCH_TS:
                    papers.append(entry)
            except json.JSONDecodeError:
                pass
    return papers


def get_already_fed_ids() -> set:
    """扫描 feed_processed 目录，找已喂过的 arxiv_id"""
    fed = set()
    # 检查当前 feed_queue (如果还没被消费)
    if os.path.exists(FEED_QUEUE):
        with open(FEED_QUEUE) as f:
            for line in f:
                try:
                    item = json.loads(line)
                    src = item.get("source", "")
                    law = item.get("data", {}).get("law", "")
                    if src == "arxiv" and "arxiv:" in law:
                        aid = law.replace("arxiv:", "").split("/")[0]
                        fed.add(aid)
                except json.JSONDecodeError:
                    pass
    # 检查已归档的
    if os.path.exists(PROCESSED_DIR):
        for fname in os.listdir(PROCESSED_DIR):
            if not fname.endswith(".jsonl"):
                continue
            fpath = os.path.join(PROCESSED_DIR, fname)
            try:
                with open(fpath) as f:
                    for line in f:
                        try:
                            item = json.loads(line)
                            src = item.get("source", "")
                            law = item.get("data", {}).get("law", "")
                            if src == "arxiv" and "arxiv:" in law:
                                aid = law.replace("arxiv:", "").split("/")[0]
                                fed.add(aid)
                        except json.JSONDecodeError:
                            pass
            except Exception:
                pass
    return fed


def write_edge_feed(arxiv_id: str, title: str, src_concept: str,
                    dst_concept: str, confidence: float):
    """写入一条 edge 类型 feed (对齐 FeedQueue._consume_one 格式)"""
    # 规范化概念名: 小写 + 下划线
    src = src_concept.lower().replace(" ", "_")
    dst = dst_concept.lower().replace(" ", "_")

    entry = {
        "source": "arxiv",
        "type": "edge",
        "data": {
            "src": src,
            "dst": dst,
            "law": f"arxiv:{arxiv_id}",
            "domain": "arxiv_research",
            "initial_s": min(0.1, confidence * 0.1),  # 根据置信度调整初始强度
        },
        "ts": time.time(),
    }
    with open(FEED_QUEUE, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def fetch_abstract(arxiv_id: str) -> str:
    """通过 arXiv API 获取摘要 (用于补充概念)"""
    import urllib.request
    import xml.etree.ElementTree as ET
    url = f"https://export.arxiv.org/api/query?id_list={arxiv_id}&max_results=1"
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        summary_el = root.find(".//a:summary", ns)
        if summary_el is not None and summary_el.text:
            return summary_el.text.strip().replace("\n", " ")
    except Exception as e:
        print(f"  [WARN] fetch abstract {arxiv_id}: {e}", file=sys.stderr)
    return ""


def supplement_concepts(paper: dict, abstract: str) -> list[dict]:
    """保证每篇论文 3-10 条因果边。已有足够则直接使用；不足则基于标题/摘要补充。"""
    concepts = paper.get("concepts", [])
    title = paper.get("title", "")
    title_lower = title.lower()
    abstract_lower = abstract.lower()

    # 如果已有 3+ 条, 直接返回 (但最多保留 10 条)
    if len(concepts) >= 3:
        return concepts[:10]

    # 不足 → 基于关键词补充
    extra = []
    patterns = [
        ("neutron star", "neutron_star_eos", "gravitational_wave_signal", 0.6),
        ("dark matter", "dark_matter_distribution", "structure_formation", 0.6),
        ("dark energy", "dark_energy_density", "cosmic_acceleration", 0.6),
        ("inflation", "inflaton_potential", "primordial_perturbations", 0.6),
        ("black hole", "black_hole_mass", "gravitational_waveform", 0.6),
        ("gravitational wave", "source_parameters", "waveform_template", 0.6),
        ("quantum error", "physical_error_rate", "logical_error_rate", 0.6),
        ("cosmic string", "string_tension", "gw_spectrum", 0.6),
        ("tensor model", "tensor_rank", "large_n_expansion", 0.6),
        ("entanglement", "entanglement_entropy", "quantum_channel_capacity", 0.6),
        ("scalar field", "scalar_potential", "cosmological_dynamics", 0.6),
        ("q-ball", "q_ball_charge", "halo_density_profile", 0.6),
        ("cosmology", "cosmological_parameters", "observable_predictions", 0.6),
        ("gauge theory", "gauge_coupling", "phase_diagram", 0.6),
        ("holography", "bulk_geometry", "boundary_cft", 0.6),
        ("supersymmetry", "susy_breaking_scale", "particle_spectrum", 0.6),
        ("string theory", "compactification_topology", "low_energy_spectrum", 0.6),
        ("quantum chaos", "lyapunov_exponent", "scrambling_time", 0.6),
        ("lindbladian", "lindblad_operators", "decoherence_rate", 0.6),
        ("error correcting code", "code_distance", "threshold", 0.6),
        ("lifted product", "base_matrix", "code_dimension", 0.6),
        ("seiberg dual", "electric_theory", "magnetic_theory", 0.7),
        ("bms", "asymptotic_symmetry", "soft_theorem", 0.7),
        ("asymptotic symmetry", "asymptotic_charge", "memory_effect", 0.7),
        ("soft charge", "soft_graviton_theorem", "infrared_structure", 0.7),
        ("axion", "axion_decay_constant", "coupling_strength", 0.7),
        ("hayden-preskill", "information_scrambling", "recovery_fidelity", 0.7),
        ("syk model", "syk_coupling", "maximal_chaos", 0.7),
        ("clifford", "clifford_group", "stabilizer_state", 0.7),
        ("pauli", "pauli_weight", "circuit_depth", 0.6),
        ("cnot", "gate_count", "circuit_complexity", 0.6),
        ("gauss-bonnet", "gauss_bonnet_coupling", "gravitational_wave_phase", 0.7),
        ("numerical relativity", "initial_data", "evolution_scheme", 0.6),
        ("einstein constraint", "constraint_violation", "numerical_stability", 0.7),
        ("lisa", "strain_sensitivity", "source_detectability", 0.7),
        ("icecube", "neutrino_flux", "source_localization", 0.7),
        ("multi-messenger", "em_counterpart", "skymap_localization", 0.7),
        ("simulation", "numerical_resolution", "systematic_error", 0.6),
        ("unclonable", "no_cloning_theorem", "information_theoretic_security", 0.7),
        ("monogamy", "monogamy_of_entanglement", "security_proof", 0.7),
        ("spacetime dimension", "dimensionality", "renormalizability", 0.7),
        ("cosmic structure", "power_spectrum", "cosmological_parameters", 0.7),
        ("interface", "boundary_condition", "transport_coefficient", 0.6),
        ("einstein", "metric", "curvature", 0.6),
        ("ricci", "ricci_curvature", "energy_momentum_tensor", 0.6),
    ]

    existing_srcs = {c.get("src", "").lower().replace(" ", "_") for c in concepts}
    existing_dsts = {c.get("dst", "").lower().replace(" ", "_") for c in concepts}

    for keyword, src, dst, conf in patterns:
        if keyword in title_lower or keyword in abstract_lower:
            if src.lower() not in existing_srcs and dst.lower() not in existing_dsts:
                extra.append({"src": src, "dst": dst, "confidence": conf})
                existing_srcs.add(src.lower())
                existing_dsts.add(dst.lower())
        if len(concepts) + len(extra) >= 5:
            break

    result = concepts + extra[:max(0, 5 - len(concepts))]
    return result[:10]


def main():
    print("[FEED-PROCESSOR] Starting...")

    papers = load_new_papers()
    print(f"[FEED-PROCESSOR] Found {len(papers)} new papers since last batch")

    if not papers:
        print("[FEED-PROCESSOR] No new papers to process")
        return

    already_fed = get_already_fed_ids()
    papers = [p for p in papers if p["arxiv_id"] not in already_fed]
    print(f"[FEED-PROCESSOR] After dedup: {len(papers)} papers to feed")

    total_edges = 0
    low_edge_papers = 0

    for i, paper in enumerate(papers):
        arxiv_id = paper["arxiv_id"]
        title = paper["title"]
        print(f"  [{i+1}/{len(papers)}] {arxiv_id}: {title[:55]}...")

        abstract = fetch_abstract(arxiv_id)
        concepts = supplement_concepts(paper, abstract)

        paper_edges = 0
        for c in concepts:
            src = c.get("src", "")
            dst = c.get("dst", "")
            if not src or not dst:
                continue
            write_edge_feed(arxiv_id, title, src, dst,
                            c.get("confidence", 0.5))
            paper_edges += 1

        total_edges += paper_edges
        flag = " ⚠ LOW" if paper_edges < 3 else ""
        if paper_edges < 3:
            low_edge_papers += 1
        print(f"    → {paper_edges} edges{flag}")

    # 统计
    queue_count = 0
    if os.path.exists(FEED_QUEUE):
        with open(FEED_QUEUE) as f:
            queue_count = sum(1 for _ in f if _.strip())

    print(f"\n[FEED-PROCESSOR] Done: {len(papers)} papers → {total_edges} causal edges")
    print(f"[FEED-PROCESSOR] Feed queue now: {queue_count} entries")
    if low_edge_papers:
        print(f"[FEED-PROCESSOR] ⚠ {low_edge_papers} papers have <3 edges")


if __name__ == "__main__":
    main()
