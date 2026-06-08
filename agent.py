#!/usr/bin/env python3
"""
PhysCausal Agent — 物理为骨 · 因果为肌 · 感知为眼

Usage:
    python agent.py                        # interactive mode
    python agent.py "如果球A速度减半, B会进洞吗?"  # single query
"""

from __future__ import annotations
import sys
import os
import json
import time
import warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)

# ── colour output ───────────────────────────────────────────────
class Style:
    BOLD = "\033[1m"; CYAN = "\033[36m"; GREEN = "\033[32m"
    YELLOW = "\033[33m"; RED = "\033[31m"; MAGENTA = "\033[35m"
    RESET = "\033[0m"

def bold(s): return f"{Style.BOLD}{s}{Style.RESET}"
def cyan(s):  return f"{Style.CYAN}{s}{Style.RESET}"
def green(s): return f"{Style.GREEN}{s}{Style.RESET}"
def yellow(s): return f"{Style.YELLOW}{s}{Style.RESET}"
def red(s):    return f"{Style.RED}{s}{Style.RESET}"
def magenta(s): return f"{Style.MAGENTA}{s}{Style.RESET}"

# ── readline history ────────────────────────────────────────────
_HIST_FILE = os.path.expanduser("~/.hermes/physcausal_history")
_HIST_MAX = 2000
try:
    import readline
    def _load_hist():
        try:
            os.makedirs(os.path.dirname(_HIST_FILE), exist_ok=True)
            readline.read_history_file(_HIST_FILE)
        except Exception:
            pass  # 历史文件损坏或编码问题不应该阻止启动
    def _save_hist():
        try:
            os.makedirs(os.path.dirname(_HIST_FILE), exist_ok=True)
            readline.set_history_length(_HIST_MAX)
            readline.write_history_file(_HIST_FILE)
        except Exception:
            pass  # 保存失败不阻止退出
    def _add_hist(line: str):
        if not line.strip(): return
        try:
            n = readline.get_current_history_length()
            if n > 0 and readline.get_history_item(n) == line.strip():
                return
        except Exception: pass
        readline.add_history(line.strip())
    _load_hist()
    _HAS_READLINE = True
except ImportError:
    _HAS_READLINE = False
    def _save_hist(): pass
    def _add_hist(line): pass

# readline prompt-safe: 用 \001/\002 包裹 ANSI 码，避免上下翻历史时残留字符
if _HAS_READLINE:
    _RL_START = "\001"
    _RL_END = "\002"
    def prompt_cyan(s):  return f"{_RL_START}{Style.CYAN}{_RL_END}{s}{_RL_START}{Style.RESET}{_RL_END}"
else:
    def prompt_cyan(s):  return cyan(s)

# ═══════════════════════════════════════════════════════════════
# Agent Shell
# ═══════════════════════════════════════════════════════════════

from llm.bridge import LLMBridge


