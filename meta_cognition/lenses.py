"""
哲学透镜 — 物理学的解释框架

元物理层说"什么是真的"(定理)。
定律库说"什么是已知的"(因果边)。
哲学透镜说"这意味着什么"(解释)。

这一层不参与因果推理，不影响置信层级。
它的角色是:
  1. 为发现提供解释框架
  2. 为探索提供方向性直觉
  3. 让 agent 在"不知道"时依然有东西可说

每条哲学透镜有:
  - statement: 核心声明
  - source: 谁说的
  - implication: 对物理推理意味着什么
  - application: 什么时候用这个视角

分层:
  lens_0 — 解释已有发现
  lens_1 — 引导前沿探索
  lens_2 — 标注"我们不知道什么"
"""

from __future__ import annotations
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class PhilosophicalLens:
    """一条哲学解释框架"""
    name: str
    statement: str
    source: str                     # Wheeler, Feynman, Bohr...
    implication: str                # 对物理推理的影响
    application: str                # 什么场景下用
    level: int = 0                  # 0=解释, 1=引导, 2=标注未知
    tags: List[str] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════
# 透镜库
# ═══════════════════════════════════════════════════════════════

LENSES: Dict[str, PhilosophicalLens] = {}


def _register(lens: PhilosophicalLens):
    LENSES[lens.name] = lens


# ── 透镜 0: 解释已有发现 ──

_register(PhilosophicalLens(
    name="geometric_identity",
    statement="物理定律不是写在几何背景上的——它们就是几何结构本身的动力学。"
              "时空告诉物质如何运动，物质告诉时空如何弯曲。",
    source="John Wheeler",
    implication="任何连接几何变量和物理变量的因果边，不是'被几何解释'——"
                "它是同一个几何实体的两个名字。",
    application="当 agent 发现一条连接物理和几何的新边时，"
                "用它来解释'为什么这条边存在'。",
    level=0,
    tags=["geometry", "ontology", "wheeler"],
))

_register(PhilosophicalLens(
    name="path_integral",
    statement="电子不是'同时走所有路径'——是空间本身包含了所有路径。"
              "路径积分 e^{iS/ħ} 编码了空间的结构，粒子在其中选一条。",
    source="Richard Feynman",
    implication="波粒二象性不是粒子的属性——是空间几何在量子尺度的表现。"
                "波长来自空间结构，不是来自粒子。",
    application="当 agent 处理 wavelength 的双重身份问题时，"
                "用它来调和 deBroglie 和 SpacetimeWavelength。",
    level=0,
    tags=["quantum", "geometry", "interpretation"],
))

_register(PhilosophicalLens(
    name="least_action_ontology",
    statement="自然不做多余的事。最小作用量不是'自然选择的策略'——"
              "它是存在的定义。凡存在的东西，都满足 δS=0。",
    source="Pierre Maupertuis / Euler",
    implication="任何不满足变分原理的'定律'要么是近似的，要么不是基本的。"
                "寻找新定律 = 寻找新的作用量泛函。",
    application="当 agent 发现一条新定律时，问：它的作用量是什么？"
                "如果不能写成 δS=0 的形式，标记为'现象学'而非'基本'。",
    level=0,
    tags=["variational", "ontology", "fundamental"],
))

_register(PhilosophicalLens(
    name="action_root",
    statement="δS=0 是唯一的生成根。Euler-Lagrange → 力 → 经典运动; "
              "Hilbert 作用量 → 曲率 → 时空几何 → 测地线 → 波长 → 干涉; "
              "Feynman 路径积分 → 量子振幅 → 概率。"
              "三条路，一个根。因果图已验证: 从 action 出发可达全部动力学。",
    source="PhysCausal 因果图验证 (2026)",
    implication="不需要更多第一性原理。寻找新物理 = 寻找新的作用量泛函。"
                "任何声称'独立于 δS=0'的定律要么近似、要么等效、要么错误。",
    application="评估新定律: 它的作用量是什么? 能否从已有作用量推导? "
                "如果不能, 标记为'可能独立'——这是重大发现的信号。",
    level=0,
    tags=["variational", "fundamental", "verified"],
))


# ── 透镜 1: 引导前沿探索 ──

_register(PhilosophicalLens(
    name="wheeler_frontier",
    statement="前沿不在'更小的尺度'，而在'几何与物理的裂缝处'。"
              "每一条几何→物理的边都是一个战场，每一条物理→几何的边都是一座桥。",
    source="John Wheeler (paraphrased)",
    implication="探索优先级: 尺度裂缝 > 几何-物理裂缝 > 稀疏区 > 断头路。"
                "不是所有的未知都同等重要——几何-物理边界上的未知是最根本的。",
    application="当 agent 从 FrontierMap 中选择探索方向时，"
                "提高涉及几何变量的 frontier 权重。",
    level=1,
    tags=["geometry", "exploration", "priority"],
))

