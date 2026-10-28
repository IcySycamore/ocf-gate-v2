"""PlanFact 的验收：口头计划放行、落成文件就要 Steps/Files、P0 必须为 0。"""
import unittest
from dataclasses import fields, replace

from state_machine.plan_gate import PlanFact


CHAT_ONLY = PlanFact(
    plan_path="",
    steps="",
    files="",
    p0_count="0",
    stack_env="conda: ppt-master",
)


def fact(**overrides: object) -> PlanFact:
    return replace(CHAT_ONLY, **overrides)


class PlanFactTests(unittest.TestCase):

    def test_rules_cover_every_field(self):
        names = sorted(item.name for item in fields(PlanFact))
        rules = sorted(rule.name for rule in PlanFact.RULES)
        self.assertEqual(rules, names)

    def test_chat_only_plan_passes(self):
        ok, problems = CHAT_ONLY.validate()
        self.assertIs(ok, True)
        self.assertEqual(problems, [])

    def test_plan_file_without_steps_is_refused(self):
        ok, problems = fact(plan_path="plans/x.md", steps="", files="## Files\n- a.py").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["steps"])

    def test_plan_file_without_files_is_refused(self):
        ok, problems = fact(plan_path="plans/x.md", steps="## Steps\n- 一步", files="").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["files"])

    def test_plan_file_with_both_sections_passes(self):
        ok, problems = fact(plan_path="plans/x.md",
                            steps="## Steps\n- 一步",
                            files="## Files\n- a.py").validate()
        self.assertIs(ok, True)
        self.assertEqual(problems, [])

    def test_steps_and_files_are_free_when_the_plan_is_in_chat(self):
        """口头计划没有文件，Steps/Files 就不该被要求。"""
        ok, problems = fact(plan_path="", steps="", files="").validate()
        self.assertIs(ok, True)
        self.assertEqual(problems, [])

    def test_p0_count_must_be_recorded(self):
        ok, problems = fact(p0_count="").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["p0_count"])
        self.assertIn("plan-auditor", PlanFact.explain(problems))

    def test_p0_count_must_be_zero(self):
        ok, problems = fact(p0_count="2").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["p0_count"])

    def test_p0_count_must_be_a_number(self):
        ok, problems = fact(p0_count="两个").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["p0_count"])

    def test_stack_env_needs_a_real_declaration(self):
        ok, problems = fact(stack_env="py").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["stack_env"])
        self.assertIn("至少 4 个字符", PlanFact.explain(problems))

    def test_reset_clears_everything(self):
        fresh = replace(fact(plan_path="plans/x.md", p0_count="0"))
        fresh.reset()
        self.assertEqual((fresh.plan_path, fresh.p0_count, fresh.stack_env), ("", "", ""))
        self.assertEqual(fresh.validate(), (False, ["p0_count", "stack_env"]))


if __name__ == "__main__":
    unittest.main()
