"""Run aggregation: per-mode totals, distributions, org-structure metrics,
comparison table, JSON dump.

论文式指标：成功率、成本（token 总量与构成）、延迟（rounds 分布）、
组织特化（通信触达基尼系数）、亲疏演化（top-5 亲密度份额）、
学习曲线（分批成功率）、难度分桶。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field


def gini(values) -> float:
    """基尼系数：0=完全均衡（人人平等），1=极端集中（单点独大）。"""
    v = sorted(x for x in values if x is not None)
    n = len(v)
    if not n or sum(v) == 0:
        return 0.0
    return round(sum((2 * i - n - 1) * x for i, x in enumerate(v, 1))
                 / (n * sum(v)), 4)


def pctl(values, q: float) -> float:
    v = sorted(values)
    if not v:
        return 0.0
    k = min(len(v) - 1, max(0, int(round(q * (len(v) - 1)))))
    return round(v[k], 2)


@dataclass
class RunStats:
    mode: str
    n_tasks: int = 0
    success: int = 0
    tokens: int = 0
    messages: int = 0
    rounds: int = 0
    expanded: int = 0
    post_failure_success: int = 0
    post_failure_tasks: int = 0
    tokens_by: dict = field(default_factory=dict)
    per_task: list = field(default_factory=list)      # [(success, rounds)]
    difficulty: dict = field(default_factory=dict)    # key -> [succ, total]
    touches: dict = field(default_factory=dict)       # aid -> count
    close_shares: list = field(default_factory=list)  # 批次级 top-5 亲密度份额

    def add(self, res, diff_key: str = "") -> None:
        self.n_tasks += 1
        self.success += bool(res.success)
        self.tokens += res.tokens
        self.messages += res.messages
        self.rounds += res.rounds
        self.expanded += bool(res.expanded)
        for k, v in res.tokens_by.items():
            self.tokens_by[k] = self.tokens_by.get(k, 0) + v
        self.per_task.append((bool(res.success), res.rounds))
        if diff_key:
            cell = self.difficulty.setdefault(diff_key, [0, 0])
            cell[0] += bool(res.success)
            cell[1] += 1
        for aid, n in res.touches.items():
            self.touches[aid] = self.touches.get(aid, 0) + n

    def as_dict(self) -> dict:
        rounds_list = [r for _s, r in self.per_task]
        batches = [self.per_task[i:i + max(1, self.n_tasks // 4)]
                   for i in range(0, self.n_tasks, max(1, self.n_tasks // 4))][:4]
        return {
            "mode": self.mode,
            "success_rate": round(self.success / self.n_tasks, 4) if self.n_tasks else 0.0,
            "avg_rounds_per_task": round(self.rounds / self.n_tasks, 2) if self.n_tasks else 0.0,
            "rounds_p50": pctl(rounds_list, 0.5),
            "rounds_p95": pctl(rounds_list, 0.95),
            "context_tokens_total": self.tokens,
            "context_tokens_per_task": round(self.tokens / self.n_tasks, 1) if self.n_tasks else 0.0,
            "tokens_by": self.tokens_by,
            "messages_total": self.messages,
            "expansion_rate": round(self.expanded / self.n_tasks, 4) if self.n_tasks else 0.0,
            "gini_touches": gini(self.touches.values()),
            "batch_success": [round(sum(s for s, _ in b) / len(b), 4)
                              if b else None for b in batches],
            "difficulty": {k: round(v[0] / v[1], 4) if v[1] else None
                           for k, v in sorted(self.difficulty.items())},
            "closeness_top5_share": [round(s, 4) for s in self.close_shares],
            "post_failure_success_rate": (
                round(self.post_failure_success / self.post_failure_tasks, 4)
                if self.post_failure_tasks else None),
        }


def comparison_table(stats: list) -> str:
    headers = ("mode", "success", "rounds", "tokens/task", "msgs", "gini", "expand",
               "post-fail")
    rows = []
    for s in stats:
        d = s.as_dict()
        rows.append((
            d["mode"], f"{d['success_rate']:.1%}", f"{d['avg_rounds_per_task']:.1f}",
            f"{d['context_tokens_per_task']:.0f}", str(d["messages_total"]),
            f"{d['gini_touches']:.2f}", f"{d['expansion_rate']:.1%}",
            "-" if d["post_failure_success_rate"] is None
            else f"{d['post_failure_success_rate']:.1%}"))
    widths = [max(len(h), max(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    line = "| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |"
    sep = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    body = "\n".join("| " + " | ".join(c.ljust(w) for c, w in zip(r, widths)) + " |"
                     for r in rows)
    return "\n".join((line, sep, body))


def dump_json(path, payload: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
