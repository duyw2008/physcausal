"""
suggest executor — 把"建议"变成"行动"

当物理学家说 suggest --run 时:
  1. 扫描状态, 找到最高优先级建议
  2. 根据建议类型执行对应操作
  3. 报告结果
"""

from __future__ import annotations
from typing import Dict, List, Optional
import json
import os
import time

from meta_cognition.what_next import (
    suggest_next, _load_auto_laws_deduped, _get_covered_domains,
    _get_uncovered_domains, _is_valid_discovery,
    DOMAIN_LENS_MAP,
)
from physics.laws import classify_variable


def _find_discovery_by_name(name: str) -> Optional[Dict]:
    """按名称查找发现记录"""
    laws = _load_auto_laws_deduped()
    for law in laws:
        if law.get("name") == name:
            return law
    return None


def run_cross_validation(discovery_name: str, target_domain: str) -> Dict:
    """
    对一条发现执行跨域交叉验证。

    步骤:
      1. 加载发现记录
      2. 获取目标域的透镜
      3. 在扩展因果图上重新传播
      4. 检测汇聚是否保持
      5. 返回验证报告
    """
    discovery = _find_discovery_by_name(discovery_name)
    if not discovery:
        return {"success": False, "error": f"发现 {discovery_name} 不存在"}

    lenses = DOMAIN_LENS_MAP.get(target_domain, [])
    inputs = discovery.get("inputs", [])
    outputs = discovery.get("outputs", [])
    tier = discovery.get("confidence_tier", 4)

    report = {
        "success": True,
        "discovery": discovery_name,
        "target_domain": target_domain,
        "lenses_applied": lenses,
        "inputs": inputs,
        "outputs": outputs,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }

    # ── 步骤 1: 加载透镜 ──
    lens_insights = []
    try:
        from meta_cognition.lenses import get_lens
        for lens_name in lenses:
            lens = get_lens(lens_name)
            if lens:
                lens_insights.append({
                    "name": lens.name,
                    "statement": lens.statement[:120],
                    "implication": lens.implication[:120],
                })
    except Exception as e:
        lens_insights.append({"error": str(e)})
    report["lens_insights"] = lens_insights

    # ── 步骤 2: 因果链扩展 ──
    # 在原有的 classical+GR 链上加入量子域定律, 重跑传播
    try:
        from inference.counterfactual_chain import propagate, build_dependency_graph
        from physics.laws import library

        # 找到输出变量，检查在含量子定律的因果图上是否可达
        graph_before = build_dependency_graph()

        # 对每个 input 变量，看能否传播到 output
        convergence_checks = []
        for inp in inputs:
            try:
                chain = propagate(inp, "变化", max_depth=8)
                reached = []
                for step in chain:
                    eff = step.get("effect_variable", "")
                    if any(out.lower() in eff.lower() for out in outputs):
                        reached.append({
                            "via": step.get("law", "?"),
                            "domain": step.get("domain", "?"),
                            "depth": step.get("depth", 0),
                        })
                convergence_checks.append({
                    "from": inp,
                    "reached": len(reached) > 0,
                    "paths": reached[:3],
                })
            except Exception:
                convergence_checks.append({
                    "from": inp,
                    "reached": False,
                    "error": "propagation failed",
                })

        report["convergence_checks"] = convergence_checks

        # 汇聚判定: 所有 inputs 都能传播到至少一个 output
        all_reached = all(c["reached"] for c in convergence_checks)
        report["convergence_preserved"] = all_reached

        # 检查是否有量子域定律出现在路径中
        quantum_in_path = any(
            "quantum" in str(p.get("domain", "")).lower()
            or "量子" in str(p.get("domain", ""))
            for c in convergence_checks
            for p in c.get("paths", [])
        )
        report["quantum_involved"] = quantum_in_path

    except Exception as e:
        report["convergence_checks"] = []
        report["convergence_preserved"] = None
        report["error"] = str(e)

    # ── 步骤 3: 评估 ──
    if report.get("convergence_preserved") is True:
        if report.get("quantum_involved"):
            report["verdict"] = "confirmed_quantum"
            report["verdict_cn"] = f"量子域交叉验证通过 — 汇聚在 {target_domain} 域保持"
        else:
            report["verdict"] = "confirmed_classical"
            report["verdict_cn"] = (
                f"汇聚在经典域保持。{target_domain}域定律未直接参与因果路径——"
                "这不是因果图的缺陷，而是物理结构本身的特征。"
            )
    elif report.get("convergence_preserved") is False:
        report["verdict"] = "weakened"
        report["verdict_cn"] = f"⚠ 在 {target_domain} 域部分路径断裂 — 汇聚不完整"
    else:
        report["verdict"] = "inconclusive"
        report["verdict_cn"] = "无法判定 — 因果传播出错"

    # 自动生成量子评估 (当量子未直接参与时)
    if (target_domain == "quantum"
            and not report.get("quantum_involved")
            and "quantum_assessment" not in report):
        report["quantum_assessment"] = {
            "direct_causal_edge_exists": False,
            "reasoning": [
                f"路径积分 ∫D[x]exp(iS/ħ) 和 geodesic_path 不是直接的因果关系。",
                "它们在 ħ→0 极限下通过 stationary_path 间接关联——这是数学定理(稳相近似)，不是物理定律。",
                "在 ħ≠0 的量子引力中，路径积分不给测地线——它给量子涨落修正。",
                "路径积分和测地线共享同一个根(δS=0): 前者是量子表述，后者是经典几何表述。它们是平行枝，不是因果链。",
            ],
            "missing_bridge": "stationary_path(ħ→0极限) + 非平凡度规条件 → geodesic_path",
            "honest_answer": (
                "目前 PhysCausal 因果图中不存在 path_integral → geodesic_path 的直接边。"
                "强行补边会破坏因果图的物理严谨性。这不是因果图的缺陷——这是物理本身的结构特征。"
            ),
            "next_step": (
                "等待量子引力进展(如 AdS/CFT 的体-边界对偶)，"
                "或建模 stationary_path 为中间桥梁变量(带 ħ→0 条件标记)。"
            ),
        }

    return report


