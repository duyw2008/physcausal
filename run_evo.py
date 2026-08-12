#!/usr/bin/env python3
"""费曼自进化 — 长时间自主运行脚本 (v2: 带PID互斥锁)"""

import sys, os, json, time, atexit, signal
from collections import Counter

# 把 physcausal 目录加入路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# 确保 user site-packages 在路径中（sympy 等）
import site
site.addsitedir(os.path.expanduser('~/.local/lib/python3.14/site-packages'))

# ── PID 互斥锁: 防止重复启动 ──
PIDFILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "evo.pid")

def check_pidfile():
    if os.path.exists(PIDFILE):
        with open(PIDFILE) as f:
            old_pid = f.read().strip()
        try:
            os.kill(int(old_pid), 0)
            print(f"❌ 费曼脑已在运行 (PID {old_pid})")
            print(f"   如需强制重启: rm {PIDFILE}")
            sys.exit(1)
        except (OSError, ValueError):
            # 进程已死，清理残留 PID 文件
            os.remove(PIDFILE)

def write_pidfile():
    with open(PIDFILE, 'w') as f:
        f.write(str(os.getpid()))

def cleanup_pidfile():
    try:
        os.remove(PIDFILE)
    except:
        pass

check_pidfile()
write_pidfile()
atexit.register(cleanup_pidfile)

from meta_cognition.evo_colony import EvoColony
from meta_cognition.evolvable_cell import ACTIONS

LOG_PATH = os.path.join(os.path.dirname(__file__), "data", "evo_log.jsonl")
SAVE_PATH = os.path.join(os.path.dirname(__file__), "data", "evo_colony.json")
DISCOVERY_PATH = os.path.join(os.path.dirname(__file__), "data", "discoveries.jsonl")
SNAPSHOT_DIR = os.path.join(os.path.dirname(__file__), "data")

colony = EvoColony()

# ── 快照恢复: 启动时检查是否有更高代快照 ──
snap_gen, snap_data = EvoColony.find_latest_snapshot(SNAPSHOT_DIR)
if snap_data and snap_gen > colony.generation:
    n = colony.restore_from_snapshot(snap_data)
    print(f"🔄 从快照恢复 gen {snap_gen} → 当前 gen {colony.generation}, {n}个神经元")
    colony._strip_cold_edges()
else:
    print(f"📸 无可用快照 (当前 gen {colony.generation})")
start_time = time.time()

