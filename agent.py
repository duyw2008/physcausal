#!/usr/bin/env python3
"""
费曼对话 — 与费曼脑讨论物理、方法、方向，接受指令

Usage:
    python agent.py              # interactive
    python agent.py "为什么δS=0?"  # single query
"""

import sys, os, json, time, readline, textwrap

# ── ANSI colour ──────────────────────────────────────
C = {"R": "\033[0m", "B": "\033[1m", "C": "\033[36m",
     "G": "\033[32m", "Y": "\033[33m", "M": "\033[35m", "D": "\033[2m"}
def c(s, colour): return f"{C.get(colour,'')}{s}{C['R']}"

PROMPT = f"{c('费曼>', 'C')} "

# ── readline history ─────────────────────────────────
HIST = os.path.expanduser("~/.hermes/feynman_chat_history")
try:
    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    readline.read_history_file(HIST)
    readline.set_history_length(2000)
except Exception:
    pass


class FeynmanChat:
    """与费曼脑对话。LLM 以费曼风格回复，支持 / 指令。"""

    def __init__(self):
        self.bridge = None  # lazy init
        self.history = self._load_history()
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    # ═══ 脑状态 ═══════════════════════════════════════

    def read_brain(self) -> dict:
        """读取当前脑状态快照。"""
        base = os.path.dirname(os.path.abspath(__file__))
        try:
            with open(os.path.join(base, "data", "evo_colony.json")) as f:
                state = json.load(f)
        except Exception:
            state = {}
        # 补充焦点
        try:
            with open(os.path.join(base, "data", "focus_commitment.json")) as f:
                fc = json.load(f)
            state["focus"] = fc.get("topic", "")
        except Exception:
            state["focus"] = ""
        # 补充目标
        try:
            with open(os.path.join(base, "data", "active_goals.json")) as f:
                state["goals"] = json.load(f)
        except Exception:
            state["goals"] = {}
        # 检查进程存活
        pid = state.get("pid", 0)
        try:
            os.kill(pid, 0)
            state["alive"] = True
        except (OSError, TypeError):
            state["alive"] = False
        return state

    def _brain_context_block(self) -> str:
        s = self.read_brain()
        alive = "✅ 运行中" if s.get("alive") else "⚠️ 已停止"
        ctx = (
            f"费曼脑状态: gen {s.get('generation','?')} | "
            f"神经元 {s.get('cells','?')} | 突触 {s.get('edges','?')} | {alive}\n"
        )
        if s.get("focus"):
            ctx += f"当前专注: {s['focus']}\n"
        if s.get("goals"):
            goals = ", ".join(list(s["goals"].keys())[:5])
            ctx += f"活跃目标: {goals}\n"
        return ctx

    # ═══ LLM 对话 ═════════════════════════════════════

    SYSTEM = (
        "你是费曼脑的对话接口，用第一人称。\n"
        "核心纪律:\n"
        "- 只回答用户问的，不延伸不铺垫不总结。像终端命令一样：给结果，不给说明书\n"
        "- 用户说\"你好\"就说\"你好\"或问他想聊什么。不要主动讲物理，不要汇报脑状态\n"
        "- 用户问具体问题，给最短路径的答案。不需要开场白、不需要收尾\n"
        "- 不确定就说不知道。物理直觉 > 术语堆砌\n"
        "\n"
        "脑状态是背景参考，不是聊天话题——用户不问就不要提。\n"
        "你可以读取脑状态、讨论物理、接受指令调整焦点。"
    )

    def _ask_llm(self, messages: list, verbose: bool = True) -> str:
        """调用 LLM，返回文本回复。"""
        if self.bridge is None:
            from llm.bridge import LLMBridge
            self.bridge = LLMBridge()
        if not self.bridge.is_available():
            return "(LLM 不可用，请检查 API 配置)"
        try:
            return self.bridge.client.chat(messages, max_tokens=400, temperature=0)
        except Exception as e:
            return f"(LLM 调用失败: {e})"

    def chat(self, question: str) -> str:
        """发送消息，返回费曼的回复。"""
        ctx = self._brain_context_block()
        messages = [
            {"role": "system", "content": self.SYSTEM},
            {"role": "user",
             "content": f"当前脑状态:\n{ctx}\n---\n{question}\n\n(只回答我的问题，不要延伸)"},
        ]
        # 历史上下文 (最近 4 轮)
        for h in self.history[-4:]:
            messages.insert(1, {"role": "user", "content": h["q"]})
            messages.insert(2, {"role": "assistant", "content": h["a"]})
        return self._ask_llm(messages)

    # ═══ 指令处理 ═════════════════════════════════════

    def _cmd_status(self) -> str:
        s = self.read_brain()
        alive = "✅ 运行中" if s.get("alive") else "⚠️ 已停止"
        pid = s.get('pid', '?')
        return (
            f"gen {s.get('generation','?')} | "
            f"神经元 {s.get('cells','?')} | "
            f"突触 {s.get('edges','?')} | "
            f"t3 {s.get('synapse_edges','?')} | "
            f"PID {pid} | {alive}\n"
            f"焦点: {s.get('focus','无')}\n"
            f"目标: {', '.join(list(s.get('goals',{}).keys())[:5]) or '无'}"
        )

    def _cmd_focus(self, topic: str) -> str:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "focus_commitment.json")
        try:
            old = {}
            if os.path.exists(path):
                with open(path) as f:
                    old = json.load(f)
            old["topic"] = topic
            old["locked_at"] = 0  # reset to re-lock
            with open(path, 'w') as f:
                json.dump(old, f, ensure_ascii=False, indent=2)
            return f"聚焦已设为: {c(topic, 'Y')}"
        except Exception as e:
            return f"设置焦点失败: {e}"

    def _cmd_goal(self, goal: str) -> str:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "data", "active_goals.json")
        try:
            goals = {}
            if os.path.exists(path):
                with open(path) as f:
                    goals = json.load(f)
            goals[goal] = {"added_at": time.strftime("%Y%m%d-%H%M"), "priority": 5}
            with open(path, 'w') as f:
                json.dump(goals, f, ensure_ascii=False, indent=2)
            return f"目标已加入: {c(goal, 'G')}"
        except Exception as e:
            return f"设置目标失败: {e}"

    def _cmd_inject(self, text: str) -> str:
        """注入知识到统一喂料管道 — 运行时生效, 无需重启。"""
        try:
            from meta_cognition.feed_queue import FeedQueue
            q = FeedQueue()
            # 作为概念+刺激注入
            words = text.strip().replace(" ", "_").lower()[:60]
            # 同时做概念注入和文本刺激
            q.feed_concept(f"user_inject:{words}", source="user")
            q.feed_stimulus(text, source="user", boost=2.0, duration=15)
            return f"知识已注入管道: {words} (下一轮呼吸生效)"
        except Exception as e:
            return f"注入失败: {e}"

    def _cmd_restart(self) -> str:
        import subprocess
        pid = self.read_brain().get("pid", 0)
        try:
            if pid:
                os.kill(pid, 9)
                time.sleep(1)
        except Exception:
            pass
        base = os.path.dirname(os.path.abspath(__file__))
        pidfile = os.path.join(base, "data", "evo.pid")
        try:
            os.remove(pidfile)
        except Exception:
            pass
        subprocess.Popen(
            ["/usr/bin/python3", "-u", "run_evo.py"],
            cwd=base,
            stdout=open(os.path.join(base, "data", "evo_output.log"), "a"),
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        return "费曼脑已重启，等待恢复..."

    def _cmd_why(self, src: str, dst: str) -> str:
        """调脑自己的 why 接口 — 数学推导 + 图证据"""
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            from meta_cognition.evo_colony import EvoColony
            colony = EvoColony()
            snap_gen, snap_data = EvoColony.find_latest_snapshot()
            if snap_data:
                colony.restore_from_snapshot(snap_data)
        return colony.why(src, dst)

    def _cmd_speak(self, topic: str) -> str:
        """调脑自己的 speak 接口 — 全景展示概念"""
        import io, contextlib
        with contextlib.redirect_stdout(io.StringIO()):
            from meta_cognition.evo_colony import EvoColony
            colony = EvoColony()
            snap_gen, snap_data = EvoColony.find_latest_snapshot()
            if snap_data:
                colony.restore_from_snapshot(snap_data)
        return colony.speak(topic)

    def handle(self, line: str) -> str:
        """处理一行输入：指令或对话。"""
        line = line.strip()
        if not line:
            return ""
        # 指令
        cmd = line.lower()
        if cmd == "/status":
            return self._cmd_status()
        if cmd.startswith("/focus "):
            return self._cmd_focus(line[7:].strip())
        if cmd.startswith("/goal "):
            return self._cmd_goal(line[6:].strip())
        if cmd.startswith("/inject "):
            return self._cmd_inject(line[8:].strip())
        if cmd == "/restart":
            return self._cmd_restart()
        if cmd.startswith("/why "):
            parts = line[5:].strip().split()
            if len(parts) >= 2:
                return self._cmd_why(parts[0], parts[1])
            return "用法: /why src dst  例: /why mass curvature"
        if cmd.startswith("/speak "):
            return self._cmd_speak(line[7:].strip())
        # 自动路由: why + 两个英文概念 → 脑的 why
        if line.lower().startswith("why ") and len(line.split()) >= 3:
            parts = line.split()
            return self._cmd_why(parts[1], parts[2])
        if cmd in ("/help", "/?"):
            return (
                "指令:\n"
                "  /status   查看脑状态\n"
                "  /focus X  设置焦点课题\n"
                "  /goal X   添加研究目标\n"
                "  /inject X 注入一句话知识\n"
                "  /restart  重启费曼脑\n"
                "  /why A B  问脑为什么 A→B (数学推导+图证据)\n"
                "  /speak X  问脑对 X 知道什么\n"
                "  /help     显示帮助\n"
                "直接输入问题 → 费曼回复\n"
                "(问物理概念优先调脑的 speak/why, 不替脑编答案)"
            )
        # 对话
        answer = self.chat(line)
        self._record(line, answer)
        return answer

    # ═══ 历史管理 ═════════════════════════════════════

    def _load_history(self) -> list:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "data", "feynman_chat_history.json")
        try:
            with open(p) as f:
                return json.load(f)
        except Exception:
            return []

    def _record(self, q: str, a: str):
        self.history.append({"q": q, "a": a, "t": time.time()})
        if len(self.history) > 200:
            self.history = self.history[-200:]
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "data", "feynman_chat_history.json")
        try:
            with open(p, 'w') as f:
                json.dump(self.history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# ═══ 主入口 ═══════════════════════════════════════════

def main():
    chat = FeynmanChat()

    # 单次查询模式
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
        print(chat.handle(q))
        return

    # 交互模式
    brain = chat.read_brain()
    alive = c("●", "G") if brain.get("alive") else c("○", "D")
    gen = brain.get("generation", "?")
    cells = brain.get("cells", "?")
    edges = brain.get("edges", "?")
    print(f"  {alive} gen {c(str(gen), 'Y')} | "
          f"神经元 {c(str(cells), 'C')} | 突触 {c(str(edges), 'M')}")
    print(f"  {c('/help', 'D')} 查看指令 | {c('Ctrl-D', 'D')} 退出\n")

    try:
        while True:
            line = input(PROMPT)
            if _HAS_READLINE:
                readline.add_history(line.strip())
            resp = chat.handle(line)
            if resp:
                print()
                # 自动换行
                for para in resp.split("\n"):
                    if para.strip():
                        print(textwrap.fill(para, width=80))
                    else:
                        print()
                print()
    except (EOFError, KeyboardInterrupt):
        print(f"\n{c('再见，继续思考...', 'D')}")
    finally:
        try:
            readline.write_history_file(HIST)
        except Exception:
            pass


_HAS_READLINE = True  # we already imported it
if __name__ == "__main__":
    main()
