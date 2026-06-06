#!/usr/bin/env python3
"""
RL + Self-Organization 协同 Demo
=================================
三部曲闭环: RL训练 → StrategyTransfer → FreeEnergyAgent 探索/利用
"""

import sys, os, warnings, time, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
warnings.filterwarnings("ignore", category=RuntimeWarning)

from env.physics_sim import make_env
from reinforcement.causal_rl import CausalQLearner, StrategyTransfer
from self_organization.free_energy import FreeEnergyAgent
from active_experiment.active_learner import ActiveLearner

BOLD = "\033[1m"; GREEN = "\033[32m"; CYAN = "\033[36m"; RESET = "\033[0m"


def run():
    np.random.seed(42)
    
    print(f"{BOLD}{'='*55}{RESET}")
    print(f"{BOLD}  RL + Self-Organization Collaborative Demo{RESET}")
    print(f"{BOLD}{'='*55}{RESET}")
    
    # ═══ Phase 1: Train RL on pendulum ═══
    print(f"\n{CYAN}Phase 1: RL on Pendulum (40 ep){RESET}")
    t0 = time.time()
    ql_p = CausalQLearner(make_env("pendulum"), epsilon=0.8)
    r_p = ql_p.train(n_episodes=40)
    print(f"  Accuracy: {r_p['final_accuracy']:.0%}  time: {time.time()-t0:.1f}s")
    
    # ═══ Phase 2: Transfer to spring ═══
    print(f"\n{CYAN}Phase 2: StrategyTransfer Pendulum → Spring{RESET}")
    
    # Cold start
    ql_cold = CausalQLearner(make_env("spring"), epsilon=0.8)
    r_cold = ql_cold.train(n_episodes=15)
    acc_cold = r_cold["final_accuracy"]
    print(f"  Spring cold:      {acc_cold:.0%}")
    
    # Warm start via StrategyTransfer
    transfer = StrategyTransfer()
    ql_warm = transfer.transfer(ql_p, make_env("spring"))
    r_warm = ql_warm.train(n_episodes=15)
    acc_warm = r_warm["final_accuracy"]
    print(f"  Spring warm:      {acc_warm:.0%} (transfer)")
    print(f"  {GREEN}Gain: {acc_cold:.0%} → {acc_warm:.0%}{RESET}")
    
    # ═══ Phase 3: FreeEnergyAgent auto-tuning ═══
    print(f"\n{CYAN}Phase 3: FreeEnergyAgent auto-tuning{RESET}")
    
    agent = FreeEnergyAgent(beta=1.0)
    env = make_env("spring")
    learner = ActiveLearner(env)
    
    for step in range(8):
        mode = agent.status()["mode"]
        episodes = 1 if mode == "exploit" else 2
        
        result = learner.run(n_episodes=episodes, samples_per_experiment=20, verbose=False)
        acc = result["accuracy"]
        agent.update_beta([acc])
        s = agent.status()
        fe = agent.free_energy_history[-1] if agent.free_energy_history else 0
        print(f"  Step {step+1}: {s['mode']:7s} β={s['beta']:.3f} F={fe:6.1f} acc={acc:.0%}")
    
    # ═══ Summary ═══
    print(f"\n{BOLD}{'='*55}{RESET}")
    print(f"  {GREEN}Trilogy: symmetry → breaking → self-organization{RESET}")
    print(f"  Transfer gain: {acc_cold:.0%} → {acc_warm:.0%} (+{acc_warm-acc_cold:.0%})")
    print(f"  Self-org final: β={agent.beta:.3f} mode={agent.status()['mode']}")


if __name__ == "__main__":
    run()