def log_event(entry: dict):
    entry["timestamp"] = time.time()
    entry["elapsed_h"] = round((time.time() - start_time) / 3600, 2)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def save_colony():
    state = {
        "generation": colony.generation,
        "cells": len(colony.cells),
        "edges": colony.graph.edge_count,
        "known_paths": len(getattr(colony, "_known_paths", set())),
        "feed_count": getattr(colony, "_feed_count", 0),
        "synapse_edges": len(colony.synapse.activations),
        "total_rewards": colony.total_rewards,
        "elapsed_h": round((time.time() - start_time) / 3600, 2),
        "pid": os.getpid(),
    }
    with open(SAVE_PATH, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def log_discovery(source: str, category: str, detail: dict):
    """记录发现，标注来源: noether_brain vs graph_cell"""
    entry = {
        "timestamp": time.time(),
        "source": source,
        "category": category,
        "generation": colony.generation,
        "edges": colony.graph.edge_count,
        **detail
    }
    with open(DISCOVERY_PATH, "a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

print(f"🧬 费曼脑启动 (☁️ 统一云架构)")
print(f"   神经元: {len(colony.cells)}, 突触: {colony.graph.edge_count}")
print(f"   日志: {LOG_PATH}")
print(f"   存档: {SAVE_PATH}")
print()
save_colony()  # 启动即写, cron 可见

# ── 优雅退出: SIGTERM 时存档再死 ──
_shutting_down = False

def _graceful_shutdown(signum, frame):
    global _shutting_down
    if _shutting_down:
        return
    _shutting_down = True
    sig_name = signal.Signals(signum).name
    print(f"\n⏸ 收到 {sig_name} @ 代{colony.generation}, 保存状态...")
    try:
        colony._save_critical_state()
        save_colony()
        snap_path = os.path.join(SNAPSHOT_DIR, f"evo_snapshot_gen{colony.generation}_exit.json")
        colony.save_snapshot(snap_path)
        print(f"  💾 退出快照: {snap_path}")
    except Exception as e:
        print(f"  ⚠ 保存失败: {e}")
    sys.exit(0)

signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)

block = 0
while True:
    try:
        colony.breathe(steps=10)
        block += 1
        
        cells = len(colony.cells)
        edges = colony.graph.edge_count
        known = len(getattr(colony, "_known_paths", set()))
        feeds = getattr(colony, "_feed_count", 0)
        ballot = len(colony.synapse.activations)
        
        # 基因组
        avg = {a: 0.0 for a in ACTIONS}
        for c in colony.cells:
            for a in ACTIONS:
                avg[a] += c.genome.get(a, 1.0 / len(ACTIONS))
        for a in avg:
            avg[a] /= max(cells, 1)
        explore = avg.get("step_forward", 0) + avg.get("step_backward", 0)
        mark = avg.get("mark", 0)
        split = avg.get("split", 0)
        
        # 投票箱 tier 分布
        by_tier = {}
        for key in colony.synapse.activations:
            t = colony.synapse.tiers.get(key, 4)
            by_tier[t] = by_tier.get(t, 0) + 1
        tier3 = by_tier.get(3, 0)
        
        # 细胞分布
        nodes = Counter(c.node for c in colony.cells)
        
        elapsed = round((time.time() - start_time) / 3600, 2)
        composed_report = getattr(colony, '_composed_alltime', 0)
        comp_str = f" 🧩:{composed_report}" if composed_report > 0 else ""
        print(f"[{elapsed:.1f}h 代{colony.generation:5d}] "
              f"神经元:{cells} 突触:{edges} 路径:{known}{comp_str} "
              f"探索:{explore:.3f} 标记:{mark:.3f} 神经发生:{split:.3f} "
              f"t3:{tier3} 喂养:{feeds}")
        
        # 每 100 代存日志
        if block % 2 == 0:
            hotspots = [f"{n}({c})" for n, c in nodes.most_common(3)]
            # 合成统计
            composed_now = getattr(colony, '_composed_total', 0)
            composed_total = getattr(colony, '_composed_alltime', 0) + composed_now
            colony._composed_alltime = composed_total
            colony._composed_total = 0
            
            log_event({
                "generation": colony.generation,
                "cells": cells,
                "edges": edges,
                "known_paths": known,
                "feed_count": feeds,
                "synapse_edges": ballot,
                "tier3_count": tier3,
                "explore_weight": round(explore, 4),
                "mark_weight": round(mark, 4),
                "split_weight": round(split, 4),
                "hotspots": hotspots,
                "focus": colony._focus.get("topic", ""),
            })
            save_colony()
        
        # 定期快照: 每 SNAPSHOT_INTERVAL 代保存完整状态 (按 block 计数, 免疫恢复代数不对齐)
        if block % max(1, colony.SNAPSHOT_INTERVAL // 10) == 0:
            snap_path = os.path.join(SNAPSHOT_DIR, f"evo_snapshot_gen{colony.generation}.json")
            if colony.save_snapshot(snap_path):
                print(f"     💾 快照: gen {colony.generation} ({cells}神经元, {edges}边)")
                EvoColony.cleanup_snapshots(SNAPSHOT_DIR)
        
        # 每 500 代(10 blocks)展示热点
        if block % 10 == 0:
            top_nodes = nodes.most_common(5)
            hot_str = " | ".join(f"{n}({c})" for n, c in top_nodes)
            print(f"        热点: {hot_str}")
            top = colony.synapse.get_strongest(3)
            if top:
                vote_str = " | ".join(
                    f'{h["src"][:12]}->{h["dst"][:12]} t{h["tier"]}' for h in top
                )
                print(f"        突触: {vote_str}")
                # 记录发现
                for h in top:
                    if h["tier"] <= 3:  # tier 3/2/1/0 才算发现, tier 4 太投机
                        log_discovery("noether_brain", "tier3_hypothesis", {
                            "src": h["src"], "dst": h["dst"],
                            "tier": h["tier"], "neurons": h["unique_neurons"],
                            "physics_passed": h.get("physics_passed"),
                        })
        
        sys.stdout.flush()
        
    except KeyboardInterrupt:
        print(f"\n⏸ 中断 @ 代{colony.generation}")
        try:
            save_colony()
        except Exception as se:
            print(f"  ⚠ 保存失败: {se}")
        break
    except Exception as e:
        print(f"❌ 错误 @ 代{colony.generation}: {e}")
        import traceback
        tb = traceback.format_exc()
        print(tb)
        # 写崩溃日志
        crash_path = os.path.join(os.path.dirname(__file__), "data", "crash.log")
        try:
            with open(crash_path, "a") as cf:
                cf.write(f"=== CRASH gen {colony.generation} {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                cf.write(tb)
                cf.write("\n")
        except Exception:
            pass
        # 🆘 紧急快照 — 死前存档
        try:
            snap_path = os.path.join(SNAPSHOT_DIR, f"evo_snapshot_gen{colony.generation}_crash.json")
            colony.save_snapshot(snap_path)
            print(f"  🆘 崩溃快照已保存: {snap_path}")
        except Exception as se:
            print(f"  ⚠ 快照保存失败: {se}")
        # 尝试保存状态（被保护）
        try:
            save_colony()
        except Exception as se:
            print(f"  ⚠ 异常状态无法保存: {se}")
        # 图状态不一致时退出，让 systemd 重启恢复
        break
