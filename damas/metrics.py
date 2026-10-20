"""Run aggregation: per-mode totals, comparison table, JSON dump."""
from __future__ import annotations

import json
from dataclasses import dataclass, field


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

    def add(self, res) -> None:
        self.n_tasks += 1
        self.success += bool(res.success)
        self.tokens += res.tokens
        self.messages += res.messages
        self.rounds += res.rounds
        self.expanded += bool(res.expanded)

    def as_dict(self) -> dict:
        return {
            "mode": self.mode,
            "success_rate": round(self.success / self.n_tasks, 4) if self.n_tasks else 0.0,
            "avg_rounds_per_task": round(self.rounds / self.n_tasks, 2) if self.n_tasks else 0.0,
            "context_tokens_total": self.tokens,
            "context_tokens_per_task": round(self.tokens / self.n_tasks, 1) if self.n_tasks else 0.0,
            "messages_total": self.messages,
            "expansion_rate": round(self.expanded / self.n_tasks, 4) if self.n_tasks else 0.0,
            "post_failure_success_rate": (
                round(self.post_failure_success / self.post_failure_tasks, 4)
                if self.post_failure_tasks else None),
        }


def comparison_table(stats: list[RunStats]) -> str:
    headers = ("mode", "success", "avg_rounds", "tokens/task", "msgs_total",
               "expand", "post-fail")
    rows = []
    for s in stats:
        d = s.as_dict()
        rows.append((
            d["mode"], f"{d['success_rate']:.1%}", f"{d['avg_rounds_per_task']:.1f}",
            f"{d['context_tokens_per_task']:.0f}", str(d["messages_total"]),
            f"{d['expansion_rate']:.1%}",
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
