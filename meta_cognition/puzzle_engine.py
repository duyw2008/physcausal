"""
认知拼图引擎 — 缺口驱动的自主发现

每个 think() 周期:
  1. 扫描 COGNITIVE_PUZZLE.md 中的缺口
  2. 对最高优先级缺口, 在因果图中搜索可能的桥接
  3. 提案 → 验证 → 嵌入 → 更新拼图
"""

from __future__ import annotations
import os, re, json
from typing import Dict, List, Optional


def _puzzle_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "docs", "COGNITIVE_PUZZLE.md"
    )


def scan_gaps() -> List[Dict]:
    """扫描认知拼图中的缺口, 返回优先级排序列表"""
    path = _puzzle_path()
    if not os.path.exists(path):
        return [{"name": "no_puzzle", "priority": 0, "desc": "COGNITIVE_PUZZLE.md not found"}]

    with open(path) as f:
        content = f.read()

    gaps = []
    pattern = r'### 缺口 (\d+): (.+?) (⭐+).*?\n- \*\*现状\*\*: (.+?)\n'
    for m in re.finditer(pattern, content, re.DOTALL):
        full_block = content[m.start():m.end()+200]  # 取缺口完整文本
        if '✅' in full_block:
            continue
        # 解析字段
        name = m.group(2).strip()
        stars = len(m.group(3))
        status = m.group(4).strip()
        
        # 找方向和优先级
        need_match = re.search(r'\*\*需要\*\*: (.+?)\n', full_block)
        dir_match = re.search(r'\*\*方向\*\*: (.+?)\n', full_block)
        pri_match = re.search(r'\*\*优先级\*\*: (.+?)\n', full_block)
        
        gaps.append({
            "id": int(m.group(1)),
            "name": name,
            "stars": stars,
            "status": status,
            "need": need_match.group(1).strip() if need_match else "",
            "direction": dir_match.group(1).strip() if dir_match else "",
            "priority": pri_match.group(1).strip() if pri_match else "",
        })

    gaps.sort(key=lambda g: -g["stars"])
    return gaps


def propose_bridge(gap: Dict) -> Optional[Dict]:
    """
    对给定缺口, 在因果图中搜索可能的桥接。
    
    策略:
      - 缺口涉及 '孤岛': 找该域的变量, 看它们和 action 主干之间缺什么边
      - 缺口涉及 '桥': 找两个域的变量对, 算因果相似度
    """
    from physics.laws import library, classify_variable
    from inference.counterfactual_chain import propagate

    gap_name = gap["name"].lower()

    proposals = []

    if "孤岛" in gap_name or "不连通" in gap["status"]:
        # 找缺口涉及的关键变量
        keywords = []
        if "电磁" in gap_name or "charge" in gap_name or "current" in gap_name:
            keywords = ["charge", "current", "electric", "magnetic"]
        elif "kk" in gap_name or "compact" in gap_name:
            keywords = ["compact_dimension", "higher_d_metric", "gauge_field"]
        elif "量子引力" in gap_name:
            keywords = ["spacetime_curvature", "entangled_state", "wormhole"]
        elif "时间" in gap_name:
            keywords = ["time", "relaxation", "entropy"]

        # 找这些变量在图中是否可达 action
        orphan_vars = []
        for v in keywords:
            chain = propagate(v, "变化", max_depth=3, max_tier=2)
            reachable = any("entropy" in s.get("effect_variable", "") for s in chain if "error" not in s)
            if not reachable:
                orphan_vars.append(v)

        if orphan_vars:
            proposals.append({
                "type": "connect_orphan",
                "gap": gap["name"],
                "orphan_vars": orphan_vars[:3],
                "suggestion": f"需要桥接 {orphan_vars[:2]} 到因果主干",
            })

    if "桥" in gap_name or "bridge" in gap_name.lower():
        proposals.append({
            "type": "scale_bridge",
            "gap": gap["name"],
            "suggestion": gap["direction"],
        })

    return proposals[0] if proposals else None


def puzzle_cycle(verbose: bool = True) -> Dict:
    """
    一次拼图周期: 扫描缺口 → 提案 → 返回发现
    
    Returns:
        {"gaps_found": N, "proposals": [...], "new_pieces": [...]}
    """
    gaps = scan_gaps()
    if not gaps:
        return {"gaps_found": 0, "proposals": [], "new_pieces": []}

    if verbose:
        print(f"[puzzle] 扫描 {len(gaps)} 个缺口")

    proposals = []
    for gap in gaps[:3]:  # 只看 top 3
        proposal = propose_bridge(gap)
        if proposal:
            proposals.append(proposal)
            if verbose:
                print(f"  缺口: {gap['name']} ({gap['stars']}★)")
                if proposal.get("orphan_vars"):
                    print(f"    孤岛变量: {proposal['orphan_vars']}")
                print(f"    提案: {proposal['suggestion']}")

    return {
        "gaps_found": len(gaps),
        "proposals": proposals,
        "top_gap": gaps[0]["name"] if gaps else None,
        "top_gap_priority": gaps[0]["stars"] if gaps else 0,
    }


def fill_gap(gap_id: int, solution_note: str) -> bool:
    """标记缺口为已填补, 更新拼图文档"""
    path = _puzzle_path()
    if not os.path.exists(path):
        return False

    with open(path) as f:
        content = f.read()

    # 找到对应缺口, 标记为 ✅
    pattern = f"(### 缺口 {gap_id}: .+?)(\\n\\n)"
    replacement = f"\\1 ✅ 已填补 ({solution_note})\\2"
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)

    if new_content != content:
        with open(path, "w") as f:
            f.write(new_content)
        return True
    return False


def puzzle_report() -> str:
    """认知拼图状态报告"""
    gaps = scan_gaps()

    lines = ["══════ 认知拼图 ══════"]
    lines.append(f"  缺口: {len(gaps)}")

    if not gaps:
        lines.append("  所有缺口已填补!")
        return "\n".join(lines)

    lines.append("")
    for g in gaps:
        stars = "★" * g["stars"] + "☆" * (3 - g["stars"])
        lines.append(f"  [{stars}] 缺口{g['id']}: {g['name']}")
        lines.append(f"    现状: {g['status'][:80]}")
        lines.append(f"    方向: {g['direction'][:80]}")
        lines.append("")

    return "\n".join(lines)
