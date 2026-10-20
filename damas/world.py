"""World model: agents, skill vectors, closeness matrix, ring assignment.

差序格局的唯一结构是亲疏表 closeness[ego][other]：环只是它的 top-k 分带，
波纹的推与收都由互惠更新驱动（受助则亲、能帮不帮则疏）。
除初始同队加分外，不存在任何固定组织结构。
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

SKILLS = ("research", "planning", "coding", "review", "ops", "writing")

# 上下文计费常量（token 模型，全模式统一口径）
FULL_CONTEXT_TOKENS = 200    # 完整任务上下文（环1／中心收到）
DIGEST_CONTEXT_TOKENS = 40   # 摘要上下文（环2 收到）
SLICE_CONTEXT_TOKENS = 60    # 子任务切片（星型 worker 收到）
PROPOSAL_TOKENS = 30         # 一份协助提案
CLAIM_BOARD_TOKENS = 100     # 扁平模式每 agent 每任务读共享 claim 板
CLAIM_TOKENS = 10            # 一次 claim 消息

SAME_TEAM_BONUS = 0.3


@dataclass
class Agent:
    aid: int
    team: int
    skills: dict = field(default_factory=dict)  # skill -> level 0..1

    def covers(self, skill: str, level: float, slack: float = 0.0) -> bool:
        return self.skills.get(skill, 0.0) >= level - slack


@dataclass
class Task:
    tid: int
    ego: int
    skills: tuple            # 需要的技能名
    level: float             # 每项技能要求的达标线

    def unsolved(self, contributors) -> list:
        """返回尚无合格贡献者的技能；contributors: [(Agent, quality_bonus)]。"""
        missing = []
        for s in self.skills:
            best = max((a.skills.get(s, 0.0) + bonus for a, bonus in contributors),
                       default=0.0)
            if best < self.level:
                missing.append(s)
        return missing


class World:
    """N 个 agent + 全体两两亲疏表。所有随机性由 seed 确定。"""

    def __init__(self, n_agents: int, n_teams: int, seed: int,
                 skill_profile: str = "uniform"):
        rng = random.Random(seed)
        self.n = n_agents
        self.agents: list[Agent] = []
        for aid in range(n_agents):
            n_skills = rng.randint(2, 4)
            picks = rng.sample(SKILLS, n_skills)
            skills = {s: round(rng.uniform(0.3, 1.0), 3) for s in picks}
            self.agents.append(Agent(aid, team=aid % n_teams, skills=skills))
        # 亲疏表：ego 视角，初始只有同队加分
        self.closeness: list[list[float]] = [
            [0.0] * n_agents for _ in range(n_agents)]
        for i in range(n_agents):
            for j in range(n_agents):
                if i != j and self.agents[i].team == self.agents[j].team:
                    self.closeness[i][j] = SAME_TEAM_BONUS
        self.rng = random.Random(seed * 31 + 7)

    # —— 差序：环分配 ——

    def rank(self, ego: int) -> list[int]:
        others = [j for j in range(self.n) if j != ego]
        others.sort(key=lambda j: (-self.closeness[ego][j], j))
        return others

    def rings(self, ego: int, r1: int = 3, r2: int = 4):
        order = self.rank(ego)
        return order[:r1], order[r1:r1 + r2]

    # —— 互惠更新 ——

    def reward(self, ego: int, helper: int, alpha: float) -> None:
        self.closeness[ego][helper] = min(1.0, self.closeness[ego][helper] + alpha)

    def alienate(self, ego: int, other: int, beta: float) -> None:
        self.closeness[ego][other] = max(0.0, self.closeness[ego][other] - beta)


def make_tasks(world: World, n_tasks: int, seed: int) -> list[Task]:
    rng = random.Random(seed * 17 + 3)
    tasks = []
    for tid in range(n_tasks):
        n_req = rng.randint(2, 3)
        skills = tuple(sorted(rng.sample(SKILLS, n_req)))
        tasks.append(Task(tid=tid, ego=rng.randrange(world.n),
                          skills=skills, level=round(rng.uniform(0.5, 0.95), 3)))
    return tasks
