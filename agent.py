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
try:
    import readline
    _HIST_FILE = os.path.expanduser("~/.hermes/physcausal_history")
    _HIST_MAX = 2000
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

    def ask(self, question: str, verbose: bool = True) -> str:
        """LLM 自然语言提问"""
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

        return answer

    def _extract_knowledge(self, answer: str):
        """从 LLM 回答中提取因果断言, 物理验证后入库"""
        try:
            from session.knowledge_extractor import extract_from_answer
            result = extract_from_answer(answer)
            if result["added"]:
                for a in result["added"]:
                    self.values.verify(a["source"], "extracted")
        except Exception:
            pass  # 知识提取失败不阻塞主流程

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
            user_input = input(f"\n{cyan('>')} ").strip()
            if not user_input: continue
            _add_hist(user_input)
            if user_input.lower() in ("quit", "exit", "q"):
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

            print(yellow(f"Unknown command: {cmd}. Type 'help'."))

        except KeyboardInterrupt:
            print("\nGoodbye!"); break
        except EOFError:
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