class PhysCausalAgent:
    """PhysCausal Agent — 四层架构的物理因果智能体"""

    SESSION_FILE = os.path.expanduser("~/.hermes/physcausal_sessions.jsonl")
    MAX_HISTORY = 10  # 最近 N 轮对话

    def __init__(self):
        self.meta_physics_enabled = True
        self.physics_enabled = True
        self.causal_enabled = True
        self.perception_enabled = False
        self.llm = LLMBridge()  # Phase 6
        self._history = self._load_history()  # 跨会话记忆
        from meta_cognition import values
        self.values = values  # 价值系统 (显著性排序)

    def _load_history(self) -> list:
        """加载最近 MAX_HISTORY 轮对话"""
        try:
            with open(self.SESSION_FILE) as f:
                lines = f.readlines()
            history = []
            for line in lines[-self.MAX_HISTORY * 2:]:  # Q+A 各一行
                try:
                    history.append(json.loads(line.strip()))
                except (json.JSONDecodeError, KeyError):
                    pass
            return history[-self.MAX_HISTORY * 2:]
        except (FileNotFoundError, OSError):
            return []

    def _save_exchange(self, question: str, answer: str):
        """保存一轮 Q&A"""
        os.makedirs(os.path.dirname(self.SESSION_FILE), exist_ok=True)
        with open(self.SESSION_FILE, "a") as f:
            f.write(json.dumps({"role": "user", "content": question}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"role": "assistant", "content": answer[:2000]}, ensure_ascii=False) + "\n")
        self._history.append({"role": "user", "content": question})
        self._history.append({"role": "assistant", "content": answer[:2000]})
        # 保留最近 MAX_HISTORY 轮
        if len(self._history) > self.MAX_HISTORY * 2:
            self._history = self._history[-self.MAX_HISTORY * 2:]

    def status(self) -> str:
        layers = [
            ("元物理层", self.meta_physics_enabled, "对称性 + 熵增 + 测量坍缩"),
            ("物理层",   self.physics_enabled,       "11 条物理定律 + 约束传播"),
            ("因果层",   self.causal_enabled,        "DAG + SCM + do-calculus"),
            ("感知层",   self.perception_enabled,    "SimpleFeatureExtractor (stub)"),
        ]
        lines = [bold("=== PhysCausal Agent Status ===")]
        for name, enabled, desc in layers:
            mark = green("✓") if enabled else yellow("(stub)")
            lines.append(f"  {mark} {name}: {desc}")
        return "\n".join(lines)

    def analyze_physics(self, variables: str) -> str:
        """对给定变量运行物理对称性分析"""
        var_list = [v.strip() for v in variables.split(",")]
        from meta_physics.symmetry import SymmetryDetector
        detector = SymmetryDetector()
        symmetries = detector.detect(var_list)

        if not symmetries:
            return yellow(f"No symmetries detected for: {var_list}")

        lines = [bold(f"=== Symmetry Analysis: {', '.join(var_list)} ===")]
        for sym in symmetries:
            lines.append(f"\n  {cyan(sym.symmetry_type.name)}: {sym.notes}")
            if sym.conserved_law:
                lines.append(f"    → {sym.conserved_law.name}")
                lines.append(f"      {sym.conserved_law.conserved_quantity} = const")
            lines.append(f"    confidence: {sym.confidence:.0%}")
        return "\n".join(lines)

    def entropy_direction(self, data_file: str, var_a: str, var_b: str) -> str:
        """用熵增原理判定因果方向"""
        import numpy as np
        from meta_physics.entropy import EntropyArrow

        data = np.loadtxt(data_file, delimiter=",", skiprows=1)
        # Assume first row is header
        try:
            with open(data_file) as f:
                header = f.readline().strip().split(",")
        except Exception:
            header = [f"V{i}" for i in range(data.shape[1])]

        arrow = EntropyArrow()
        result = arrow.infer_causal_direction(data, header, var_a, var_b)

        lines = [bold(f"=== Entropy Arrow: {var_a} vs {var_b} ===")]
        lines.append(f"  Direction: {cyan(result.direction)}")
        lines.append(f"  ΔEntropy: {result.delta_entropy:.4f}")
        lines.append(f"  Reversible: {result.is_reversible}")
        lines.append(f"  {result.notes}")
        return "\n".join(lines)

    def counterfactual_worlds(self, observed: str, interventions: str, outcome: str) -> str:
        """多世界反事实分析"""
        from meta_physics.measurement import MultiWorldCounterfactual

        # Parse "x=1,y=2" format
        def parse_dict(s):
            d = {}
            for pair in s.split(","):
                k, v = pair.split("=")
                d[k.strip()] = float(v.strip())
            return d

        obs_dict = parse_dict(observed)
        intv_list = [parse_dict(i) for i in interventions.split(";")]

        mwc = MultiWorldCounterfactual()
        mwc.create_actual_world(obs_dict)

        # Set counterfactual values (simplified — in full version uses SCM)
        for i, intv in enumerate(intv_list):
            bid = mwc.create_counterfactual_world(intv, label=f"cf_{i+1}")
            # Simple linear extrapolation for demo
            cf_vals = dict(obs_dict)
            cf_vals.update(intv)
            # Crude counterfactual: each unit change in cause → β change in outcome
            for cause_var, cause_val in intv.items():
                delta = cause_val - obs_dict.get(cause_var, cause_val)
                if outcome in cf_vals and cause_var != outcome:
                    cf_vals[outcome] = cf_vals[outcome] + delta * 0.5
            mwc.branches[bid].set_variables(cf_vals)

        return mwc.all_branches_report(outcome)

    def pipeline(self, data_file: str, treatment: str, outcome: str) -> str:
        """运行完整四层流水线"""
        import numpy as np
        from integration.pipeline import PhysCausalPipeline

        try:
            data = np.loadtxt(data_file, delimiter=",", skiprows=1)
        except Exception:
            data = np.loadtxt(data_file, delimiter=",")

        try:
            with open(data_file) as f:
                header = f.readline().strip().split(",")
        except Exception:
            header = [f"V{i}" for i in range(data.shape[1])]

        pl = PhysCausalPipeline()
        return pl.quick_analyze(data, header, treatment, outcome)

    def learn(self, env_name: str, episodes: int = 5, samples: int = 30) -> str:
        """主动学习 — 通过干预实验发现因果结构"""
        from env.physics_sim import make_env, ENV_REGISTRY
        from active_experiment.active_learner import ActiveLearner

        if env_name == "all":
            learner = ActiveLearner(None)
            results = learner.run_all_envs(
                n_episodes=episodes, verbose=False
            )
            return learner._summary(results) or "Learning complete. Check module library."

        if env_name not in ENV_REGISTRY:
            available = ", ".join(ENV_REGISTRY.keys())
            return yellow(f"Unknown env: {env_name}. Available: {available}")

        env = make_env(env_name)
        learner = ActiveLearner(env)
        result = learner.run(
            n_episodes=episodes,
            samples_per_experiment=samples,
            verbose=False,
        )

        lines = [bold(f"=== Active Learning: {env_name} ===")]
        lines.append(f"Episodes: {result['episodes']}")
        lines.append(f"Samples: {result['total_samples']}")
        lines.append(f"Discovered: {result['correct']}/{len(result['true_edges'])} edges "
                     f"({result['accuracy']:.0%})")
        if result['false_positives']:
            lines.append(yellow(f"False positives: {result['false_positives']}"))
        if result['missed']:
            lines.append(yellow(f"Missed: {result['missed']}"))
        lines.append(f"Experiments: {', '.join(f'do({e})' for e in result['experiments'])}")
        if result['module_added']:
            lines.append(green(f"📦 Module added to library"))
        lines.append(f"Converged: {result['converged']}")
        return "\n".join(lines)

    META_KEYWORDS = [
        "刚才问了", "刚才问过", "上次的问题", "之前问了", "历史问题",
        "我问过什么", "我问了什么", "你记得", "还记得", "回忆一下",
        "之前问了什么", "刚才问了什么", "之前的对话", "上次对话",
    ]

    def ask(self, question: str, verbose: bool = True) -> str:
        """LLM 自然语言提问"""
        # 元问题检测: 关于对话历史本身的问题 → 直接回答，不走因果管道
        if any(kw in question for kw in self.META_KEYWORDS):
            return self._answer_about_history(question, verbose)

        result = self.llm.ask(question, history=self._history, verbose=verbose)

        graph = result.get("graph", {})
        mode = graph.get("mode", "")
        analysis = result.get("analysis", {})
        explanation = result.get("explanation", "")

        # 理论模式 (含 fallback): 直接展示解释
        if mode in ("theoretical", "theoretical_fallback"):
            answer = explanation if explanation else yellow("No explanation available.")
        else:
            lines = []
            if verbose:
                lines.append(bold("=== PhysCausal Analysis ==="))
            lines.append(f"{bold('Variables:')} {', '.join(graph.get('variables', []))}")
            edges = graph.get('edges', [])
            if edges:
                lines.append(f"{bold('Causal graph:')} {', '.join(f'{s}→{d}' for s,d in edges)}")

            if analysis.get("ate") is not None:
                lines.append(f"\n{bold('Effect:')}")
                lines.append(f"  ATE = {analysis['ate']:.4f} ± {analysis['std_error']:.4f}")
                if analysis.get("ci"):
                    lines.append(f"  95% CI: [{analysis['ci'][0]:.4f}, {analysis['ci'][1]:.4f}]")
                lines.append(f"  Method: {analysis.get('method', '?')}")
                if analysis.get("adjustment_set"):
                    lines.append(f"  Adjusted for: {', '.join(analysis['adjustment_set'])}")
            elif analysis.get("identifiable") is False:
                lines.append(f"\n{yellow('Effect not identifiable from data')}")

            if explanation:
                lines.append(f"\n{bold('Explanation:')}")
                lines.append(explanation)
            answer = "\n".join(lines)

        # 保存到会话记忆
        self._save_exchange(question, answer)

        # 更新价值系统: 标记用户兴趣
        self._track_interest(question, answer)

        # 提取会话知识: 从回答中提取因果断言入库
        self._extract_knowledge(answer)

        # 标注知识来源: 定律库贡献 vs LLM 贡献
        if mode in ("theoretical", "theoretical_fallback"):
            answer = self._format_for_terminal(answer)
            answer = self._annotate_sources(answer)
            # 哲学透镜: 从哲学层面解释
            answer = self._add_philosophical_lens(question, answer)
            # 矛盾驱动自主探索: 如果回答暴露了定律间的矛盾，触发更深层思考
            answer = self._react_to_contradictions(question, answer)
            # 自主学习: 检测知识缺口, 自动补全定律
            self._auto_learn(question, answer)

        return answer

    def _auto_learn(self, question: str, answer: str):
        """自主学习: 检测知识缺口, 问 LLM 获取候选定律, 验证入库"""
        try:
            from session.auto_learn import auto_learn, learn_external_mentions
            # 先尝试从答案中检测的外部知识直接学习
            result = learn_external_mentions(self, answer)
            if result["success"]:
                print(f"\n  {green('📚 Learned from answer:')} {', '.join(result['learned'])}")
            # 再尝试从知识缺口学习
            result2 = auto_learn(self, question, answer)
            if result2["success"]:
                if not result["success"]:
                    print(f"\n  {green('📚 Auto-learned:')} {', '.join(result2['learned'])}")
        except Exception:
            pass

    def _add_philosophical_lens(self, question: str, answer: str) -> str:
        """从哲学透镜层为回答添加解释框架"""
        try:
            from meta_cognition.lenses import match_for_context, explain_discovery

            # 从问题和回答中提取变量和领域关键词
            combined = question + " " + answer[:500]
            variables = []
            domains = []

            # 变量检测
            var_keywords = {
                "mass": "mass", "energy": "energy", "wavelength": "wavelength",
                "geodesic": "geodesic_path", "curvature": "curvature",
                "wave_function": "wave_function", "collapse": "collapse",
                "entropy": "entropy", "time": "time",
                "interference": "interference_pattern",
                "momentum": "momentum", "force": "force",
            }
            for kw, var in var_keywords.items():
                if kw in combined.lower():
                    variables.append(var)

            # 领域检测
            domain_keywords = {
                "quantum": "quantum", "thermodynamics": "thermodynamics",
                "relativity": "general_relativity", "mechanics": "mechanics",
                "unification": "unification", "geometry": "geometry",
            }
            for kw, dom in domain_keywords.items():
                if kw in combined.lower():
                    domains.append(dom)

            if not variables and not domains:
                return answer

            lens_text = explain_discovery([], variables, domains)
            if lens_text:
                # 插入到来源标注之后
                if "── 知识溯源" in answer:
                    parts = answer.split("── 知识溯源", 1)
                    return parts[0] + lens_text + "\n\n── 知识溯源" + parts[1]
                else:
                    return answer + lens_text
        except Exception:
            pass
        return answer

    def _react_to_contradictions(self, question: str, answer: str) -> str:
        """如果回答暴露了定律间的矛盾，触发自主探索"""
        from physics.laws import library

        # 收集回答中引用的、有 collapse_timescale 的定律
        mentioned = {}
        for law in library.list_all():
            if law.name in answer:
                ts = getattr(law, 'collapse_timescale', None)
                if ts:
                    mentioned[law.name] = ts

        # 需要至少 2 种不同的时间尺度 → 存在矛盾
        unique_ts = set(mentioned.values())
        if len(unique_ts) < 2:
            return answer

        # 用 LLM 生成对这个矛盾的研究问题
        if not self.llm.is_available():
            return answer

        try:
            prompt = (
                "以下 PhysCausal 定律库中的定律对同一现象给出了不同的描述，形成了理论张力：\n\n"
            )
            for name, ts in mentioned.items():
                prompt += f"  {name}: 坍缩时间尺度 = {ts}\n"
            prompt += (
                "\n请生成 1-2 个值得深入研究的问题，帮助理解为什么这些框架会得出不同结论，"
                "以及如何可能调和它们。只返回问题，用中文，每行一个。"
            )

            response = self.llm.client.chat([{"role": "user", "content": prompt}])
            questions = [
                q.strip().lstrip("0123456789. -•·")
                for q in response.split("\n")
                if q.strip() and ("?" in q or "？" in q or len(q) > 15)
            ]

            if questions:
                extra = "\n\n💡 检测到理论张力，自主探索:\n"
                for q in questions[:2]:
                    extra += f"  → {q}\n"
                answer += extra

                # 尝试用 chain 对矛盾涉及的变量做链式推导
                try:
                    from inference.counterfactual_chain import propagate, format_chain
                    from collections import Counter
                    # 收集这些定律的所有变量，找出现次数最多的
                    var_counter = Counter()
                    for law in library.list_all():
                        if law.name in mentioned:
                            for v in law.inputs + law.outputs:
                                var_counter[v] += 1
                    # 选出现最频繁的变量
                    if var_counter:
                        var = var_counter.most_common(1)[0][0]
                        chain = propagate(var, "reconcile")
                        if chain.get("steps"):
                            chain_text = format_chain(chain)
                            answer += f"\n  🔗 链式探索 ({var}):\n{chain_text[:300]}"
                except Exception:
                    pass
        except Exception:
            pass

        return answer

    def _answer_about_history(self, question: str, verbose: bool = True) -> str:
        """回答关于对话历史本身的元问题"""
        if not self._history:
            return "目前还没有任何对话历史。"

        lines = [bold("=== Conversation History ===")]
        lines.append(f"共 {len(self._history)//2} 轮对话 (最近):\n")

        for h in self._history[-10:]:  # 最近 5 轮
            role_label = "Q" if h["role"] == "user" else "A"
            content = h["content"]
            if h["role"] == "assistant":
                content = content[:200] + ("..." if len(h["content"]) > 200 else "")
            lines.append(f"  {cyan(role_label)}: {content}")

        lines.append(f"\n文件: {self.SESSION_FILE}")
        return "\n".join(lines)

    def _format_for_terminal(self, text: str) -> str:
        """将 LLM 输出的 Markdown 格式转换为终端 ANSI"""
        import re
        # **text** → ANSI bold
        text = re.sub(r'\*\*(.+?)\*\*', lambda m: bold(m.group(1)), text)
        # `code` → ANSI dim
        text = re.sub(r'`([^`]+)`', lambda m: f"\033[2m{m.group(1)}\033[0m", text)
        # --- → ───
        text = re.sub(r'^---+$', '─' * 50, text, flags=re.MULTILINE)
        # Remove LaTeX \(...\) wrappers (already Unicode)
        text = text.replace(r'\(', '').replace(r'\)', '')
        text = text.replace(r'\[', '').replace(r'\]', '')
        return text

    def _annotate_sources(self, answer: str) -> str:
        """标注答案中 PhysCausal 定律库贡献的部分"""
        from physics.laws import library

        # 统计被引用的 PhysCausal 定律
        cited_physcausal = []
        for law in library.list_all():
            if law.name in answer:
                cited_physcausal.append(law.name)

        # 检测 LLM 从外部引入的定律/概念 (不在 PhysCausal 库中)
        import re
        external_mentions = set()
        # 匹配 "XXX定律" 或 "XXX 定律" — 要求至少 2 个字符的前缀
        for m in re.finditer(r'([A-Za-z\u4e00-\u9fff]{2,}(?:定律|定理|原理|方程|法则|效应))', answer):
            name = m.group(1)
            # 检查是否在 PhysCausal 库中
            in_library = any(law.name in name or name in law.name for law in library.list_all())
            if not in_library and len(name) > 2:
                external_mentions.add(name)

        n_physcausal = len(cited_physcausal)
        n_external = len(external_mentions)
        total_concepts = n_physcausal + n_external

        # 贡献比例: PhysCausal 定律数 / 总引用概念数
        if total_concepts > 0:
            ratio = n_physcausal / total_concepts
        else:
            ratio = 0.3  # 默认: 至少提供了推理框架

        ratio = min(ratio, 0.95)

        footer = [f"\n{'─' * 50}"]
        footer.append(f"📚 PhysCausal 定律库贡献: {ratio:.0%}")
        if cited_physcausal:
            footer.append(f"   引用: {', '.join(cited_physcausal[:6])}")
            if len(cited_physcausal) > 6:
                footer.append(f"          ... 等 {len(cited_physcausal)} 条")
        if external_mentions:
            footer.append(f"🤖 LLM 外部知识 ({n_external}): {', '.join(sorted(external_mentions)[:4])}")

        return answer + "\n".join(footer)

    def _extract_knowledge(self, answer: str):
        """从 LLM 回答中提取因果断言, 物理验证后入库 (LLM 驱动)"""
        try:
            from session.knowledge_extractor import extract_from_answer
            client = self.llm.client if self.llm.is_available() else None
            result = extract_from_answer(answer, client=client)
            if result["added"]:
                for a in result["added"]:
                    self.values.verify(a["source"], "extracted")
        except Exception:
            pass

    def _track_interest(self, question: str, answer: str):
        """从问答中提取涉及的定律/概念, 增加显著性"""
        from physics.laws import library

        # 方法一: 从 LLM 回答中提取 (理论模式有效)
        for law in library.list_all():
            if law.name.lower() in answer.lower():
                self.values.user_interest(law.name, "law")

        # 方法二: 从问题文本中检测物理概念 (落入因果管道时的 fallback)
        CONCEPT_MAP = {
            "newton": "Newton II", "牛顿": "Newton II", "F=ma": "Newton II",
            "力和加速": "Newton II", "力与加速": "Newton II",
            "熵": "Entropy Increase", "entropy": "Entropy Increase",
            "热力学第二": "Entropy Increase",
            "ohm": "Ohm", "欧姆": "Ohm", "电压": "Ohm", "电流": "Ohm",
            "pendulum": "Pendulum Period", "单摆": "Pendulum Period", "摆": "Pendulum Period",
            "弹簧": "Simple Harmonic", "spring": "Simple Harmonic", "简谐": "Simple Harmonic",
            "fourier": "Fourier", "热传导": "Fourier",
            "schwarzschild": "Schwarzschild", "黑洞": "Schwarzschild", "史瓦西": "Schwarzschild",
            "时间膨胀": "TimeDilation", "time dilation": "TimeDilation",
        }
        q_lower = question.lower()
        for keyword, law_name in CONCEPT_MAP.items():
            if keyword in q_lower:
                self.values.user_interest(law_name, "law")

    def creative_transfer(self, source: str, target_vars: str,
                          target_types: str, data_file: str) -> str:
        """跨域骨架迁移"""
        import numpy as np
        from creative.evolution import CreativeEvolution

        target_list = [v.strip() for v in target_vars.split(",")]
        type_dict = {}
        for pair in target_types.split(","):
            k, v = pair.strip().split(":")
            type_dict[k.strip()] = v.strip()

        try:
            data = np.loadtxt(data_file, delimiter=",", skiprows=1)
        except Exception:
            data = np.loadtxt(data_file, delimiter=",")

        evo = CreativeEvolution()
        result = evo.cross_domain_discover(source, target_list, type_dict, data)

        if result["success"]:
            lines = [bold("=== Cross-Domain Discovery ===")]
            lines.append(f"Source module: {cyan(source)}")
            lines.append(f"Discovered edges: {green(str(result['discovered_edges']))}")
            lines.append(f"Skeleton: {result.get('skeleton', 'N/A')}")
            lines.append(f"Score: {result['score']:.1f}")
            return "\n".join(lines)
        return yellow(f"Transfer failed: {result.get('reason', 'unknown')}")

    def creative_evolve(self, data_file: str, variables: str, generations: int = 30) -> str:
        """进化搜索因果结构"""
        import numpy as np
        from creative.evolution import CreativeEvolution

        var_list = [v.strip() for v in variables.split(",")]
        try:
            data = np.loadtxt(data_file, delimiter=",", skiprows=1)
        except Exception:
            data = np.loadtxt(data_file, delimiter=",")

        evo = CreativeEvolution()
        result = evo.evolve(data, var_list, n_generations=generations,
                            population_size=15, verbose=False)
        return evo.report(result)


