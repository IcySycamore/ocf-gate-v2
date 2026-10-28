"""
    Intake Gate
    受理阶段的事实：人类和 agent 一起填的那几项，加上机器数出来的盘问轮数。

    读者是进 planning 的那道门，也就是 validate()：规则里标为必填的项非空即通过。
    受理事实只在 asking 期间存在，离开 asking 时由 reset() 清空（见 docs/facts.md）。
"""
from dataclasses import dataclass

from .abstract_fact import AbstractFact, Rule


@dataclass
class IntakeFact(AbstractFact):
    """
    受理阶段的事实

    必填与否写在 RULES 里，不写在字段上：那是策略，会变；字段是形状，不该跟着变。
    """
    goal: str = ""            # 目标
    tool: str = ""            # 工具
    deliverable: str = ""     # 交付物
    consenus: str = ""        # 经人类确认的共识原文
    constraints: str = ""     # 经人类确认的约束原文
    reference: str = ""       # 参考资料
    code_style: str = ""      # 代码风格
    design_style: str = ""    # 设计风格
    plan_style: str = ""      # 计划形式
    grill_style: str = ""     # 盘问形式
    grill_rounds: int = 0     # 盘问轮数，人类每回话一次加一

    RULES = (
        Rule("goal"),
        Rule("tool"),
        Rule("deliverable"),
        Rule("consenus"),
        Rule("constraints"),
        Rule("reference", required=False),
        Rule("code_style", required=False),
        Rule("design_style", required=False),
        Rule("plan_style", required=False),
        Rule("grill_style", required=False),
        Rule("grill_rounds",
             condition=lambda fact: fact.grill_rounds >= 1,
             description="至少盘问 1 轮"),
    )
