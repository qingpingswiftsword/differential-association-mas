# differential-association-mas

**差序格局 × 多智能体协作** — Fei Xiaotong's *differential mode of association* (《乡土中国》, 1948) as an organizational prior for multi-agent systems. A deterministic, zero-API-cost simulation comparing it against flat peer self-organization (Agensh-style claim loops, [arXiv:2609.26781](https://arxiv.org/abs/2609.26781)) and central orchestration.

> "社会关系……好像把一块石头丢在水面上所发生的一圈圈推出去的波纹。" —— 费孝通

## The idea

Every agent keeps a **closeness matrix** (亲疏表). When an agent (ego) receives a task, it drops a stone in water:

- **Ring 1**（义务圈，top-3 closest）: must respond, receives full context (200t)
- **Ring 2**（人情圈，next-4）: helps only if it happens to fit (顺手才帮), receives digest (40t); declining a job it *could* have done alienates it (−β)
- **Beyond**（圈外）: never touches the task — unless coverage fails and the **ripple expands one band outward**（圈子外扩）, the伸缩性 that lets 差序格局 survive rare needs

After success, ego's closeness toward every helper rises (+α) — **rings drift with reciprocity**, no fixed org chart.

## 现实映射：哪些多智能体场景天然需要差序

差序格局不是复古审美，它对应四条现实约束：**上下文=钱**（全文只喂得起少数）、**权限与合规**（"亲"就是访问边界）、**带宽物理受限**（广播不可行）、**责任与互惠**（必应 vs 可拒）。下面每个场景都同时踩中不止一条：

**① 软件研发智能体团队**（上下文=钱 · 责任分层）
monorepo 全库上下文动辄上百 k token，喂不起全员广播。环1 = 同仓库常驻 agent，义务必应 review、收全文；环2 = 相邻模块 agent，收 diff 摘要、顺手才帮；编译器后端、安全审计等生僻需求触发外扩拉专家；常年互相 review 的圈子随互惠自然收紧。

**② 医院多智能体会诊**（权限与合规 · 责任分层）
电子病历全文受隐私合规约束——"亲疏"在这里就是访问控制，不只是省钱。环1 = 主诊团，义务必应（首诊负责制）、收病历全文；环2 = 其他科室，去标识摘要、会诊排期可拒（拒了伤声誉 = −β）；罕见病外扩跨院专家池。对照：所有会诊排一个总调度 = 星型的中心单点，宕机全院停摆。

**③ 量化研究 agent 集群**（权限与合规 · 上下文=钱）
私有因子假设/信号不广播——claim 板在这里就是泄密白板。环1 = 同策略组，共享完整假设链与原始信号；环2 = 跨组，只收结论摘要，且**能及而不该看的人根本不在环里**（环成员资格是比婉拒更早的一层防御）；因子贡献追溯 = 关系漂移的记账。

**④ 仓储机器人集群**（带宽物理受限）
Wi-Fi 信道竞争让全队广播物理不可行——O(k) 在这里不是经济学选择，是物理必然。环1 = 同巷道/同班次机器人，收全量状态；环2 = 邻区，心跳摘要；任务超本地能力跨区呼叫支援（外扩）。对照：中心调度器单点死亡 = 本 demo 中唯一 0% 恢复的形态。

**⑤ 开源社区 maintainer 层级**（责任分层 · 互惠记账）
回到人类社会本身：Linux kernel 的 reviewer 层级就是差序格局的活标本——这套协议不是发明，是观察。环1 = subsystem maintainer，PR 义务必应 review；环2 = 常驻 contributor，顺手才帮，能 review 而不 review 伤关系；coverage 失败才发 RFC 全员广播（最贵也最少用）；commit credit 让亲疏表随贡献漂移，无固定组织架构图。

> 对照读法：flat 假设"广播给所有人、大家抢着做"，在**权限、带宽、成本**三面墙前同时不成立；star 把所有协调压给一个中心，对应现实中"所有事等一个调度者"的队列（本 demo 中 p50=62 轮、通信 Gini 0.70）。

## Three protocols, one stage

| | chaxu 差序格局 | flat 扁平 claim（Agensh 式） | star 中心编排 |
|---|---|---|---|
| 结构 | ego 环分带 O(k) | 共享 claim 板 O(n) 广播 | 全消息过中心 O(n) |
| 上下文策略 | 全文/摘要按环衰减 | 全员可读 | 中心切片分发 |
| 冲突处理 | 无（圈层即序） | 技能最优者留下 | 中心排队串行 |
| 单点故障 | 无（外扩即重构） | 无 | **中心死亡 → 全停** |

