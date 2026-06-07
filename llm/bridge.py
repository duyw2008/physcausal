"""
LLM 桥接 — 自然语言 ↔ PhysCausal 管道

将 DeepSeek LLM 接入 PhysCausal Pipeline:

  "力和质量如何影响加速度？"
    → LLM 提取因果图: Force→Acceleration, Mass→Acceleration
    → PhysCausal 生成合成数据 + 因果发现 + 效应估计
    → LLM 生成自然语言解读
    → "力每增加 1N，加速度增加约 1/m m/s²。质量增加抑制加速度。"

五步管道:
  1. LLM 提取因果图 (语言→结构)
  2. 数据生成 (从 DAG 构造 SCM, 采样)
  3. 物理约束 (PhysicsConstrainedDAG + 元物理过滤)
  4. 效应估计 (识别→估计→显著性)
  5. LLM 自然语言解读 (数字→中文)
"""

from __future__ import annotations
import json, re
from typing import Any, Dict, List, Optional
import numpy as np


# ═══════════════════════════════════════════════════════════════
# LaTeX → Unicode 转换器
# ═══════════════════════════════════════════════════════════════

_LATEX_UNICODE = {
    # Greek
    r"\Delta": "Δ", r"\delta": "δ", r"\sigma": "σ", r"\Sigma": "Σ",
    r"\pi": "π", r"\Pi": "Π", r"\lambda": "λ", r"\Lambda": "Λ",
    r"\omega": "ω", r"\Omega": "Ω", r"\psi": "ψ", r"\Psi": "Ψ",
    r"\phi": "φ", r"\Phi": "Φ", r"\theta": "θ", r"\Theta": "Θ",
    r"\rho": "ρ", r"\alpha": "α", r"\beta": "β", r"\gamma": "γ",
    r"\epsilon": "ε", r"\varepsilon": "ε", r"\mu": "μ", r"\nu": "ν",
    r"\tau": "τ", r"\eta": "η", r"\xi": "ξ", r"\zeta": "ζ",
    r"\chi": "χ", r"\kappa": "κ",
    # Math operators and symbols
    r"\geq": "≥", r"\leq": "≤", r"\approx": "≈", r"\equiv": "≡",
    r"\propto": "∝", r"\sim": "∼", r"\neq": "≠", r"\pm": "±",
    r"\mp": "∓", r"\times": "×", r"\cdot": "·", r"\cdots": "⋯",
    r"\infty": "∞", r"\partial": "∂", r"\nabla": "∇",
    r"\int": "∫", r"\oint": "∮", r"\sum": "∑", r"\prod": "∏",
    r"\sqrt": "√", r"\rightarrow": "→", r"\Rightarrow": "⇒",
    r"\leftarrow": "←", r"\Leftarrow": "⇐",
    r"\nRightarrow": "⇏", r"\longrightarrow": "⟶",
    r"\langle": "⟨", r"\rangle": "⟩",
    r"\hbar": "ℏ", r"\mathcal{E}": "ℰ", r"\mathcal{E}": "ℰ",
    # Fractions (simple: \frac{a}{b} → a/b)
    # Subscripts/superscripts handled separately
    r"\text{entanglement}": "entanglement",
    r"\text{signaling}": "signaling",
    r"\text{gravity}": "gravity",
    r"\text{acceleration}": "acceleration",
    # Clean up
    r"\{": "", r"\}": "", r"\\": "",
}

def _latex_to_unicode(latex: str) -> str:
    """将 LaTeX 公式转为 Unicode 显示"""
    s = latex
    # Replace known patterns
    for lt, uni in _LATEX_UNICODE.items():
        s = s.replace(lt, uni)
    # Simple fractions: \frac{a}{b} → a/b
    s = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'\1/\2', s)
    # Remove remaining {} and backslashes
    s = s.replace("{", "").replace("}", "")
    # Subscripts: _{...} → 保持原文 (如 r_s → r_s)
    # Superscripts: ^{...} → 保持原文
    s = re.sub(r'_{([^}]+)}', r'_\1', s)
    s = re.sub(r'\^{([^}]+)}', r'^\1', s)
    # text{} → just the content
    s = re.sub(r'\\text\{([^}]+)\}', r'\1', s)
    return s.strip()


