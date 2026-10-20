"""damas — Differential-mode-of-Association Multi-Agent System.

费孝通《乡土中国》(1948) 的"差序格局"（differential mode of association）
作为多智能体协作的组织先验：以己为中心、亲疏分环、义务与信息随圈层衰减。
与 flat mesh（Agensh 式 claim loop）和 central orchestrator（星型）同场对比。
"""
from damas.world import World, Agent, Task
from damas.protocols import run_chaxu, run_flat, run_star, StepResult

__version__ = "0.1.0"