## Quick start

```bash
python3 run_demo.py --sweep          # 三模式对比 + 规模扫描 → results/demo.json
python3 -m http.server 8000          # 打开 http://localhost:8000/viz/index.html
```

No dependencies, no API keys, fully deterministic (`--seed`). Python ≥ 3.10.

## What the numbers say (seed 7, 24 agents, 60 tasks)

| mode | success | rounds p50/p95 | tokens/task | comm. Gini | post-fail recovery |
|---|---|---|---|---|---|
| chaxu | 86.7% | 1 / 1 | **1717** | 0.27 | **75.0%** |
| flat | 76.7% | 1 / 2 | 2603 | 0.13 | 66.7% |
| star | 85.0% | 62 / 114 | 1945 | **0.70** | **0%** (single point) |

**Communication Gini** over per-agent message touches — the paper's *organizational specialization* axis, quantified: star funnels everything through the center (0.70, near-monopoly), flat spreads it evenly (0.13, no structure at all), chaxu sits between (0.27, a stable core–periphery). Structured ≠ unequal: 差序格局 keeps a core without a single point of failure.

Token composition per task (chaxu / flat / star):

Scaling sweep (tokens/task by population):

| agents | chaxu | flat | star |
|---|---|---|---|
| 12 | 1314 | 1293 | 1015 |
| 24 | 1717 | 2603 | 1945 |
| 48 | 1874 | 5136 | 3849 |
| 96 | **1933** | **10171** | **7653** |

## Ablations — which ring does the work

Five chaxu variants, everything else fixed (`run_demo.py` runs them by default):

| variant | success | tokens/task | Gini | what it proves |
|---|---|---|---|---|
| 默认 | 86.7% | 1717 | 0.27 | — |
| **无外扩** `max_expand=0` | **51.7%** | 916 | 0.31 | **外扩是承重墙**（−35.0pp） |
| 宽环 r1=5,r2=8 | 86.7% | 2114 | 0.23 | 同成功率贵 ~400t — 圈子不是越大越好 |
| 无互惠 α=β=0 | 86.7% | 1806 | 0.28 | 关系漂移不承担成功率，只承担成本形状 |
| 无婉拒 p=0 | 86.7% | 1671 | 0.27 | 婉拒机制近似中性 |

The headline: **ring expansion is the load-bearing wall.** Remove it and 差序格局 degenerates into a smaller flat group (51.7% ≈ flat's success at less than flat's cost). Keeping rings *small* and expanding *only on coverage failure* is exactly the economic bargain 费孝通 described — 平时维持小圈子，事到临头才外扩.

Difficulty breakdown (seed 7): hard 3-skill tasks are where chaxu's rings visibly strain (64.3% vs 100% for easy) — expansion covers the gap but not for free.

**The stable finding across seeds:** 差序格局 wins context cost — rings are O(k), broadcast and star topologies are O(n), and the gap grows with scale (5× at n=96). It also wins failure recovery: ring expansion *is* reorganization, while a dead center is dead. **It does not claim the success-rate crown** — full-population pools (flat/star) beat it on some seeds. No free organizational structure; only fit for context.

## Honest boundaries

- All agents are rule-based heuristics, no LLM calls
- Tokens are a fixed charging model (full 200 / digest 40 / slice 60 / proposal 30 / claim-board 100 / claim 10)
- star's rounds include a linear queue-wait model (center serializes coordination)
- The point is organizational mechanics, not benchmark SOTA

## Layout

```
damas/world.py        agents, closeness matrix, ring assignment, reciprocity updates
damas/protocols.py    run_chaxu / run_flat / run_star (token-composition + touch accounting)
damas/tasks.py        (in world.py) seeded synthetic tasks
damas/metrics.py      aggregation: percentiles, Gini, batch/difficulty buckets, closeness evolution
run_demo.py           CLI: baseline + failure injection + scale sweep + 5-variant ablation + viz export
viz/index.html        ripple animation + 11 charts incl. token breakdown, Gini, ablations (reads results/demo.json)
```

## References

- 费孝通《乡土中国·差序格局》(1948) — *From the Soil*
- Agensh: Scaling Organizational Intelligence to 1,024 Agents ([arXiv:2609.26781](https://arxiv.org/abs/2609.26781))

## License

MIT
