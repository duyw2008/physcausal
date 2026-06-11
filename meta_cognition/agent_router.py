"""
Noether 对话接口 — ask 成为唯一入口

所有命令通过自然语言触发:
  "质量减半会怎样" → chain
  "有什么新类比"   → analogy
  "切换到量子引力"  → focus QG
  "帮我验证一下"   → suggest
  "生成论文"       → paper
  "跑研究循环"     → research
  "大胆假设"       → speculate
  "看看状态"       → viz
  "回忆一下"       → memory
  "后台运行"       → watch
"""
from __future__ import annotations
from typing import Optional, Callable
from meta_cognition.nl_router import execute_nl_query, parse_nl_query

# ── 命令路由表 ──

AGENT_COMMANDS = {
    "chain": {
        "keywords": ["会怎样", "传播", "推理", "导致", "影响", "变化", "减半", "加倍", "增加", "减少", "升高", "降低"],
        "parser": lambda text: _parse_chain(text),
    },
    "analogy": {
        "keywords": ["类比", "相似", "同构", "共鸣", "模式"],
        "parser": lambda _: ("analogy",),
    },
    "focus": {
        "keywords": ["方向", "聚焦", "研究", "切换", "换到", "转向"],
        "parser": lambda text: _parse_focus(text),
    },
    "suggest": {
        "keywords": ["建议", "验证", "检查", "下一步", "该做什么"],
        "parser": lambda _: ("suggest",),
    },
    "research": {
        "keywords": ["研究循环", "跑研究", "完整验证", "全流程"],
        "parser": lambda _: ("research",),
    },
    "speculate": {
        "keywords": ["假设", "假说", "大胆", "猜测", "如果"],
        "parser": lambda _: ("speculate",),
    },
    "paper": {
        "keywords": ["论文", "报告", "写", "生成"],
        "parser": lambda _: ("paper",),
    },
    "viz": {
        "keywords": ["状态", "面板", "可视化", "仪表盘"],
        "parser": lambda _: ("viz",),
    },
    "memory": {
        "keywords": ["记忆", "回忆", "过去", "历史", "之前"],
        "parser": lambda _: ("memory",),
    },
    "autonomous": {
        "keywords": ["自主", "自己跑", "自动", "探索"],
        "parser": lambda text: _parse_autonomous(text),
    },
    "watch": {
        "keywords": ["后台", "定时", "挂着", "watch", "开始工作", "工作吧", "自己跑"],
        "parser": lambda _: ("watch",),
    },
    "plan": {
        "keywords": ["规划", "路径", "怎么到", "桥接"],
        "parser": lambda text: _parse_plan(text),
    },
    "strategy": {
        "keywords": ["策略", "最优", "决策", "应该", "哪个方向"],
        "parser": lambda _: ("strategy",),
    },
}


def _parse_chain(text: str):
    """解析因果链查询: '如果质量减半会怎样' → ('chain', 'mass', '减半')"""
    import re
    for cn, en in {"质量": "mass", "速度": "velocity", "温度": "temperature", "能量": "energy",
                   "动量": "momentum", "熵": "entropy", "力": "force", "时间": "time",
                   "波长": "wavelength", "频率": "frequency", "压力": "pressure",
                   "电压": "voltage", "电流": "current"}.items():
        text = text.replace(cn, en)
    
    changes = {"减半": "减半", "加倍": "加倍", "增加": "增加", "减少": "减少",
               "升高": "升高", "降低": "降低", "增强": "增强", "减弱": "减弱"}
    
    text_lower = text.lower()
    for en_var in ["mass", "velocity", "temperature", "energy", "momentum", "entropy",
                   "force", "time", "wavelength", "frequency", "pressure", "current"]:
        if en_var in text_lower:
            for ch_cn, ch_val in changes.items():
                if ch_cn in text:
                    return ("chain", en_var, ch_val)
            return ("chain", en_var, "变化")
    return None


def _parse_focus(text: str):
    """解析方向切换: '切换到量子引力' → ('focus', 'QG')"""
    dirs = {"量子引力": "QG", "量子基础": "QM", "涌现": "EM", "信息": "IB",
            "几何统一": "GU", "因果发现": "CD", "因果统一": "CU",
            "跨域": "CB", "知识手册": "KS"}
    for cn, tag in dirs.items():
        if cn in text:
            return ("focus", tag)
    return ("focus", "")  # 只显示菜单


