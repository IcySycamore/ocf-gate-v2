"""
    Plan Gate
    计划阶段的事实：agent 给的计划、审计结果、人类声明的环境。

    读者是进 executing 的那道门，也就是 validate()。这里只管事实自身的完整性——
    "计划的 Files 有没有碰保护清单"需要保护清单作为额外输入，是另一道门。
"""
from dataclasses import dataclass

from .abstract_fact import AbstractFact, Rule


@dataclass
class PlanFact(AbstractFact):
    """
    计划阶段的事实

    计划可以只在对话里给，也可以落成文件。落成文件时 Steps 和 Files 必须有内容：
    Files 还要拿去跟保护清单比对，所以它不能空。
    """
    plan_path: str = ""     # 计划文件路径；空 = 计划只存在于对话里
    steps: str = ""         # 计划的 Steps 段落
    files: str = ""         # 计划的 Files 段落
    p0_count: str = ""      # plan-auditor 报的 P0 数；空 = 还没审
    stack_env: str = ""     # 人类声明的环境

    RULES = (
        Rule("plan_path", required=False),
        Rule("steps",
             condition=lambda fact: not fact.plan_path.strip() or bool(fact.steps.strip()),
             description="给了计划文件就必须有 Steps"),
        Rule("files",
             condition=lambda fact: not fact.plan_path.strip() or bool(fact.files.strip()),
             description="给了计划文件就必须有 Files"),
        Rule("p0_count",
             condition=lambda fact: fact.p0_count.strip().isdigit() and int(fact.p0_count) == 0,
             description="必须是 0；空值也算失败，先跑 plan-auditor 再记结果"),
        Rule("stack_env",
             condition=lambda fact: len(fact.stack_env.strip()) >= 4,
             description="至少 4 个字符：人类要声明可用环境"),
    )