class LLMBridge:
    """
    LLM ↔ PhysCausal 桥接器。

    LLM 做翻译 (语言↔结构)，PhysCausal 做推理 (因果+物理)。
    """

    def __init__(self, client=None):
        if client is None:
            try:
                from causal.llm_client import DeepSeekClient
                client = DeepSeekClient()
            except Exception:
                client = None
        self.client = client
        self._last_graph: Optional[Dict] = None

    def is_available(self) -> bool:
        return self.client is not None and bool(
            getattr(self.client, 'api_key', '')
        )

    # ═══ Step 1: LLM → 因果图 ═══

    THEORY_KEYWORDS = ["如果", "假如", "假设", "要是", "推理", "推导", "为什么",
                       "怎么", "如何影响", "如何计算", "证明", "理论上",
                       "会不会", "是否", "有没有", "谁更", "哪个更", "更高", "更快",
                       "更强", "更大", "更小", "更重", "更轻",
                       "是什么关系", "有什么关系", "有何关系", "什么关系",
                       # 因果方向提问
                       "原因还是结果", "是因还是果", "谁是因谁是果",
                       "谁是因", "谁是果", "哪个是因", "哪个是果",
                       # 假设后果提问 (无"如果"的条件句)
                       "会怎样", "会如何", "会怎么", "会变化",
                       # 定律/概念解释提问
                       "说的是什么", "是什么", "什么是", "什么意思",
                       "定义", "解释一下", "介绍一下",
                       # 元物理/哲学问题
                       "稳定", "结构", "原理", "定律", "规则",
                       "本质", "根本", "底层", "基础"]

    # 物理理论概念 — 匹配到这些且没有具体变量名 → 理论模式
    PHYSICS_THEORY_CONCEPTS = [
        "熵", "时间方向", "时间箭头", "不可逆", "最小作用", "对称性",
        "守恒", "noether", "波函数", "量子", "相对论", "光速不变",
        "等效原理", "不确定性", "测不准", "薛定谔", "波粒二象",
        "熵增", "热寂", "麦克斯韦妖", "因果律", "决定论",
        "涌现", "重整化", "粗粒化", "全息原理",
        # 常见物理量 (配合因果方向提问时触发)
        "温度升高", "分子运动", "分子动能", "热运动",
        "光速", "时空弯曲", "引力波", "暗能量", "暗物质",
        # 元物理/信息
        "稳定结构", "特征结构", "信息熵", "Landauer",
    ]

    def _is_physics_question(self, question: str) -> bool:
        """
        语义分类: 这个问题的本质是物理原理推导, 还是经验因果推断?

        用 LLM 做一次性判断, 不依赖关键词列表。
        LLM 不可用时回退到关键词系统。
        """
        if not self.is_available():
            return False  # 回退到 _is_theoretical + _mentions_physics

        prompt = (
            "判断以下问题是询问物理学/自然科学原理, 还是社会科学/经验因果效应。\n\n"
            "物理学问题 (physics): 问的是自然界规律和机制。\n"
            "  例: '铁球和羽毛谁先落地', '力和加速度的关系', '光速为什么是极限', "
            "'温度升高是原因还是结果', '量子纠缠能超光速吗'。\n\n"
            "经验因果问题 (empirical): 问的是社会/经济/医学中的因果关系, 需要数据来回答。\n"
            "  例: '教育如何影响收入', '药物对康复时间的影响', '广告对销量的效应', "
            "'运动能减肥吗', '吸烟与肺癌的关系'。\n\n"
            f"问题: {question}\n\n"
            "只回答一个词: physics 或 empirical"
        )
        try:
            response = self.client.chat([{"role": "user", "content": prompt}])
            return "physics" in response.lower()[:20]
        except Exception:
            return False

    def _mentions_physics(self, question: str) -> bool:
        """检测问题是否涉及已知物理变量或物理场景"""
        PHYSICS_VARIABLES = [
            # 力学
            "力", "质量", "加速度", "速度", "位移", "动量", "动能", "势能",
            "弹性", "弹簧", "摩擦", "重力", "引力",
            # 电磁
            "电压", "电流", "电阻", "电荷", "电场", "磁场", "磁通量",
            "感应", "电容", "电感",
            # 热力学
            "温度", "热量", "热", "压力", "体积", "熵", "热力学",
            "分子运动", "分子动能",
            # 光学/声学
            "光", "折射", "反射", "波长", "频率", "声", "波速",
            # 量子/相对论
            "量子", "光子", "电子", "波函数", "纠缠", "光速",
            "坍缩", "本征态", "本征值", "测量公设", "退相干",
            "时间膨胀", "黑洞", "事件视界",
            # Jacobi / Kaluza-Klein / 几何化
            "测地线", "度规", "投影", "高维", "紧致化", "Kaluza", "Jacobi",
            # 流体
            "浮力", "流速", "密度", "压强",
            # 物理场景 (实验/思想实验)
            "落地", "自由落体", "下落", "扔下", "掉下", "落下",
            "铁球", "羽毛", "铅球", "真空", "空气阻力",
            "碰撞", "弹回", "反弹", "摆", "单摆", "钟摆",
            "漂浮", "沉没", "轨道", "绕", "公转",
            # 天文
            "太阳", "地球", "自转", "东边升起", "日出", "日落",
            "月球", "行星", "卫星", "日食", "月食", "潮汐",
        ]
        return any(var in question for var in PHYSICS_VARIABLES)

    def _is_theoretical(self, question: str) -> bool:
        """检测是否是理论推导问题 (不需要数据, 只需定律+数学)"""
        if any(kw in question for kw in self.THEORY_KEYWORDS):
            return True
        # 检查是否在问物理理论概念 (没有具体变量名时)
        if any(concept in question for concept in self.PHYSICS_THEORY_CONCEPTS):
            # 确认不是在问具体因果效应 (没有明确的 treatment/outcome 变量)
            import re
            # 检测是否包含"影响"+"什么"这类因果效应提问
            effect_pattern = re.search(r'(.+?)(影响|导致|造成|引起)(.+?)(吗|？|\?)', question)
            if not effect_pattern:
                return True
        return False

    def _theory_context(self, question: str) -> str:
        """
        为理论问题注入相关物理定律 (不是全部 88 条，而是与问题相关的)。

        过滤策略: 问题中提到变量名 → 定律包含该变量 → 注入
                 问题中提到领域词 → 注入该领域全部定律
                 无匹配 → 注入元物理原则 (兜底)
        """
        from physics.laws import library

        all_laws = library.list_all()

        # 关键词→领域映射
        DOMAIN_KEYWORDS = {
            "mechanics": ["力", "质量", "加速度", "速度", "位移", "动量", "动能",
                          "弹簧", "摆", "碰撞", "弹性", "摩擦", "重力", "引力"],
            "electromagnetism": ["电压", "电流", "电阻", "电荷", "电场", "磁场",
                                  "电磁", "感应", "电容", "电感", "磁通"],
            "thermodynamics": ["温度", "热", "热量", "压力", "体积", "熵", "热力学"],
            "quantum": ["量子", "波函数", "坍缩", "本征", "退相干", "纠缠", "光子",
                        "电子", "泡利", "测不准", "不确定性", "薛定谔", "波粒"],
            "general_relativity": ["相对论", "光速", "时空", "黑洞", "时间膨胀",
                                    "引力波", "史瓦西", "等效原理"],
            "optics": ["光", "折射", "反射", "波长", "透镜", "焦距"],
            "acoustics": ["声", "波速", "频率", "多普勒"],
            "fluids": ["流体", "浮力", "流速", "密度", "压强"],
            "unification": ["高维", "投影", "测地线", "度规", "Kaluza", "Jacobi"],
        }

        # 确定相关领域
        relevant_domains = set()
        for domain, keywords in DOMAIN_KEYWORDS.items():
            if any(kw in question for kw in keywords):
                relevant_domains.add(domain)

        # 如果匹配到具体领域，只注入这些领域 + 元物理原则
        if relevant_domains:
            filtered_laws = [law for law in all_laws
                             if law.domain in relevant_domains
                             or law.domain in ("meta_physics",)]
            # 加上通用的物理原则: Newton II (F=ma 几乎总是相关的)
            for law in all_laws:
                if law.name in ("Newton II", "Locality", "NoCommunication"):
                    if law not in filtered_laws:
                        filtered_laws.append(law)
        else:
            # 无匹配 → 注入全部 (兜底)
            filtered_laws = all_laws

        lines = ["你是一个精通理论物理推导的科学家。"]
        lines.append("请使用 Unicode 数学符号 (如 ΔS ≥ 0, F = ma, ω = √(k/m)), 不要用 LaTeX。")

        if relevant_domains:
            lines.append(f"以下是 PhysCausal 定律库中与问题相关的 {len(filtered_laws)}/{len(all_laws)} 条定律 "
                         f"(领域: {', '.join(sorted(relevant_domains))}):")
        else:
            lines.append(f"以下是 PhysCausal 物理定律库中的全部 {len(all_laws)} 条定律:")
        lines.append("")

        for law in filtered_laws:
            eq = law.latex if hasattr(law, 'latex') and law.latex else law.name
            # LaTeX → Unicode 转换
            eq_u = _latex_to_unicode(eq)
            lines.append(f"  {law.name} ({law.domain}): {eq_u}")
            if law.causal_direction:
                dirs = [f"{s}→{d}" for s, d in law.causal_direction]
                lines.append(f"    因果方向: {', '.join(dirs)}")
            if law.forbidden_directions:
                dirs = [f"{s}→{d}" for s, d in law.forbidden_directions[:3]]
                lines.append(f"    禁止: {', '.join(dirs)}")
            if getattr(law, 'collapse_timescale', None):
                lines.append(f"    坍缩时间尺度: {law.collapse_timescale}")
            lines.append("")

        lines.append("")
        lines.append("推理方法 (矛盾驱动):")
        lines.append("1. 先扫描问题中涉及的概念，找出定律库中覆盖这些概念的多条定律")
        lines.append("2. 如果多条定律对同一现象给出了不同的约束 (不同的时间尺度、不同的因果方向、不同的理论框架)，")
        lines.append("   这就是矛盾的起点——不要跳过它，以矛盾为线索组织分析")
        lines.append("3. 逐一分析每个框架下的推导路径和结论")
        lines.append("4. 说明分歧的根源 (是公设差异? 尺度边界? 理论范式不同?)")
        lines.append("5. 给出综合结论，诚实标注哪些是确定的、哪些是解释分歧")
        lines.append("")
        lines.append("请基于以上定律进行推导，使用 Unicode 数学符号。")
        return "\n".join(lines)

    def _all_law_variables(self) -> list:
        from physics.laws import library
        vars_ = set()
        for law in library.list_all():
            vars_.update(law.inputs)
            vars_.update(law.outputs)
        return list(vars_)

    CAUSAL_GRAPH_PROMPT = """你是一个因果推断专家。从以下自然语言描述中提取因果图。
{{
  "variables": ["变量1", "变量2", ...],
  "edges": [["原因", "结果"], ...],
  "confounders": [["混杂变量1", "混杂变量2"], ...],
  "treatment": "处理变量名",
  "outcome": "结果变量名",
  "explanation": "一句话解释变量和边的关系"
}}

规则:
  - 变量名用中文简短命名
  - 每条边表示直接因果关系
  - 混淆变量是同时影响 treatment 和 outcome 的变量
  - treatment 是描述中问的主要干预, outcome 是描述中问的主要结果
  - 如果描述中没有混杂变量, confounders 为空数组
"""

    def extract_graph(self, question: str) -> Dict:
        """从自然语言描述中提取因果图"""
        if not self.is_available():
            return self._fallback_graph(question)

        # 注入物理上下文 — 让 LLM 知道不该漏掉哪些变量
        physics_hint = self._detect_physics_context(question)
        prompt = self.CAUSAL_GRAPH_PROMPT.format(question=question)
        if physics_hint:
            prompt += f"\n\n物理定律提示 (根据问题自动检测):\n{physics_hint}\n请确保因果图包含这些定律中涉及的所有变量。"
        try:
            response = self.client.chat([
                {"role": "user", "content": prompt}
            ])
            # Check for API error
            if '"error"' in response[:20]:
                return self._fallback_graph(question)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                graph = json.loads(json_match.group())
                # Validate required fields
                if graph.get("variables"):
                    self._last_graph = graph
                    return graph
                # variables 非空就够了 — edges 可以为空 (表示无因果关系)
        except Exception:
            pass

        return self._fallback_graph(question)

    def _detect_physics_context(self, question: str) -> str:
        """
        检测问题涉及的物理领域，返回相关定律提示。

        让 LLM 知道: 这个问题涉及哪些物理变量，不能漏掉。
        """
        hints = []

        # 关键词 → 变量映射
        KEYWORD_MAP = {
            "电压": ["voltage", "电阻", "current", "Ohm: V=IR"],
            "电流": ["current", "电压", "电阻", "Ohm: V=IR"],
            "电阻": ["resistance", "电压", "电流", "Ohm: V=IR"],
            "力": ["force", "mass", "acceleration", "Newton: F=ma"],
            "加速度": ["acceleration", "force", "mass", "Newton: F=ma"],
            "质量": ["mass", "force", "acceleration", "Newton: F=ma"],
            "温度": ["temperature", "kinetic_energy", "Kinetic Theory: KE→T"],
            "分子运动": ["kinetic_energy", "temperature", "Kinetic Theory: KE→T"],
            "弹": ["elastic_constant", "displacement", "force", "Hooke: F=-kx"],
            "折射": ["incident_angle", "refraction_angle", "refractive_index", "Snell"],
            "磁": ["magnetic_flux_change", "induced_emf", "Faraday"],
            "频率": ["frequency", "wavelength", "wave_speed", "Doppler"],
            "摆": ["length", "gravity", "period", "Pendulum: T=2π√(L/g)"],
            # 新增 9 条
            "引力": ["mass", "distance", "force_gravity", "Gravity: F=GMm/r²"],
            "重力": ["mass", "acceleration", "force", "Gravity: F=mg"],
            "碰撞": ["m1", "m2", "v1", "v2", "Momentum: conservation"],
            "动量": ["mass", "velocity", "momentum", "Momentum: p=mv"],
            "透镜": ["object_distance", "focal_length", "image_distance", "Lens: 1/f=1/u+1/v"],
            "焦距": ["focal_length", "object_distance", "image_distance", "Lens"],
            "气体": ["pressure", "volume", "temperature", "Ideal Gas: PV=nRT"],
            "气压": ["pressure", "volume", "temperature", "Ideal Gas"],
            "流体": ["velocity", "pressure", "density", "Bernoulli"],
            "流速": ["cross_section", "velocity", "flow_rate", "Continuity: A1v1=A2v2"],
            "发热": ["current", "resistance", "heat_power", "Joule: P=I²R"],
            "反射": ["incident_angle", "reflection_angle", "Reflection: θi=θr"],
            "做功": ["force", "displacement", "energy", "Work: W=F·d"],
            "动能": ["mass", "velocity", "kinetic_energy", "KE: ½mv²"],
            "能量": ["mass", "velocity", "energy", "KE + PE conservation"],
        }

        hints = []
        for keyword, info in KEYWORD_MAP.items():
            if keyword in question:
                law = info[-1]
                vars_ = info[:-1]
                hints.append(f"- {law}: 变量 = {vars_}")

        if hints:
            return "\n".join(hints)
        return ""

    def _fallback_graph(self, question: str) -> Dict:
        """LLM 不可用时的简单回退"""
        return {
            "variables": ["X", "Y"],
            "edges": [["X", "Y"]],
            "confounders": [],
            "treatment": "X",
            "outcome": "Y",
            "explanation": f"从描述自动提取: {question[:50]}..."
        }

    # ═══ Step 2: 数据生成 (从 DAG 构造 SCM, 采样) ═══

    def generate_data(self, graph: Dict, n_samples: int = 500) -> Dict:
        """从因果图生成合成数据"""
        variables = graph.get("variables", [])
        edges_list = graph.get("edges", [])

        from causal.graph import CausalDAG
        from causal.scm import linear_scm

        try:
            dag = CausalDAG(variables, edges_list)
        except Exception:
            return {"data": None, "error": "Invalid DAG"}

        # 构建随机 SCM
        rng = np.random.RandomState(42)
        coeffs = {}
        for v in variables:
            parents = list(dag.parents(v))
            if parents:
                coeffs[v] = {p: rng.uniform(0.5, 2.5) for p in parents}

        scm = linear_scm(dag, coeffs, noise_std=0.3)
        samples = scm.sample(n_samples)

        # Dict → array
        data = np.column_stack([samples[v] for v in variables])

        return {
            "data": data,
            "variable_names": variables,
            "dag": dag,
            "scm": scm,
        }

    # ═══ Step 3+4: PhysCausal 管道 ═══

    def analyze(self, graph: Dict) -> Dict:
        """运行完整因果分析管道"""
        variables = graph.get("variables", [])
        edges = graph.get("edges", [])

        # 如果 LLM 判断无因果关系
        if not edges:
            return {
                "treatment": graph.get("treatment", ""),
                "outcome": graph.get("outcome", ""),
                "ate": None,
                "std_error": None,
                "ci": None,
                "method": "LLM判断: 无边 = 无因果关系",
                "adjustment_set": [],
                "identifiable": False,
            }

        data_info = self.generate_data(graph, n_samples=300)
        if data_info.get("error"):
            return {"error": data_info["error"]}

        data = data_info["data"]
        var_names = data_info["variable_names"]
        treatment = graph.get("treatment", var_names[0])
        outcome = graph.get("outcome", var_names[-1])

        from integration.pipeline import PhysCausalPipeline

        pipeline = PhysCausalPipeline()
        result = pipeline.run(
            data, var_names,
            treatment=treatment, outcome=outcome,
            verbose=False,
        )

        inference = result.get("inference", {})
        return {
            "treatment": treatment,
            "outcome": outcome,
            "ate": inference.get("ate"),
            "std_error": inference.get("std_error"),
            "ci": inference.get("ci"),
            "method": inference.get("method", "unknown"),
            "adjustment_set": inference.get("adjustment_set", []),
            "identifiable": inference.get("identifiable", False),
        }

    # ═══ Step 5: 数字 → 自然语言 ═══

    EXPLAIN_PROMPT = """你是一个善于用中文解释数据的因果推断专家。

分析结果:
  处理变量: {treatment}
  结果变量: {outcome}
  因果效应 (ATE): {ate}
  标准误: {std_error}
  95% 置信区间: [{ci_lower}, {ci_upper}]
  识别方法: {method}
  调整变量: {adjustment_set}

原始问题: {question}

请用 3-5 句流畅的中文解释这个结果:
  1. 第一句: 直接回答这个问题 (效应是多少, 方向)
  2. 第二句: 解释调整了哪些变量 (如果适用)
  3. 第三句: 效应是否显著, 置信区间什么含义
  4. 可选: 一个直观比喻或行动建议
"""

    def explain(self, question: str, analysis: Dict, graph: Dict) -> str:
        """生成自然语言解读"""
        if not self.is_available():
            return self._fallback_explain(analysis)

        prompt = self.EXPLAIN_PROMPT.format(
            treatment=analysis.get("treatment", "?"),
            outcome=analysis.get("outcome", "?"),
            ate=analysis.get("ate", "N/A"),
            std_error=analysis.get("std_error", "N/A"),
            ci_lower=analysis.get("ci", ["?", "?"])[0] if analysis.get("ci") else "?",
            ci_upper=analysis.get("ci", ["?", "?"])[1] if analysis.get("ci") else "?",
            method=analysis.get("method", "?"),
            adjustment_set=", ".join(analysis.get("adjustment_set", [])),
            question=question,
        )

        try:
            return self.client.chat([
                {"role": "user", "content": prompt}
            ])
        except Exception:
            return self._fallback_explain(analysis)

    def _fallback_explain(self, analysis: Dict) -> str:
        ate = analysis.get("ate")
        ci = analysis.get("ci")
        if ate is not None:
            lines = [
                f"因果效应: {ate:.4f}",
            ]
            if ci:
                lines.append(f"95% 置信区间: [{ci[0]:.4f}, {ci[1]:.4f}]")
            if analysis.get("method"):
                lines.append(f"方法: {analysis['method']}")
            return "\n".join(lines)
        return "无法估计因果效应。"

    # ═══ 完整管道 ═══

    def _ask_theoretical(self, question: str, history: list = None,
                          verbose: bool = True) -> Dict:
        """理论问题模式 — 不生成数据, 直接推导"""
        if verbose:
            print("  Mode: THEORETICAL (laws + math, no data needed)")

        theory_prompt = self._theory_context(question)
        messages = [{"role": "system", "content": theory_prompt}]

        # 注入历史会话 — 以真实 role 交替插入，保持对话格式
        if history and len(history) >= 2:
            recent = history[-6:]  # 最近 3 轮
            if verbose:
                n_q = sum(1 for h in recent if h.get("role") == "user")
                print(f"  History: {n_q} recent Q&A rounds injected")
            for h in recent:
                role = h.get("role", "user")
                content = h.get("content", "")
                # questions 保留完整，answers 截断到 500 字（远长于原来的 200）
                if role == "assistant":
                    content = content[:500]
                messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": question})
        response = self.client.chat(messages)
        return {
            "question": question,
            "graph": {"variables": [], "edges": [], "mode": "theoretical"},
            "analysis": {"ate": None, "method": "theoretical derivation"},
            "explanation": response,
        }

    def _ask_theoretical_fallback(self, question: str, verbose: bool) -> Dict:
        """理论问题降级模式 — 用物理定律库 + 元物理原则回答, 不调用 LLM"""
        if verbose:
            print("  Mode: THEORETICAL (no LLM — physics library only)")

        from physics.laws import library
        from meta_physics.entropy import EntropyArrow
        from meta_physics.symmetry import SymmetryDetector

        answer_parts = []

        # 关键词检测: 熵 / 时间方向 / 热力学第二定律
        entropy_kw = ["熵", "entropy", "热力学第二", "时间方向", "时间箭头", "不可逆"]
        symmetry_kw = ["对称", "守恒", "noether"]
        action_kw = ["最小作用", "least action", "变分"]
        locality_kw = ["光速", "locality", "类时", "类空"]

        # 检测涉及哪些元物理原则
        if any(kw in question for kw in entropy_kw):
            answer_parts.append(
                "【熵增与时间方向】\n"
                "根据热力学第二定律 (元物理原则③): ΔS ≥ 0。\n\n"
                "熵增原理直接定义了时间的箭头:\n"
                "  - 孤立系统的熵只增不减 → 区分了过去和未来\n"
                "  - 时间的方向就是熵增的方向\n"
                "  - 这是宏观不可逆性的根源\n\n"
                "Eddington 称熵为「时间之箭」(Arrow of Time)。\n"
                "在微观层面, 物理定律 (牛顿/F=ma, 薛定谔方程) 是时间反演对称的;\n"
                "时间方向的涌现纯粹来自统计——宏观状态数增长使熵增几乎必然。\n\n"
                "PhysCausal 中的实现:\n"
                "  meta_physics/entropy.py — EntropyArrow 类\n"
                "  用条件熵 H(Y|X) < H(X|Y) 判定因果方向 (熵增方向 = 因果方向)"
            )

        if any(kw in question for kw in symmetry_kw):
            answer_parts.append(
                "【对称性与守恒】\n"
                "根据 Noether 定理 (元物理原则②): 每种连续对称性对应一个守恒量。\n"
                "  - 时间平移对称 → 能量守恒\n"
                "  - 空间平移对称 → 动量守恒\n"
                "  - 旋转对称 → 角动量守恒\n"
            )

        if any(kw in question for kw in action_kw):
            answer_parts.append(
                "【最小作用量原理】\n"
                "根据最小作用量原理 (元物理原则①): δS = 0。\n"
                "这是物理定律的生成性原理——所有经典运动方程都可从 δS=0 导出。\n"
            )

        # 搜索相关物理定律
        q_lower = question.lower()
        relevant_laws = []
        for law in library.list_all():
            if law.name.lower() in q_lower or law.domain.lower() in q_lower:
                relevant_laws.append(law)
            # 检查输入输出变量
            for var in law.inputs + law.outputs:
                if var.lower().replace("_", "") in q_lower.replace(" ", ""):
                    if law not in relevant_laws:
                        relevant_laws.append(law)

        if relevant_laws and not answer_parts:
            answer_parts.append("【相关物理定律】\n")
            for law in relevant_laws:
                answer_parts.append(
                    f"  {law.name} ({law.domain}): {law.latex}\n"
                    f"    因果方向: {law.causal_direction}\n"
                )

        if not answer_parts:
            answer_parts.append(
                "这个问题涉及理论推导, 需要 LLM 来做数学推理。\n"
                "当前 DeepSeek API 不可用, 无法生成完整回答。\n\n"
                "PhysCausal 已加载的物理定律库:\n"
                f"  {len(library.list_all())} 条定律, 8 个领域\n"
                "设置 DEEPSEEK_API_KEY 以启用 LLM 理论推导模式。"
            )

        return {
            "question": question,
            "graph": {"variables": [], "edges": [], "mode": "theoretical_fallback"},
            "analysis": {"ate": None, "method": "physics library + meta-physics"},
            "explanation": "\n\n".join(answer_parts),
        }

    def _validate_graph(self, graph: Dict) -> Dict:
        """
        Step 1.5: 物理验证 — LLM 的因果图是否正确？

        用元物理五原则验证每一条边:
          - 因果方向 (Acceleration → Mass? 违反 F=ma)
          - 局域因果 (类空间隔?)
          - 守恒律 (反事实后守恒量是否保持?)

        Returns:
          修正后的 graph，修正的边会被标记
        """
        variables = graph.get("variables", [])
        edges = graph.get("edges", [])
        if not edges:
            return graph

        # 查物理定律库 — 是否有禁止边
        from physics.laws import library as phys_lib

        # 统一的变量名映射
        from shared import ZH_MAP
        
        vars_en = [ZH_MAP.get(v, v.lower()) for v in variables]
        forbidden_en = phys_lib.forbidden_edges(vars_en)

        # forbidden_en 是英文 → 找对应中文
        forbidden_zh = set()
        en_to_zh = {ZH_MAP.get(v, v.lower()): v for v in variables}
        for src_en, dst_en in forbidden_en:
            src_zh = en_to_zh.get(src_en, src_en)
            dst_zh = en_to_zh.get(dst_en, dst_en)
            forbidden_zh.add((src_zh, dst_zh))
        corrected = []
        corrections = []

        for src, dst in edges:
            if (src, dst) in forbidden_zh:
                # 找到禁止的反向边 → 反转它
                law_name = "unknown"
                for law in phys_lib.find_relevant(vars_en):
                    src_en = ZH_MAP.get(src, src.lower())
                    dst_en = ZH_MAP.get(dst, dst.lower())
                    if (src_en, dst_en) in law.forbidden_directions:
                        law_name = law.name
                        break
                corrected.append((dst, src))
                corrections.append(
                    f"REVERSED {src}→{dst} → {dst}→{src} ({law_name})"
                )
            else:
                corrected.append((src, dst))

        if corrections:
            graph = dict(graph)
            graph["edges"] = corrected
            graph["_corrections"] = corrections

        return graph

    def ask(self, question: str, history: list = None, verbose: bool = True) -> Dict:
        """
        完整 LLM+PhysCausal 管道。

        用户用自然语言提问 → 因果图 → 物理验证 → 分析 → 中文解释。
        """
        if verbose:
            print(f"  Query: {question}")

        # 检测理论问题 — 关键词系统 (快速, 覆盖大部分情况)
        if self._is_theoretical(question):
            if self.is_available():
                return self._ask_theoretical(question, history=history, verbose=verbose)
            else:
                return self._ask_theoretical_fallback(question, verbose)

        # 预检测: 问题涉及已知物理变量/场景 → 理论模式
        if self._mentions_physics(question):
            if self.is_available():
                return self._ask_theoretical(question, history=history, verbose=verbose)
            else:
                return self._ask_theoretical_fallback(question, verbose)

        # 语义分类: 关键词漏网时, 用 LLM 判断问题本质
        if self._is_physics_question(question):
            if self.is_available():
                return self._ask_theoretical(question, history=history, verbose=verbose)
            else:
                return self._ask_theoretical_fallback(question, verbose)

        # 对话追问检测: 短问题 + 有历史 → 可能是对上一轮理论讨论的追问
        FOLLOWUP_PATTERNS = [
            "你觉得", "你感觉", "你认为", "你怎么看", "你倾向",
            "哪个对", "哪种", "哪个更", "哪一个是",
            "是吗", "真的吗", "对吗", "这样吗",
            "为什么", "什么意思", "怎么说", "解释一下",
        ]
        if history and len(history) >= 2 and len(question) < 40:
            if any(p in question for p in FOLLOWUP_PATTERNS):
                return self._ask_theoretical(question, history=history, verbose=verbose)

        # Step 1
        if verbose: print("  Step 1: LLM extracting causal graph...")
        graph = self.extract_graph(question)

        if verbose:
            print(f"    Variables: {graph.get('variables', [])}")
            print(f"    Edges: {graph.get('edges', [])}")
            print(f"    Treatment: {graph.get('treatment')}, Outcome: {graph.get('outcome')}")

        # Step 1.5: Physics validation
        if verbose: print("  Step 1.5: Physics validation...")
        graph = self._validate_graph(graph)
        corrections = graph.get("_corrections", [])
        if corrections and verbose:
            for c in corrections:
                print(f"    ⚠ {c}")
            # 更新 treatment/outcome 如果被反转的边涉及它们
            edges = graph.get("edges", [])
            if edges and graph.get("treatment") and graph.get("outcome"):
                edge_set = set(tuple(e) for e in edges)
                t, o = graph["treatment"], graph["outcome"]
                if (o, t) in edge_set and (t, o) not in edge_set:
                    # LLM 的因果方向被物理定律反转了
                    graph["treatment"], graph["outcome"] = o, t
                    if verbose:
                        print(f"    ⚠ Treatment/Outcome swapped: {o}→{t}")

        # Step 2+3+4
        if verbose: print("  Step 2-4: PhysCausal analysis...")
        analysis = self.analyze(graph)

        # Step 5
        if verbose: print("  Step 5: LLM generating explanation...")
        explanation = self.explain(question, analysis, graph)

        return {
            "question": question,
            "graph": graph,
            "analysis": analysis,
            "explanation": explanation,
        }