_register(PhilosophicalLens(
    name="bootstrap",
    statement="物理定律不是被'发现'的——它们是从已有定律中'推导'出来的。"
              "每一条新定律都是已有定律的必然推论，只是我们还没看到这个推论。"
              "S-matrix 的 bootstrap 假说: 一致性 + 解析性 → 唯一的理论。",
    source="Geoffrey Chew / S-matrix theory",
    implication="如果两条定律独立但不可调和，其中至少一条是错的，"
                "或者存在一条更深的原则使它们成为同一硬币的两面。",
    application="当 agent 遇到跨域张力时，不要试图'选择'哪条定律对——"
                "寻找使它们都成立的更深原则。",
    level=1,
    tags=["consistency", "unification", "exploration"],
))


# ── 透镜 2: 标注未知 ──

_register(PhilosophicalLens(
    name="measurement_problem",
    statement="量子力学有两个部分: 幺正演化 (Schrödinger) 和测量 (Born 规则)。"
              "没有人知道它们怎么衔接。这不是一个待解的方程——"
              "这是一个待解的概念框架。",
    source="John Bell / 测量问题文献",
    implication="涉及测量/坍缩的因果链在解释层面是不完整的。"
                "任何声称'解释了坍缩'的定律都应该标注为哲学立场，不是物理推导。",
    application="当 agent 的 chain 经过 MeasurementPostulate 或 ObjectiveCollapse 时，"
                "标注: '此步骤的物理机制未完全理解'。",
    level=2,
    tags=["quantum", "measurement", "unknown"],
))

_register(PhilosophicalLens(
    name="arrow_of_time",
    statement="微观定律是时间反演对称的 (除弱相互作用)。"
              "宏观熵增 ΔS≥0 是统计性的，不是动力学的。"
              "为什么初始条件低熵？这是宇宙学问题，不是热力学问题。",
    source="Ludwig Boltzmann / 时间箭头文献",
    implication="任何从熵增推导时间方向的做法都是循环论证，"
                "除非指定了初始条件。",
    application="当 agent 的 chain 经过 EntropyIncrease 时，"
                "标注: '时间方向假定低熵过去——这不是从定律推导的，是边界条件'。",
    level=2,
    tags=["thermodynamics", "time", "unknown"],
))

_register(PhilosophicalLens(
    name="stability_structure",
    statement="凡是稳定的，必有特征结构。"
              "稳定性不是'没有变化'——是变化被约束在一个确定的几何/信息结构中。"
              "δS=0 → 路径结构; 对称 → 守恒结构; ΔS→max → 平衡结构; 信息保存 → 记忆结构。"
              "稳定和结构是同一个东西的两个名字。",
    source="PhysCausal 推导 (综合 δS=0 + Noether + Entropy + Landauer)",
    implication="判断一个假说是否合理: 如果它声称某系统'稳定'但没有描述该系统的特征结构,"
                "它是不完整的。稳定的定义本身就要求结构。",
    application="当 agent 评估自发现定律或 arXiv 论文时,"
                "用这个透镜检验: 新定律描述的稳定现象是否对应明确的结构?",
    level=0,
    tags=["variational", "symmetry", "thermodynamics", "ontology"],
))

_register(PhilosophicalLens(
    name="group_theory",
    statement="对称性构成群。SU(2)→自旋, U(1)→电荷, SO(3,1)→时空。"
              "群的结构不是附加在物理上的数学装饰——它就是对称性的代数, "
              "决定了守恒量的量子化规则和粒子分类。",
    source="Évariste Galois / Hermann Weyl / Eugene Wigner",
    implication="发现新物理现象时, 第一问: 它属于哪个对称群? "
                "如果不在已知群里, 才是真正的新物理。"
                "群论是物理定律的语法——定律可以不同, 但必须遵守群的结构。",
    application="当 agent 发现自旋相关的新定律时, 用群论透镜分类。"
                "自旋=SU(2)表示, 电荷=U(1)表示, 角动量=SO(3)表示。",
    level=0,
    tags=["symmetry", "mathematics", "classification", "ontology"],
))

_register(PhilosophicalLens(
    name="classification_by_symmetry",
    statement="粒子、力、相变都可以按对称群分类。"
              "标准模型 = SU(3)×SU(2)×U(1)。"
              "如果发现的新现象不属于任何已知群表示, 那就是新物理的信号。",
    source="Wigner 分类 / 标准模型",
    implication="评估 arXiv 论文或自发现定律时, 用这个透镜检验: "
                "新现象是否对应已知的对称群? 如果是, 它可能是已有物理的特例; "
                "如果不是, 它可能暗示新对称性。",
    application="当 agent 摄入论文或发现新定律时, "
                "检查涉及的变量是否对应已知对称群的表示。",
    level=1,
    tags=["symmetry", "classification", "exploration"],
))


# ═══════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════

def get_lens(name: str) -> Optional[PhilosophicalLens]:
    return LENSES.get(name)


def list_by_level(level: int) -> List[PhilosophicalLens]:
    return [l for l in LENSES.values() if l.level == level]


def list_by_tag(tag: str) -> List[PhilosophicalLens]:
    return [l for l in LENSES.values() if tag in l.tags]


