#!/usr/bin/env python3
"""
noether_chat.py — 与诺特脑对话
用法: python3 noether_chat.py
"""
import sys, os, json, subprocess, readline

sys.path.insert(0, os.path.dirname(__file__))

from physics.enrich_knowledge import feed_enrichment
feed_enrichment()

# 初始化
print("🧬 诺特脑 v0.5.0 — 对话接口")
print("输入 /help 查看命令, /q 退出")
print()

DATA = os.path.join(os.path.dirname(__file__), "data")

def run_query(cmd):
    r = subprocess.run([sys.executable, "brain_query.py", cmd] + cmd.split()[1:],
                       capture_output=True, text=True, cwd=os.path.dirname(__file__))
    lines = [l for l in r.stdout.split("\n") if not l.startswith("🧪")]
    return "\n".join(lines)

def run_ask(question):
    r = subprocess.run([sys.executable, "brain_ask.py", question],
                       capture_output=True, text=True, cwd=os.path.dirname(__file__))
    lines = [l for l in r.stdout.split("\n") if not l.startswith("🧪")]
    return "\n".join(lines)

def run_derive(src, dst):
    r = subprocess.run([sys.executable, "brain_derive.py", src, dst],
                       capture_output=True, text=True, cwd=os.path.dirname(__file__))
    return r.stdout[-2000:] if len(r.stdout) > 2000 else r.stdout

HELP = """
/help          — 显示帮助
/state         — 脑当前状态
/goals         — 活跃目标
/setgoal <概念> <原因> — 设定目标
/ask <问题>    — 问脑
/derive <A> <B> — 推导A→B
/discoveries   — 自主发现
/bridges       — 跨域桥梁
/q             — 退出"""

while True:
    try:
        cmd = input("🧠> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nbye")
        break
    
    if not cmd:
        continue
    
    parts = cmd.split()
    head = parts[0].lower()
    
    if head == "/q":
        print("bye")
        break
    elif head == "/help":
        print(HELP)
    elif head == "/state":
        print(run_query("state"))
    elif head == "/goals":
        print(run_query("goals"))
    elif head == "/setgoal" and len(parts) >= 3:
        concept = parts[1]
        reason = " ".join(parts[2:])
        print(run_query(f"set_goal {concept} {reason}"))
    elif head == "/derive" and len(parts) >= 3:
        print(f">>> 推导 {parts[1]} → {parts[2]} ...")
        print(run_derive(parts[1], parts[2]))
    elif head == "/discoveries":
        print(run_query("discoveries"))
    elif head == "/bridges":
        print(run_query("bridges"))
    elif head == "/ask" and len(parts) >= 2:
        question = " ".join(parts[1:])
        print(f">>> 问脑: {question}")
        print(run_ask(question))
    else:
        # 自由对话: 脑上下文 + LLM 自然语言
        question = cmd
        print(f">>> 问脑: {question}")
        brain_context = run_ask(question)
        # 调用 LLM 自然解释
        from llm.bridge import LLMBridge
        llm = LLMBridge()
        prompt = (
            "你是诺特脑，一个基于进化殖民地+物理知识图谱的自主发现系统。\n"
            "用户向你提问。下面是你的内部认知（coincidence统计、抽象桥、自主发现边）。\n"
            "请基于这些信息用中文自然回答，像物理学家讨论一样。如果认知中没有答案，诚实说。\n"
            f"\n用户: {question}\n\n诺特脑认知:\n{brain_context[:3000]}\n\n诺特脑回答:"
        )
        result = llm._ask_theoretical(prompt, verbose=False)
        answer = result.get("explanation", "") or result.get("answer", "")
        if answer:
            # 提取文字
            if isinstance(answer, str):
                clean = answer[:1500]
            elif isinstance(answer, dict):
                clean = answer.get("explanation", "")[:1500]
            else:
                clean = str(answer)[:1500]
            print(f"\n诺特脑: {clean}")
            print(f"\n── 以下是原始认知 ──")
            print(brain_context[:1000])
        else:
            print(brain_context)