# ═══════════════════════════════════════════════════════════════
# CLI — Command Registry
# ═══════════════════════════════════════════════════════════════

CMD_HELP = {
    "≡ Causal": {
        "ask <question>":       "LLM causal analysis (+ physics validation)",
        "learn <env|all> [e] [s]": "active discovery (7 envs)",
        "pipeline <csv> <T> <Y>": "full 4-layer pipeline",
    },
    "≡ Creative": {
        "creative transfer <src> <vars> <types> <csv>": "cross-domain skeleton",
        "creative evolve <csv> <vars> [gen]": "evolution search",
        "modules":               "module library (auto-grows)",
        "skeletons":             "skeleton library",
        "compose":               "auto-compose modules",
        "associate [module]":    "discover structural associations",
        "explain <module1> <module2>": "explain why two modules are isomorphic",
    },
    "≡ Meta-Physics": {
        "symmetry <v1,v2,...>":  "detect symmetries + conservation",
        "entropy <csv> <A> <B>": "entropy arrow direction",
        "dissonance":          "detect cognitive dissonance (research questions)",
        "autonomous [n]":     "let agent think independently (n thoughts)",
        "chain <var> <change>": "counterfactual propagation (e.g. chain mass 减半)",
        "research":           "完整研究循环 v2 (惊喜+优先级+鲁棒性+留一法+归档)",
        "suggest":            "元认知 — 扫描状态, 告诉物理学家下一步该做什么",
        "meta":              "meta-learning summary (cross-env strategies)",
        "status":                "layer status",
    },
}