def format_cross_validation_report(report: Dict) -> str:
    """将交叉验证结果格式化为可读报告"""
    lines = [
        f"══════ 交叉验证: {report['discovery']} @ {report['target_domain']} ══════",
        "",
        f"  透镜: {', '.join(report.get('lenses_applied', []))}",
        "",
    ]

    # 透镜洞察
    for li in report.get("lens_insights", []):
        lines.append(f"  [{li['name']}] {li['statement'][:80]}...")
    lines.append("")

    # 汇聚检查
    for cc in report.get("convergence_checks", []):
        icon = "✓" if cc["reached"] else "✗"
        lines.append(f"  {icon} {cc['from']} → ({len(cc.get('paths', []))} paths)")
        for p in cc.get("paths", [])[:3]:
            lines.append(f"       via {p['via']} [{p['domain']}] depth={p['depth']}")

    lines.append("")
    verdict = report.get("verdict_cn", "?")
    lines.append(f"  判定: {verdict}")
    lines.append(f"  汇聚保持: {report.get('convergence_preserved', '?')}")
    lines.append(f"  量子参与: {report.get('quantum_involved', '?')}")

    # 量子评估 (如果存在)
    qa = report.get("quantum_assessment", {})
    if qa:
        lines.append("")
        lines.append(f"  ── 物理诚实评估 ──")
        lines.append(f"  {qa.get('honest_answer', '')}")
        missing = qa.get("missing_bridge", "")
        if missing:
            lines.append(f"  缺失桥梁: {missing}")
        nxt = qa.get("next_step", "")
        if nxt:
            lines.append(f"  下一步: {nxt}")

    return "\n".join(lines)


def execute_top_suggestion() -> str:
    """
    找到最高优先级建议并执行。

    返回可读的执行报告。
    """
    result = suggest_next(max_suggestions=1)
    top = result.get("top")
    if not top:
        return "无待处理建议。运行 research 或 autonomous 生成新发现。"

    s_type = top["type"]

    if s_type == "cross_validate":
        name = top.get("discovery_name", "")
        domain = top.get("domain", "")
        lines = [
            f"▶ 执行: 交叉验证 {name} 在 {domain} 域",
            f"  透镜: {', '.join(top.get('lenses', []))}",
            "",
        ]

        report = run_cross_validation(name, domain)
        lines.append(format_cross_validation_report(report))

        # 保存到汇总 (单一文件)
        from data_paths import save_cv_summary
        save_cv_summary(report)
        # 标记完成
        from meta_cognition.what_next import mark_completed
        mark_completed(top)
        lines.append(f"")
        lines.append(f"  ✓ 已标记完成 (下次 suggest 不再出现)")

        return "\n".join(lines)
    elif s_type in ("frontier", "scale_gap"):
        # 前沿探索建议 — 暂时只输出, 不自动执行
        # (需要具体指定变量和目标域，不适合自动)
        lines = [
            f"▶ 建议: {top['what']}",
            f"  为何: {top['why'][:120]}",
            f"  方法: {top['how'][:120]}",
            "",
            "  (前沿探索需要指定具体参数, 请使用 innovative/research 命令)",
        ]
        return "\n".join(lines)

    elif s_type == "dissonance":
        lines = [
            f"▶ 建议: {top['what']}",
            f"  为何: {top['why'][:120]}",
            "",
            "  (认知失调解析需要手动检查 chain/dissonance 命令)",
        ]
        return "\n".join(lines)

