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

    CAUSAL_GRAPH_PROMPT = """你是一个因果推断专家。从以下自然语言描述中提取因果图。

描述: {question}

请以严格的 JSON 格式返回，只返回 JSON:
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
        from physics.laws import library

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

        # 中英文变量名映射
        ZH_MAP = {
            "力": "force", "质量": "mass", "加速度": "acceleration",
            "速度": "velocity", "位移": "displacement", "时间": "time",
            "能量": "energy", "动量": "momentum", "功": "work",
            "电压": "voltage", "电流": "current", "电阻": "resistance",
            "功率": "power", "温度": "temperature", "压力": "pressure",
            "体积": "volume", "密度": "density", "长度": "length",
            "频率": "frequency", "周期": "period",
            "分子运动": "kinetic_energy", "动能": "kinetic_energy",
            "分子动能": "kinetic_energy", "分子运动加剧": "kinetic_energy",
            "波长": "wavelength", "频率": "frequency", "声速": "wave_speed",
            "入射角": "incident_angle", "折射角": "refraction_angle",
            "反射角": "reflection_angle", "焦距": "focal_length",
            "物距": "object_distance", "像距": "image_distance",
            "截面积": "cross_section", "流速": "flow_rate",
            "磁通量": "magnetic_flux_change", "感应电流": "induced_current",
            "热量": "heat_power", "声源速度": "source_velocity",
            "观测频率": "observed_frequency",
        }

        # 变量 → 英文 (用于匹配物理定律库)
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

    def ask(self, question: str, verbose: bool = True) -> Dict:
        """
        完整 LLM+PhysCausal 管道。

        用户用自然语言提问 → 因果图 → 物理验证 → 分析 → 中文解释。
        """
        if verbose:
            print(f"  Query: {question}")

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