def _parse_options(rest, n_min, n_max=99):
    """Parse optional numeric arguments."""
    parts = rest.split()
    args = {}
    for p in parts:
        if '=' in p:
            k, v = p.split('=', 1)
            try: args[k] = int(v)
            except: args[k] = v
    return args

def run_interactive():
    agent = PhysCausalAgent()
    print(bold("=" * 60))
    print(bold("  PhysCausal Agent — 物理为骨 · 因果为肌 · 感知为眼"))
    print(bold("  v0.2.1  |  Type 'help' for commands, 'quit' to exit"))
    print(bold("=" * 60))

    while True:
        try:
            user_input = input(f"\n{prompt_cyan('>')} ").strip()
            if not user_input: continue
            _add_hist(user_input)
            if user_input.lower() in ("quit", "exit", "q"):
                _save_hist()
                print("Goodbye!"); break

            parts = user_input.split()
            cmd, rest = parts[0], " ".join(parts[1:])

            # ── Help ──
            if cmd in ("help", "h"):
                for section, cmds in CMD_HELP.items():
                    print(f"\n{bold(section)}")
                    for c, desc in cmds.items():
                        print(f"  {c:<45s} {desc}")
                continue

            # ── Status ──
            if cmd == "status":
                print(agent.status()); continue

            # ── Ask ──
            if cmd == "ask":
                if not rest: print(red("Usage: ask <question>")); continue
                print(agent.ask(rest)); continue

            # ── Learn ──
            if cmd == "learn":
                p = rest.split()
                if not p: print(red("Usage: learn <env|all> [episodes] [samples]")); continue
                env, eps, sam = p[0], 3, 20
                if len(p) > 1: eps = int(p[1])
                if len(p) > 2: sam = int(p[2])
                print(agent.learn(env, eps, sam)); continue

            # ── Pipeline ──
            if cmd == "pipeline":
                p = rest.split()
                if len(p) < 3: print(red("Usage: pipeline <csv> <T> <Y>")); continue
                print(agent.pipeline(p[0], p[1], p[2])); continue

            # ── Creative ──
            if cmd == "creative":
                sub = rest.split()
                if not sub: print(red("Usage: creative transfer|evolve ...")); continue
                if sub[0] == "transfer":
                    if len(sub) < 5: print(red("Usage: creative transfer <src> <vars> <types> <csv>")); continue
                    print(agent.creative_transfer(sub[1], sub[2], sub[3], sub[4])); continue
                if sub[0] == "evolve":
                    if len(sub) < 3: print(red("Usage: creative evolve <csv> <vars> [gen]")); continue
                    gen = int(sub[3]) if len(sub) > 3 else 30
                    print(agent.creative_evolve(sub[1], sub[2], gen)); continue

            if cmd == "modules":
                from creative.module_library import ModuleLibrary
                lib = ModuleLibrary()
                for m in lib.list_all():
                    print(f"  {m.name} ({m.domain}): {m.edges}"); continue

            if cmd == "skeletons":
                from creative.skeleton_library import SkeletonLibrary
                for s in SkeletonLibrary().list_skeletons():
                    print(f"  {s['name']}: {len(s['variables'])} vars, {len(s['edges'])} edges"); continue

            if cmd == "compose":
                from composition.composer import CompositionDiscovery
                r = CompositionDiscovery().auto_compose(verbose=False)
                print(green(f"Discovered {r['n_discovered']}, added {r['n_added']}")); continue

            if cmd == "associate":
                from creative.structure_discovery import discovery
                if rest:
                    assocs = discovery.associate(rest)
                    if assocs:
                        print(bold(f"Modules isomorphic to '{rest}':"))
                        for a in assocs:
                            print(f"  {a['name']} ({a['domain']}): {a['edges']}")
                            print(f"    {a['shared_pattern']}")
                    else:
                        print(yellow(f"No isomorphic modules found for '{rest}'"))
                else:
                    print(discovery.summary())
                continue

            if cmd == "explain":
                parts = rest.split()
                if len(parts) < 2:
                    print(red("Usage: explain <module1> <module2>"))
                    continue
                from creative.structure_discovery import _topology_signature
                from creative.module_library import ModuleLibrary
                lib = ModuleLibrary()
                m1, m2 = lib.get(parts[0]), lib.get(parts[1])
                if not m1: print(red(f"Module '{parts[0]}' not found")); continue
                if not m2: print(red(f"Module '{parts[1]}' not found")); continue
                sig1, sig2 = _topology_signature(m1.edges), _topology_signature(m2.edges)
                if sig1 == sig2:
                    n_in = len(set(s for s,_ in m1.edges) - set(d for _,d in m1.edges))
                    print(bold(f"'{m1.name}' ↔ '{m2.name}' are isomorphic"))
                    print(f"  Same skeleton: {n_in} input(s) → output")
                    print(f"  {m1.name} ({m1.domain}): {m1.edges}")
                    print(f"  {m2.name} ({m2.domain}): {m2.edges}")
                    print(f"  Structural signature: {sig1}")
                    print(f"\n  {green('Role mapping:')}")
                    m1_inputs = [s for s,_ in m1.edges if s not in set(d for _,d in m1.edges)]
                    m2_inputs = [s for s,_ in m2.edges if s not in set(d for _,d in m2.edges)]
                    for a, b in zip(m1_inputs, m2_inputs):
                        print(f"    {m1.domain}::{a} ↔ {m2.domain}::{b}")
                else:
                    print(yellow(f"'{m1.name}' and '{m2.name}' are NOT isomorphic"))
                    print(f"  sig1={sig1}")
                    print(f"  sig2={sig2}")
                continue

            # ── Meta-Physics ──
            if cmd == "symmetry":
                if not rest: print(red("Usage: symmetry v1,v2,...")); continue
                print(agent.analyze_physics(rest)); continue

            if cmd == "entropy":
                p = rest.split()
                if len(p) < 3: print(red("Usage: entropy <csv> <A> <B>")); continue
                print(agent.entropy_direction(p[0], p[1], p[2])); continue

            if cmd == "history":
                if rest == "clear":
                    if _HAS_READLINE:
                        readline.clear_history()
                        _save_hist()
                        print(green("Command history cleared."))
                    else:
                        print(yellow("Readline not available."))
                elif rest == "sessions":
                    if os.path.exists(PhysCausalAgent.SESSION_FILE):
                        size = os.path.getsize(PhysCausalAgent.SESSION_FILE)
                        with open(PhysCausalAgent.SESSION_FILE) as f:
                            lines = f.readlines()
                        print(f"Session Q&A: {len(lines)//2} exchanges ({size} bytes)")
                        print(f"  File: {PhysCausalAgent.SESSION_FILE}")
                    else:
                        print("No session history yet.")
                elif rest == "clear-sessions":
                    if os.path.exists(PhysCausalAgent.SESSION_FILE):
                        os.remove(PhysCausalAgent.SESSION_FILE)
                        print(green("Session Q&A history cleared."))
                    else:
                        print("No session history to clear.")
                else:
                    if _HAS_READLINE:
                        n = readline.get_current_history_length()
                        print(f"Command history: {n} entries (max {_HIST_MAX})")
                        print(f"  File: {_HIST_FILE}")
                        print(f"  history clear      — clear command history")
                        print(f"  history sessions   — show session Q&A")
                        print(f"  history clear-sessions — clear session Q&A")
                    else:
                        print("Readline not available.")
                continue

            if cmd == "meta":
                from reinforcement.meta_learner import meta
                print(meta.summary()); continue

            if cmd == "chain":
                p = rest.split()
                if len(p) < 2:
                    print(red("Usage: chain <variable> <change>  (e.g. chain mass 减半)"))
                    continue
                from inference.counterfactual_chain import propagate, format_chain
                chain = propagate(p[0], " ".join(p[1:]))
                print(format_chain(chain)); continue

            if cmd == "dissonance":
                from meta_cognition.dissonance import cognitive_summary
                print(cognitive_summary()); continue

            if cmd == "plan":
                p = rest.split()
                if len(p) < 2:
                    print(red("plan <start> <target>  |  plan bridge <domain1> <domain2>"))
                    continue
                from inference.causal_planner import plan, format_plan, find_bridge_paths
                if p[0] == "bridge" and len(p) >= 3:
                    paths = find_bridge_paths(p[1], p[2])
                    print(f"=== 领域桥接: {p[1]} ↔ {p[2]} ===")
                    for i, b in enumerate(paths[:5]):
                        print(f"  {i+1}. {b['start_var']}→{b['target_var']} (代价={b['score']:.1f} 长度={b['length']})")
                else:
                    paths = plan(p[0], " ".join(p[1:]), max_depth=6)
                    print(format_plan(paths, p[0], " ".join(p[1:])))
                continue

            if cmd == "innovate":
                from creative.innovation_engine import innovation_report
                print(innovation_report()); continue

            if cmd == "research":
                from creative.research_cycle import research_report_v2
                print(research_report_v2()); continue

            if cmd == "focus":
                if not rest:
                    from meta_cognition.research_directions import (
                        RESEARCH_DIRECTIONS, get_current_focus, set_focus
                    )
                    current = get_current_focus()
                    if current:
                        print(f"▶ 当前聚焦: [{current['tag']}] {current['name']}")
                        print(f"  {current['core_question']}")
                        print()

                    # 编号列表
                    for i, d in enumerate(RESEARCH_DIRECTIONS):
                        focused = " ▶" if current and current["id"] == d["id"] else "  "
                        stars = "★" * d["difficulty"] + "·" * (5 - d["difficulty"])
                        print(f"  {i+1:2d}. [{d['tag']}] {d['name']}")
                        print(f"       难度{stars}  |  {d['core_question'][:70]}")

                    print()
                    print(f"  [1-{len(RESEARCH_DIRECTIONS)}] 选择方向 | [0] 取消聚焦 | [q] 退出")

                    try:
                        choice = input("  > ").strip().lower()
                    except (EOFError, KeyboardInterrupt):
                        continue

                    if choice == "q":
                        continue
                    if choice == "0":
                        import os
                        from data_paths import focus_path; f = focus_path()
                        if os.path.exists(f):
                            os.remove(f)
                        print("聚焦已取消。物理学家恢复自由探索。")
                        continue

                    try:
                        idx = int(choice) - 1
                        if 0 <= idx < len(RESEARCH_DIRECTIONS):
                            d = RESEARCH_DIRECTIONS[idx]
                            r = set_focus(d["id"])
                            if r["success"]:
                                print(f"\n▶ 聚焦方向: [{d['tag']}] {d['name']}")
                                print(f"  核心问题: {d['core_question']}")
                                print(f"  关键变量: {', '.join(d['key_variables'][:4])}")
                                print(f"  开放问题:")
                                for op in d["open_problems"][:3]:
                                    print(f"    · {op}")
                                print(f"\n  后续 suggest/innovate/speculate 将偏向此方向。")
                            else:
                                print(f"设置失败: {r.get('reason', '?')}")
                        else:
                            print(f"无效编号: 1-{len(RESEARCH_DIRECTIONS)}")
                    except ValueError:
                        print(f"无效输入")

                elif rest == "none":
                    from meta_cognition.research_directions import set_focus
                    set_focus("")
                    import os
                    from data_paths import focus_path; f = focus_path()
                    if os.path.exists(f):
                        os.remove(f)
                    print("聚焦已取消。物理学家恢复自由探索。")
                else:
                    from meta_cognition.research_directions import set_focus
                    r = set_focus(rest)
                    if r["success"]:
                        d = r["direction"]
                        print(f"▶ 聚焦方向: {d['tag']} {d['name']}")
                        print(f"  核心问题: {d['core_question']}")
                        print(f"  关键变量: {', '.join(d['key_variables'][:6])}")
                    else:
                        print(f"未知方向: {rest}。用 focus 查看可选方向。")
                continue

            if cmd == "speculate":
                from creative.speculate import speculate_report, speculate_save
                if rest == "--save":
                    print(speculate_save())
                else:
                    print(speculate_report())
                continue

            if cmd == "paper":
                from creative.paper_writer import write_paper
                print(write_paper())
                continue

            if cmd == "suggest":
                if rest == "--run-all":
                    from meta_cognition.suggest_executor import execute_all_cross_validations
                    print(execute_all_cross_validations())
                elif rest == "--run":
                    from meta_cognition.suggest_executor import execute_top_suggestion
                    print(execute_top_suggestion())
                else:
                    from meta_cognition.suggest_executor import interactive_suggest
                    interactive_suggest()
                continue

            if cmd == "watch":
                if rest == "stop":
                    if hasattr(agent, '_watch_thread') and agent._watch_thread:
                        agent._watch_running = False
                        print(green("Watch stopped."))
                    else:
                        print(yellow("No watch running."))
                    continue
                import threading
                def _watch_loop():
                    while getattr(agent, '_watch_running', True):
                        time.sleep(1800)  # 30 分钟
                        if not getattr(agent, '_watch_running', True):
                            break
                        try:
                            from meta_cognition.autonomous import AutonomousAgent
                            a = AutonomousAgent()
                            a.internal.energy = 1.0
                            a.internal.coherence_drive = 0.9
                            discoveries = []
                            for i in range(15):
                                r = a.think(verbose=False, llm_bridge=None)
                                if r:
                                    l = r.get('learned', [])
                                    rt = r.get('type', '')
                                    s = r.get('significance', 0)
                                    if l and s > 0 and rt in ('dissonance', 'frontier'):
                                        discoveries.append({'rtype': rt, 'l': l, 'sig': s})
                            print(f"\n{green('[PhysCausal]')} {len(discoveries)} 发现, 好奇心={a.internal.curiosity_level:.2f}")
                            for d in discoveries:
                                stars = '★★★' if d['sig']>=2 else '★★' if d['sig']>=1 else '★'
                                print(f"  {stars} [{d['rtype']}] {d['l']}")
                        except Exception as e:
                            print(f"[PhysCausal] watch error: {e}")
                agent._watch_thread = threading.Thread(target=_watch_loop, daemon=True)
                agent._watch_running = True
                agent._watch_thread.start()
                mins = 30
                print(green(f"Watch started — 每 {mins} 分钟自动运行 (watch stop 停止)"))
                continue

            if cmd == "autonomous":
                from meta_cognition.autonomous import AutonomousAgent
                n = int(rest) if rest.isdigit() else 15
                agent_auto = AutonomousAgent()
                agent_auto.internal.energy = 1.0
                agent_auto.internal.coherence_drive = 0.9
                discoveries = []
                validations = []
                for i in range(n):
                    result = agent_auto.think(verbose=False, llm_bridge=None)
                    if result:
                        learned = result.get('learned', [])
                        rtype = result.get('type', '')
                        sig = result.get('significance', 0)
                        if learned and sig > 0 and rtype in ('dissonance', 'frontier'):
                            tag = result.get('frontier_type', 'tension')
                            if rtype == 'dissonance':
                                tag = result.get('issue_law_a','?') + ' <-> ' + result.get('issue_law_b','?')
                            discoveries.append({'tag': tag, 'rtype': rtype, 'learned': learned, 'sig': sig, 'reason': result.get('sig_reason','')})
                        vs = result.get('tiered_validation', 0)
                        if vs > 0:
                            validations.append({'score': vs, 'convs': result.get('tiered_convergences',[])})

                s = agent_auto.internal
                print(f"\n=== PhysCausal ({n} 轮思考, 0 token) ===")
                print(f"好奇心={s.curiosity_level:.2f}  精力={s.energy:.2f}  累计发现={s.total_discoveries}")

                type_cn = {'dissonance': '认知失调', 'frontier': '前沿探索', 'sparse_zone': '稀疏区',
                           'scale_gap': '尺度裂缝', 'dead_end': '断头路', 'tension': '张力'}
                rtype_cn = {'dissonance': '失调', 'frontier': '前沿'}

                if discoveries:
                    print(f"\n{green('新发现')} ({len(discoveries)}):")
                    for d in discoveries:
                        stars = '★★★' if d['sig']>=2 else '★★' if d['sig']>=1 else '★'
                        tag_cn = type_cn.get(d.get('tag', d['tag']), d['tag'])
                        print(f"  {stars} [{rtype_cn.get(d['rtype'], d['rtype'])}] {tag_cn}")
                        print(f"     → {d['learned']}")
                        if d.get('reason'): print(f"     {d['reason']}")
                else:
                    print(f"{yellow('本轮无新发现')}")

                if validations:
                    print(f"\n{green('弱验证')}:")
                    for v in validations:
                        print(f"  一致度={v['score']:.0%}  汇聚点={v['convs']}")

                print(f"\n{agent_auto.trend_report()}")
                # ── 语义聚类 + 粗粒化 ──
                from meta_cognition.semantic_cluster import find_semantic_clusters
                from emergence.coarse_grainer import report as coarse_report
                from emergence.hierarchical_abstraction import abstraction_report
                clusters = find_semantic_clusters(min_combined=0.5)
                if clusters:
                    print(f"\n{green('语义聚类')}:")
                    for c in clusters[:3]:
                        print(f"  {c['variables'][0]} ↔ {c['variables'][1]} (名称={c['name_sim']:.0%})")
                cg = coarse_report()
                if '候选宏观变量: 0' not in cg:
                    print(f"\n{green('粗粒化')}:")
                    for line in cg.split('\n')[1:6]:
                        if line.strip(): print(f"  {line.strip()}")

                # ── 创新引擎 ──
                from creative.innovation_engine import innovate
                innovations = innovate(n_candidates=10, min_score=0.8)
                if innovations:
                    print(f"\n{green('创新提案')}: {len(innovations)} 条候选边")
                    for inv in innovations[:3]:
                        print(f"  {inv['src']} → {inv['dst']} ({inv['verdict']})")
                continue

            print(yellow(f"Unknown command: {cmd}. Type 'help'."))

        except KeyboardInterrupt:
            _save_hist()
            print("\nGoodbye!"); break
        except EOFError:
            _save_hist()
            print("\nGoodbye!"); break

if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(f"PhysCausal Agent v0.1.0\n")
        agent = PhysCausalAgent()
        query = " ".join(sys.argv[1:])
        print(f"{cyan('>')} {query}")
        # Simple routing
        cmd = query.split()[0].lower()
        rest = " ".join(query.split()[1:])
        if cmd == "symmetry":
            print(agent.analyze_physics(rest))
        else:
            print(agent.status())
    else:
        run_interactive()