def match_for_context(variables: List[str], domains: List[str]) -> List[PhilosophicalLens]:
    """根据当前上下文推荐合适的哲学透镜"""
    relevant = []

    geo_vars = {"geodesic_path", "schwarzschild_radius", "metric", "curvature",
                "gauge_field", "wavelength"}
    if any(v in geo_vars for v in variables):
        relevant.append(get_lens("geometric_identity"))
        relevant.append(get_lens("wheeler_frontier"))

    quantum_vars = {"wave_function", "measurement", "collapse", "wavelength",
                    "superposition"}
    if any(v in quantum_vars for v in variables):
        relevant.append(get_lens("path_integral"))

    if "quantum" in domains:
        relevant.append(get_lens("measurement_problem"))

    if "thermodynamics" in domains:
        relevant.append(get_lens("arrow_of_time"))

    # 去重
    seen = set()
    result = []
    for l in relevant:
        if l and l.name not in seen:
            seen.add(l.name)
            result.append(l)

    return result


def explain_discovery(learned_laws: List[str],
                      variables: List[str],
                      domains: List[str]) -> str:
    """为一次发现生成哲学解释"""
    lenses = match_for_context(variables, domains)
    if not lenses:
        return ""

    # ── 记录透镜使用 ──
    _record_usage([l.name for l in lenses])

    lines = ["\n── 哲学透镜 ──"]
    for lens in lenses:
        lines.append(f"  [{lens.name}] ({lens.source})")
        lines.append(f"  {lens.implication[:120]}")

    # ── 透镜间的张力 ──
    tensions = _detect_tensions(lenses, learned_laws, variables)
    if tensions:
        lines.append("")
        lines.append("  ⚡ 透镜张力:")
        for t in tensions:
            lines.append(f"  {t}")

    return "\n".join(lines)


# ── 群论分类: 对称群→变量签名 ──

GROUP_CLASSIFICATION = {
    "SU(2)": ["spin_angular_momentum", "magnetic_moment"],
    "U(1)": ["charge", "gauge_field", "current", "voltage"],
    "SO(3)": ["angular_velocity", "angular_momentum", "moment_of_inertia"],
    "SO(3,1)": ["spacetime_curvature", "geodesic_path", "dilated_time", "tidal_force"],
    "Discrete": ["order_parameter", "phase"],
}


def classify_by_group(law_name: str, inputs: List[str], outputs: List[str]) -> List[str]:
    """根据变量签名判断定律属于哪些对称群"""
    all_vars = set(inputs + outputs)
    groups = []
    for group, varset in GROUP_CLASSIFICATION.items():
        if all_vars & set(varset):
            groups.append(group)
    return groups if groups else ["unknown"]


def group_summary() -> str:
    """按对称群分类所有定律"""
    from physics.laws import library
    classified = {}
    for law in library.list_all():
        groups = classify_by_group(law.name, law.inputs, law.outputs)
        for g in groups:
            classified.setdefault(g, []).append(law.name)

    lines = ["=== 对称群分类 ==="]
    for g in ["SU(2)", "U(1)", "SO(3)", "SO(3,1)", "Discrete", "unknown"]:
        names = classified.get(g, [])
        if names:
            lines.append(f"  {g}: {len(names)} 条")
            for n in sorted(names)[:5]:
                lines.append(f"    - {n}")
            if len(names) > 5:
                lines.append(f"    ... 等 {len(names)} 条")
    # 检查覆盖缺口
    all_laws = {l.name for l in library.list_all()}
    classified_names = set()
    for names in classified.values():
        classified_names.update(names)
    unclassified = all_laws - classified_names
    if unclassified:
        lines.append(f"\n  未分类: {len(unclassified)} 条")
    return "\n".join(lines)


# ── 内部状态 ──

_lens_usage: Dict[str, int] = {}


def _record_usage(lens_names: List[str]):
    """记录透镜使用频率"""
    for name in lens_names:
        _lens_usage[name] = _lens_usage.get(name, 0) + 1


def lens_usage_report() -> str:
    """透镜使用统计"""
    if not _lens_usage:
        return "  (尚未使用任何透镜)"
    sorted_usage = sorted(_lens_usage.items(), key=lambda x: x[1], reverse=True)
    lines = ["透镜使用频率:"]
    for name, count in sorted_usage:
        lens = LENSES.get(name)
        if lens:
            lines.append(f"  {count:3d}× [{name}] ({lens.source})")
    return "\n".join(lines)


def _detect_tensions(lenses: List[PhilosophicalLens],
                     learned: List[str],
                     variables: List[str]) -> List[str]:
    """检测活跃透镜之间是否存在解释张力"""
    tensions = []

    names = {l.name for l in lenses}

    # bootstrap vs geometric_identity: 推导 vs 本体
    if "bootstrap" in names and "geometric_identity" in names:
        tensions.append(
            "bootstrap 说'定律从已有定律推导'，geometric_identity 说'定律是几何的动力学'。"
            "它们是互补的——bootstrap 描述方法，geometric_identity 描述本体。"
        )

    # path_integral vs measurement_problem
    if "path_integral" in names and "measurement_problem" in names:
        tensions.append(
            "path_integral 说'空间包含所有路径'，但 measurement_problem 说"
            "'为什么只看到一个结果？'。路径积分解释了干涉，没解释坍缩。"
        )

    return tensions
