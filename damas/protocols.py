"""Three coordination protocols on the same world/tasks.

- chaxu（差序格局）：ego 环分带请求；环1 义务必应+完整上下文，
  环2 人情可拒+摘要，拒了有能力的活才疏远；覆盖不住 → 圈子外扩一格。
- flat（Agensh 式）：无中心无环，共享 claim 板自组织认领，
  全员读板（广播 token 大头），冲突按技能最优截断，一轮覆盖不住再 claim 一轮。
- star（中心 orchestrator）：全部消息过中心，中心串行排队（延迟线性增长），
  中心是单点。
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from damas.world import (World, Task, FULL_CONTEXT_TOKENS, DIGEST_CONTEXT_TOKENS,
                         SLICE_CONTEXT_TOKENS, PROPOSAL_TOKENS,
                         CLAIM_BOARD_TOKENS, CLAIM_TOKENS)


@dataclass
class Config:
    r1: int = 3            # 环1 人数（义务圈）
    r2: int = 4            # 环2 人数（人情圈）
    alpha: float = 0.05    # 受助成功的亲密度增量
    beta: float = 0.10     # 能帮不帮的疏远量
    p_decline: float = 0.3  # 环2 婉拒概率（人情有价）
    max_claims: int = 8    # 扁平模式单任务最多并行认领
    max_expand: int = 1    # 差序外扩次数上限


@dataclass
class StepResult:
    success: bool
    rounds: int
    tokens: int
    messages: int
    expanded: bool = False
    note: str = ""


def _contributors(world: World, pairs) -> list:
    return [(world.agents[h], bonus) for h, bonus in pairs]


# ———————————————————————————————— 差序格局 ————————————————————————————————

def run_chaxu(world: World, task: Task, rng: random.Random, cfg: Config,
              disabled: frozenset = frozenset()) -> StepResult:
    tokens = messages = rounds = 0
    contributors: list = []
    ego = task.ego
    ring1, ring2 = world.rings(ego, cfg.r1, cfg.r2)
    expansions_left = cfg.max_expand
    expanded = False

    while True:
        rounds += 1
        # 环1：义务必应，收完整上下文
        for h in ring1:
            if h in disabled:
                continue
            tokens += FULL_CONTEXT_TOKENS + PROPOSAL_TOKENS
            messages += 2
            contributors.append((h, 0.15))
        # 环2：收摘要，顺手才帮；有能力而婉拒才疏远（能力不足不怪）
        for h in ring2:
            if h in disabled:
                continue
            tokens += DIGEST_CONTEXT_TOKENS + CLAIM_TOKENS
            messages += 2
            a = world.agents[h]
            relevant = any(a.covers(s, task.level, slack=0.05) for s in task.skills)
            if relevant and rng.random() >= cfg.p_decline:
                tokens += PROPOSAL_TOKENS
                contributors.append((h, 0.05))
            elif relevant:
                world.alienate(ego, h, cfg.beta)

        if not task.unsolved(_contributors(world, contributors)):
            break
        if expansions_left <= 0:
            break
        # 圈子外扩一格：新入带者是显式请求来的远亲——收完整上下文、
        # 力所能及即应（远亲难得答应，不设婉拒）
        expansions_left -= 1
        expanded = True
        _, new_band = world.rings(ego, cfg.r1 + cfg.r2, cfg.r2 + 4)
        for h in new_band:
            if h in disabled:
                continue
            tokens += FULL_CONTEXT_TOKENS + PROPOSAL_TOKENS
            messages += 2
            a = world.agents[h]
            if any(a.covers(s, task.level, slack=0.05) for s in task.skills):
                contributors.append((h, 0.15))

        if not task.unsolved(_contributors(world, contributors)):
            break
        break  # 只外扩一次，仍不覆盖即失败

    success = not task.unsolved(_contributors(world, contributors))
    if success:
        for h, _b in contributors:
            world.reward(ego, h, cfg.alpha)
    return StepResult(success, rounds, tokens, messages, expanded=expanded)


# ———————————————————————————————— 扁平 claim ————————————————————————————————

def run_flat(world: World, task: Task, rng: random.Random, cfg: Config,
             removed: frozenset = frozenset()) -> StepResult:
    pool = [a for a in world.agents if a.aid not in removed and a.aid != task.ego]
    tokens = messages = rounds = 0
    contributors: list = []

    for attempt in (0, 1):  # claim 板常驻工作区：第二轮只需再 claim
        rounds += 1
        if attempt == 0:
            tokens += CLAIM_BOARD_TOKENS * len(pool)
            messages += 1  # 一次发布
        slack = 0.05 - 0.05 * attempt  # 第二轮放宽到恰好达标
        claimers = [a for a in pool
                    if any(a.covers(s, task.level, slack) for s in task.skills)]
        if len(claimers) > cfg.max_claims:  # 认领冲突：技能总量最优者留下
            claimers.sort(key=lambda a: (-sum(a.skills.get(s, 0.0)
                                              for s in task.skills), a.aid))
            for a in claimers[cfg.max_claims:]:
                tokens += CLAIM_TOKENS
            claimers = claimers[:cfg.max_claims]
        for a in claimers:
            tokens += CLAIM_TOKENS + PROPOSAL_TOKENS
            messages += 2
            contributors.append((a, 0.0))
        if not task.unsolved(contributors):
            break

    success = not task.unsolved(contributors)
    return StepResult(success, rounds, tokens, messages)


# ———————————————————————————————— 中心星型 ————————————————————————————————

def run_star(world: World, task: Task, rng: random.Random, cfg: Config,
             center_down: bool = False, queue_len: int = 0) -> StepResult:
    center = 0
    if center_down:
        return StepResult(False, 0, 0, 0, note="center_down")
    tokens = messages = 0
    workers = [a.aid for a in world.agents if a.aid != center and a.aid != task.ego]
    tokens += FULL_CONTEXT_TOKENS + PROPOSAL_TOKENS   # ego→中心 上下文往返
    messages += 2
    tokens += SLICE_CONTEXT_TOKENS * len(workers)     # 中心向全员发切片
    messages += len(workers)
    contributors: list = []
    for h in workers:
        a = world.agents[h]
        if any(a.covers(s, task.level, slack=0.05) for s in task.skills):
            tokens += PROPOSAL_TOKENS
            contributors.append((h, 0.05))
        else:
            tokens += CLAIM_TOKENS                    # 谢绝回执也占一条消息
    success = not task.unsolved([(world.agents[h], b) for h, b in contributors])
    return StepResult(success, rounds=2 + 2 * queue_len, tokens=tokens,
                      messages=messages + len(workers))
