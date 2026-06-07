"""
Meta-Learning 演示 — 跨域策略迁移

在 spring / pendulum / circuit 上训练元学习器,
然后在 doppler (不同骨架) 上测试迁移效率。
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from env.physics_sim import make_env
from reinforcement.causal_rl import CausalQLearner
from reinforcement.meta_learner import MetaLearner, meta


def demo():
    print("=" * 60)
    print("  Meta-Learning: 跨域策略迁移演示")
    print("=" * 60)

    meta_learner = MetaLearner()

    # ═══ Phase 1: 在源 envs 上训练 ═══
    source_envs = ["spring", "pendulum", "circuit"]
    print("\n── Phase 1: Training on source environments ──")

    for name in source_envs:
        env = make_env(name)
        ql = CausalQLearner(env)
        print(f"\n  Training {name} ({ql._skeleton_signature()}):")
        result = meta_learner.train_and_record(ql, name, n_episodes=60, verbose=True)
        print(f"    Final accuracy: {result['final_accuracy']:.0%}, converged: {result['converged']}")

    # ═══ Phase 2: 元学习总结 ═══
    print("\n── Phase 2: Meta-learning summary ──")
    print(meta_learner.summary())

    # ═══ Phase 3: 迁移测试 ═══
    target_name = "doppler"
    print(f"\n── Phase 3: Transfer to '{target_name}' ──")
    target_env = make_env(target_name)
    ql_target = CausalQLearner(target_env)
    print(f"  Target skeleton: {ql_target._skeleton_signature()}")
    print(f"  Variables: {target_env.variables}")

    # 3a: 从零训练 (baseline)
    print("\n  [Baseline] Training from scratch...")
    result_scratch = ql_target.train(n_episodes=40, verbose=False)
    print(f"    Final accuracy: {result_scratch['final_accuracy']:.0%}")

    # 3b: 用元策略初始化
    print("\n  [Meta-bootstrap] Training with meta-policy...")
    meta_ql = meta_learner.bootstrap(target_env)
    result_meta = meta_ql.train(n_episodes=40, verbose=False)
    print(f"    Final accuracy: {result_meta['final_accuracy']:.0%}")

    # 3c: 效率对比
    speedup = result_meta["final_accuracy"] - result_scratch["final_accuracy"]
    print(f"\n  Transfer efficiency: {speedup:+.0%}")
    if speedup > 0:
        print(f"  ✓ Meta-learning improved accuracy by {speedup:.0%}")
    elif speedup == 0:
        print(f"  → No difference (different skeleton, no knowledge transfer)")
    else:
        print(f"  ✗ Meta-learning hurt ({speedup:.0%})")

    # ═══ 持久化 ═══
    meta_learner.save()
    print(f"\n  Meta-knowledge saved to {MetaLearner.META_FILE}")


if __name__ == "__main__":
    demo()