def _parse_plan(text: str):
    """解析规划: '从质量怎么到波长' → ('plan', 'mass', 'wavelength')"""
    for cn, en in {"质量": "mass", "速度": "velocity", "温度": "temperature",
                   "能量": "energy", "波长": "wavelength", "熵": "entropy",
                   "频率": "frequency", "干涉": "interference", "力": "force"}.items():
        text = text.replace(cn, en)
    
    import re
    # "从 X 到 Y" 模式
    m = re.search(r"从\s*(\w+)\s*(?:怎么|如何)?\s*(?:到|→|达)\s*(\w+)", text)
    if m:
        return ("plan", m.group(1), m.group(2))
    # "X 怎么桥接到 Y"
    m = re.search(r"(\w+)\s*(?:怎么|如何)?\s*(?:桥接|连接)?\s*(?:到)?\s*(\w+)", text)
    if m:
        return ("plan", m.group(1), m.group(2))
    return None


def _parse_autonomous(text: str):
    """解析自主运行: '自己跑10轮' → ('autonomous', '10')"""
    import re
    m = re.search(r"(\d+)\s*轮", text)
    n = m.group(1) if m else "15"
    return ("autonomous", n)


def parse_agent_command(text: str) -> Optional[Tuple]:
    """从自然语言解析智能体命令"""
    text_lower = text.lower()
    
    for cmd_name, config in AGENT_COMMANDS.items():
        if any(kw in text_lower for kw in config["keywords"]):
            result = config["parser"](text)
            if result:
                return result
    
    # 回退到知识网络查询
    kg_result = parse_nl_query(text)
    if kg_result:
        return ("kg", kg_result)
    
    return None


def execute_agent_command(text: str) -> Optional[str]:
    """执行自然语言智能体命令"""
    result = parse_agent_command(text)
    if not result:
        return None
    
    cmd = result[0]
    args = result[1:]
    
    # ── KG 查询 (委托给 nl_router) ──
    if cmd == "kg":
        return execute_nl_query(text)
    
    # ── 核心命令 ──
    if cmd == "chain":
        from inference.counterfactual_chain import propagate, format_chain
        chain = propagate(args[0], args[1], max_depth=6)
        return format_chain(chain)
    
    if cmd == "plan":
        from inference.causal_planner import plan, format_plan
        paths = plan(args[0], args[1], max_depth=6)
        return format_plan(paths, args[0], args[1])
    
    if cmd == "analogy":
        from creative.causal_analogy import analogy_report
        return analogy_report()
    
    if cmd == "focus":
        if args and args[0]:
            from meta_cognition.research_directions import set_focus, get_current_focus
            r = set_focus(args[0])
            if r["success"]:
                d = r["direction"]
                from meta_cognition.talk import talk_report
                return f"聚焦: [{d['tag']}] {d['name']}\n核心: {d['core_question']}\n关键变量: {', '.join(d['key_variables'][:5])}" + "\n" + talk_report()
            return f"未知方向: {args[0]}"
        from meta_cognition.research_directions import focus_report
        return focus_report()
    
    if cmd == "suggest":
        from meta_cognition.suggest_executor import execute_top_suggestion
        return execute_top_suggestion()
    
    if cmd == "research":
        from creative.research_cycle import research_report_v2
        return research_report_v2()
    
    if cmd == "speculate":
        from creative.speculate import speculate_report
        return speculate_report()
    
    if cmd == "paper":
        from creative.paper_writer import write_paper
        return write_paper()
    
    if cmd == "viz":
        from meta_cognition.viz import viz_report
        return viz_report()
    
    if cmd == "memory":
        from meta_cognition.memory import memory_report
        return memory_report()
    
    if cmd == "autonomous":
        n = int(args[0]) if args else 15
        from meta_cognition.autonomous import AutonomousAgent
        a = AutonomousAgent()
        a.internal.energy = 1.0
        discoveries = []
        for i in range(n):
            r = a.think(verbose=False, llm_bridge=None)
            if r and r.get("interesting"):
                discoveries.append(r)
        return f"自主运行 {n} 轮: {len(discoveries)} 个有趣的想法"
    
    if cmd == "watch":
        from meta_cognition.identity import NAME
        return f"💬 {NAME}: 好的，我开始后台工作了。每30分钟自主研究一轮。\n   如需停止: 在 agent 终端输入 watch stop" 
    
    if cmd == "strategy":
        from reinforcement.meta_rl import strategy_report
        return strategy_report()
    
    return None
