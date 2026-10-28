"""IntakeFact 的验收：哪几项必填、盘问轮数怎么算、重置清哪些。"""
import unittest
from dataclasses import fields, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from state_machine.intake_gate import IntakeFact


FULL = IntakeFact(
    goal="重构状态机",
    tool="python, unittest",
    deliverable="可运行的 gate 模块",
    consenus="受理期只收集，不改文件",
    constraints="只允许标准库",
    reference="docs/facts.md",
    code_style="snake_case",
    design_style="纯函数优先",
    plan_style="先写测试",
    grill_style="一轮一个问题",
    grill_rounds=3,
)


def fact(**overrides: object) -> IntakeFact:
    """一份填满的受理事实；只覆盖需要改的那几项。"""
    return replace(FULL, **overrides)


class IntakeFactTests(unittest.TestCase):

    def test_rules_cover_every_field(self):
        """规则数组和字段必须一一对应，否则 validate() 会抛 RuleMismatch。"""
        names = sorted(item.name for item in fields(IntakeFact))
        rules = sorted(rule.name for rule in IntakeFact.RULES)
        self.assertEqual(rules, names)

    def test_full_intake_passes(self):
        ok, problems = FULL.validate()
        self.assertIs(ok, True)
        self.assertEqual(problems, [])

    def test_missing_required_field_is_named(self):
        ok, problems = fact(goal="").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["goal"])

    def test_whitespace_only_counts_as_empty(self):
        ok, problems = fact(tool="  \t\n ").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["tool"])

    def test_optional_field_may_be_empty(self):
        ok, problems = fact(reference="", design_style="").validate()
        self.assertIs(ok, True)
        self.assertEqual(problems, [])

    def test_grill_rounds_needs_at_least_one_round(self):
        ok, problems = fact(grill_rounds=0).validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["grill_rounds"])
        self.assertEqual(IntakeFact.explain(problems), "grill_rounds: 至少盘问 1 轮")

    def test_multiple_missing_are_listed_in_declaration_order(self):
        ok, problems = fact(goal="", tool="", deliverable="").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["goal", "tool", "deliverable"])

    def test_reset_clears_strings_and_rounds(self):
        fresh = replace(FULL)
        fresh.reset()
        self.assertEqual(fresh.goal, "")
        self.assertEqual(fresh.grill_rounds, 0)
        self.assertEqual(fresh.validate(), (False, ["goal", "tool", "deliverable",
                                                    "consenus", "constraints",
                                                    "grill_rounds"]))

    def test_update_reads_the_intake_file(self):
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        path = Path(scratch.name) / "intake_fact.txt"
        path.write_text("goal=重构状态机\ngrill_rounds=2\n", encoding="utf-8")

        fresh = IntakeFact()
        fresh.update(path)
        self.assertEqual((fresh.goal, fresh.grill_rounds), ("重构状态机", 2))
        self.assertEqual(fresh.validate(), (False, ["tool", "deliverable",
                                                    "consenus", "constraints"]))


if __name__ == "__main__":
    unittest.main()