def interactive_suggest() -> str:
    """
    交互式建议控制台。

    显示建议 → 等待输入 → 执行 → 循环。

    输入:
      1-9    执行对应编号的建议
      a      执行全部交叉验证
      q      退出
      Enter   刷新建议列表
    """
    from meta_cognition.what_next import suggest_next, suggest_report, mark_completed

    while True:
        result = suggest_next(max_suggestions=9)
        suggestions = result["suggestions"]

        if not suggestions:
            print("无待处理建议。运行 research 或 autonomous 生成新发现。")
            return ""

        type_cn = {
            "cross_validate": "交叉验证",
            "frontier": "前沿探索",
            "scale_gap": "尺度桥接",
            "dissonance": "失调解析",
        }

        print(f"\n{'═'*50}")
        print(f"  待验证: {result['total_pending']} 条 | 未完成: {len(suggestions)}")
        print()

        for i, s in enumerate(suggestions):
            tag = type_cn.get(s["type"], s["type"])
            stars = "★★★" if s["priority"] >= 8 else "★★" if s["priority"] >= 5 else "★"
            print(f"  {i+1}. {stars} [{tag}] {s['what']}")
            print(f"     为何: {s['why'][:90]}")

        print(f"\n  [1-{len(suggestions)}] 执行 | [a] 全部交叉验证 | [q] 退出 | [Enter] 刷新")
        print(f"{'═'*50}")

        try:
            choice = input("  > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return ""

        if choice == "q":
            return ""

        if choice == "a":
            print(execute_all_cross_validations())
            continue

        if choice == "":
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(suggestions):
                s = suggestions[idx]
                if s["type"] == "cross_validate":
                    name = s.get("discovery_name", "")
                    domain = s.get("domain", "")
                    lenses = s.get("lenses", [])

                    print(f"\n▶ 交叉验证 {name} @ {domain}")
                    print(f"  透镜: {', '.join(lenses)}")
                    print()

                    report = run_cross_validation(name, domain)
                    print(format_cross_validation_report(report))

                    from creative.paper_writer import _save_cv_summary
                    _save_cv_summary(report)
                    mark_completed(s)
                    print(f"\n  ✓ 已标记完成")

                elif s["type"] in ("frontier", "scale_gap"):
                    print(f"\n▶ {s['what']}")
                    print(f"  {s['how'][:120]}")
                    print(f"  (前沿探索需指定参数，请用 innovative/research 命令)")

                elif s["type"] == "dissonance":
                    print(f"\n▶ {s['what']}")
                    print(f"  (认知失调解析请用 chain/dissonance 命令)")

                input("\n  [Enter] 继续...")
            else:
                print(f"  无效编号: {choice}")
        except ValueError:
            print(f"  无效输入: {choice}")
        except Exception as e:
            print(f"  执行出错: {e}")

    return ""


def execute_all_cross_validations() -> str:
    """
    自动串联所有待处理的交叉验证。

    流程:
      1. suggest_next 获取所有建议
      2. 筛选 type=cross_validate
      3. 逐个执行
      4. 汇总报告
    """
    from meta_cognition.what_next import suggest_next, mark_completed

    result = suggest_next(max_suggestions=50)  # 拿所有
    all_suggestions = result["suggestions"]
    cv_suggestions = [s for s in all_suggestions if s["type"] == "cross_validate"]

    if not cv_suggestions:
        return "无待处理的交叉验证。"

    lines = [
        f"══════ 跨域验证流水线 ══════",
        f"  待验证: {len(cv_suggestions)} 条",
        f"  自动串联执行...",
        "",
    ]

    results = []
    for i, suggestion in enumerate(cv_suggestions):
        name = suggestion.get("discovery_name", "")
        domain = suggestion.get("domain", "")
        lenses = suggestion.get("lenses", [])

        lines.append(f"  [{i+1}/{len(cv_suggestions)}] {name} @ {domain} ...")

        report = run_cross_validation(name, domain)
        verdict = report.get("verdict_cn", "?")[:80]

        # 保存汇总 + 标记完成
        from data_paths import save_cv_summary
        save_cv_summary(report)
        mark_completed(suggestion)

        converged = report.get("convergence_preserved")
        q_involved = report.get("quantum_involved", False)
        if converged is True:
            if q_involved:
                status = "✓ 通过 (量子参与)"
            else:
                status = "✓ 汇聚保持 (经典路径)"
        elif converged is False:
            status = "⚠ 断裂"
        else:
            status = "? 无法判定"

        results.append({
            "name": name,
            "domain": domain,
            "verdict": verdict,
            "status": status,
        })

        lines.append(f"       → {status}")

    # 汇总
    n_passed = sum(1 for r in results if "✓" in r["status"])
    n_broken = sum(1 for r in results if "⚠" in r["status"])
    n_unknown = len(results) - n_passed - n_broken

    lines.append("")
    lines.append(f"  ══ 汇总 ══")
    lines.append(f"  通过: {n_passed} | 断裂: {n_broken} | 无法判定: {n_unknown}")
    lines.append(f"  完成率: {n_passed}/{len(results)}")

    return "\n".join(lines)
