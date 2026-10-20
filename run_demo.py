#!/usr/bin/env python3
"""differential-association-mas — 差序格局 vs 扁平自组织 vs 中心编排 三模式对比.

Zero API keys, fully deterministic (seeded). Example:

    python run_demo.py --agents 24 --teams 4 --tasks 60 --seed 7

主表永远是干净 baseline；--fail-at 0.4 额外做一次故障注入仿真，
单独报告 post-fail 成功率（恢复力对比）：
    chaxu → ego 的环1 不可用（只能外扩重构圈子）；
    flat  → 30% 的 agent 退出认领池；
    star  → 中心 orchestrator 死亡（单点故障，无恢复）。
"""
from __future__ import annotations

import argparse
import random
import sys
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from damas.world import World, make_tasks                          # noqa: E402
from damas.protocols import Config, run_chaxu, run_flat, run_star  # noqa: E402
from damas.metrics import RunStats, comparison_table, dump_json    # noqa: E402

MODES = ("chaxu", "flat", "star")


def simulate(mode: str, n_agents: int, n_teams: int, tasks, cfg: Config,
             seed: int, fail_at: float = 0.0) -> RunStats:
    world = World(n_agents, n_teams, seed)   # 每次仿真从同一起点出发
    rng = random.Random(seed * 101 + zlib.crc32(mode.encode()))
    stats = RunStats(mode=mode)
    fail_from = int(len(tasks) * fail_at)
    flat_removed = frozenset()
    if fail_from and mode == "flat":
        pool = [a.aid for a in world.agents if a.aid != 0]
        flat_removed = frozenset(world.rng.sample(pool, k=max(1, int(0.3 * world.n))))
    for i, task in enumerate(tasks):
        failed_phase = bool(fail_from) and i >= fail_from
        if mode == "chaxu":
            ring1, _ = world.rings(task.ego, cfg.r1, cfg.r2)
            disabled = frozenset(ring1) if failed_phase else frozenset()
            res = run_chaxu(world, task, rng, cfg, disabled=disabled)
        elif mode == "flat":
            res = run_flat(world, task, rng, cfg,
                           removed=flat_removed if failed_phase else frozenset())
        else:
            res = run_star(world, task, rng, cfg,
                           center_down=failed_phase, queue_len=i)
        if not failed_phase:
            stats.add(res)
        else:
            stats.post_failure_tasks += 1
            stats.post_failure_success += bool(res.success)
    return stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--agents", type=int, default=24)
    ap.add_argument("--teams", type=int, default=4)
    ap.add_argument("--tasks", type=int, default=60)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--fail-at", type=float, default=0.4,
                    help="故障注入点（任务进度比例，0 关闭）")
    ap.add_argument("--sweep", action="store_true",
                    help="追加规模扫描：agents∈{12,24,48,96} 的 tokens/task")
    ap.add_argument("--out", default="results/demo.json")
    args = ap.parse_args()

    world0 = World(args.agents, args.teams, args.seed)
    tasks = make_tasks(world0, args.tasks, args.seed)
    cfg = Config()

    baseline = {m: simulate(m, args.agents, args.teams, tasks, cfg,
                            args.seed, fail_at=0.0) for m in MODES}
    injected = ({m: simulate(m, args.agents, args.teams, tasks, cfg,
                             args.seed, fail_at=args.fail_at) for m in MODES}
                if args.fail_at else None)
    for m in MODES:
        if injected:
            baseline[m].post_failure_success = injected[m].post_failure_success
            baseline[m].post_failure_tasks = injected[m].post_failure_tasks

    print(f"agents={args.agents} teams={args.teams} tasks={args.tasks} "
          f"seed={args.seed} fail_at={args.fail_at or 'off'}\n")
    print(comparison_table([baseline[m] for m in MODES]))
    print("\nchaxu: 环1 义务必应+全文 / 环2 人情可拒+摘要 / 覆盖不住外扩一圈")
    print("flat : 共享 claim 板全员可读，自组织认领（广播即成本）")
    print("star : 全消息过中心，中心串行排队，中心即单点")
    print("\npost-fail 列来自独立的故障注入仿真（baseline 主表不受影响）")

    payload = {
        "params": vars(args),
        "baseline": {m: baseline[m].as_dict() for m in MODES},
        "post_failure": ({m: injected[m].as_dict() for m in MODES}
                         if injected else None),
        "token_model": {"full": 200, "digest": 40, "slice": 60,
                        "proposal": 30, "claim_board": 100, "claim": 10},
    }
    if args.sweep:
        sweep = []
        for n in (12, 24, 48, 96):
            w = World(n, 4, args.seed)
            t = make_tasks(w, args.tasks, args.seed)
            row = {"agents": n}
            for m in MODES:
                s = simulate(m, n, 4, t, cfg, args.seed, fail_at=0.0)
                row[m] = s.as_dict()["context_tokens_per_task"]
            sweep.append(row)
        payload["sweep"] = sweep
        print("sweep:", [(r["agents"], r["chaxu"], r["flat"], r["star"])
                         for r in sweep])
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    dump_json(out, payload)

    # 涟漪可视化数据：agent 列表、亲疏矩阵、样例任务（页面端自行算环）
    viz = {
        "seed": args.seed,
        "agents": [{"aid": a.aid, "team": a.team, "skills": a.skills}
                   for a in world0.agents],
        "closeness": world0.closeness,
        "tasks": [{"tid": t.tid, "ego": t.ego, "skills": list(t.skills),
                   "level": t.level} for t in tasks[:12]],
    }
    dump_json(Path("viz/data.json"), viz)
    print(f"JSON → {out}\nviz  → viz/data.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
