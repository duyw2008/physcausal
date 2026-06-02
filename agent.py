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
        except FileNotFoundError: pass
    def _save_hist():
        try:
            readline.set_history_length(_HIST_MAX)
            readline.write_history_file(_HIST_FILE)
        except Exception: pass
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

class PhysCausalAgent:
    """PhysCausal Agent — 四层架构的物理因果智能体"""

    def __init__(self):
        self.meta_physics_enabled = True
        self.physics_enabled = True
        self.causal_enabled = True
        self.perception_enabled = False  # Phase 6

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


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def run_interactive():
    agent = PhysCausalAgent()

    print(bold("=" * 60))
    print(bold("  PhysCausal Agent — 物理为骨 · 因果为肌 · 感知为眼"))
    print(bold("  v0.1.0  |  Type 'help' for commands, 'quit' to exit"))
    print(bold("=" * 60))

    while True:
        try:
            user_input = input(f"\n{cyan('>')} ").strip()
            if not user_input:
                continue
            _add_hist(user_input)
            if user_input.lower() in ("quit", "exit", "q"):
                _save_hist()
                print("Goodbye!")
                break

            cmd = user_input.split()[0].lower()
            rest = user_input[len(cmd):].strip()

            if cmd in ("help", "h"):
                print(f"""{bold('Commands:')}
  pipeline <file.csv> <T> <Y> — run full pipeline (perception→causal)
  status                        — show layer status
  symmetry <var1,var2,...>      — detect symmetries
  entropy <file.csv> <A> <B>    — infer causal direction via entropy
  worlds <obs> <intv> <outcome> — multi-world counterfactual
  quit                          — exit
""")

            elif cmd == "status":
                print(agent.status())

            elif cmd == "symmetry":
                if not rest:
                    print(red("Usage: symmetry var1,var2,..."))
                else:
                    print(agent.analyze_physics(rest))

            elif cmd == "entropy":
                parts = rest.split()
                if len(parts) < 3:
                    print(red("Usage: entropy <file.csv> <var_a> <var_b>"))
                else:
                    print(agent.entropy_direction(parts[0], parts[1], parts[2]))

            elif cmd == "worlds":
                parts = rest.split()
                if len(parts) < 3:
                    print(red("Usage: worlds x=1,y=2 intv1;intv2 outcome_var"))
                else:
                    print(agent.counterfactual_worlds(parts[0], parts[1], parts[2]))

            elif cmd == "pipeline":
                parts = rest.split()
                if len(parts) < 3:
                    print(red("Usage: pipeline <file.csv> <treatment> <outcome>"))
                else:
                    print(agent.pipeline(parts[0], parts[1], parts[2]))

            else:
                print(yellow(f"Unknown command: {cmd}. Type 'help'."))

        except KeyboardInterrupt:
            _save_hist()
            print("\nGoodbye!")
            break
        except Exception as e:
            print(red(f"Error: {e}"))


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
