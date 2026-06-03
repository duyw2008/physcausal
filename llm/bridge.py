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

        prompt = self.CAUSAL_GRAPH_PROMPT.format(question=question)
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
                if graph.get("variables") and graph.get("edges"):
                    self._last_graph = graph
                    return graph
        except Exception:
            pass

        return self._fallback_graph(question)

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

    def ask(self, question: str, verbose: bool = True) -> Dict:
        """
        完整 LLM+PhysCausal 管道。

        用户用自然语言提问 → 因果图 → 分析 → 中文解释。
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
