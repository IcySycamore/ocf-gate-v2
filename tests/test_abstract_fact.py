"""AbstractFact 的验收：读、校验、重置，以及三种"写错了"的报错。"""
import unittest
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from state_machine.abstract_fact import (
    AbstractFact,
    FactError,
    FactFileError,
    Rule,
    RuleMismatch,
)


@dataclass
class DemoFact(AbstractFact):
    """一个最普通的子类：两个必填，一个可选。"""
    title: str = ""
    count: int = 0
    note: str = ""

    RULES = (
        Rule("title"),
        Rule("count"),
        Rule("note", required=False),
    )


@dataclass
class SizedFact(AbstractFact):
    """带条件的规则：非空还不够，要够长。"""
    title: str = ""

    RULES = (
        Rule("title", condition=lambda fact: len(fact.title.strip()) >= 4,
             description="至少 4 个字符"),
    )


@dataclass
class MissingRuleFact(AbstractFact):
    alpha: str = ""
    beta: str = ""

    RULES = (Rule("alpha"),)


@dataclass
class TypoRuleFact(AbstractFact):
    alpha: str = ""
    beta: str = ""

    RULES = (Rule("alpha"), Rule("bata"))


@dataclass
class NoDefaultFact(AbstractFact):
    alpha: str

    RULES = (Rule("alpha"),)


class AbstractFactTests(unittest.TestCase):

    def setUp(self):
        scratch = TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.dir = Path(scratch.name)

    def write(self, text: str, name: str = "facts.txt") -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    # ---------------- 校验 ----------------

    def test_empty_fact_fails_with_fields_in_declaration_order(self):
        ok, problems = DemoFact().validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["title", "count"])

    def test_optional_field_is_skipped(self):
        ok, problems = DemoFact(title="x", count=1, note="").validate()
        self.assertIs(ok, True)
        self.assertEqual(problems, [])

    def test_counter_zero_counts_as_empty(self):
        ok, problems = DemoFact(title="x", count=0).validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["count"])

    def test_condition_beyond_emptiness(self):
        ok, problems = SizedFact(title="abc").validate()
        self.assertIs(ok, False)
        self.assertEqual(problems, ["title"])
        self.assertIs(SizedFact(title="abcd").validate()[0], True)

    def test_explain_falls_back_to_default_wording(self):
        self.assertEqual(DemoFact.explain(["title", "count"]),
                         "title: 必填项为空; count: 必填项为空")

    def test_explain_uses_the_rule_wording(self):
        self.assertEqual(SizedFact.explain(["title"]), "title: 至少 4 个字符")

    # ---------------- 读 ----------------

    def test_update_reads_key_value(self):
        fact = DemoFact()
        fact.update(self.write("title=重构状态机\ncount=3\n"))
        self.assertEqual((fact.title, fact.count), ("重构状态机", 3))

    def test_update_skips_comments_and_blank_lines(self):
        fact = DemoFact()
        fact.update(self.write("# 受理记录\n\ntitle=x\n\n"))
        self.assertEqual(fact.title, "x")

    def test_update_is_incremental(self):
        fact = DemoFact(note="上一轮留下的")
        fact.update(self.write("title=x\n"))
        self.assertEqual((fact.title, fact.note), ("x", "上一轮留下的"))

    def test_update_splits_on_the_first_equals_sign(self):
        fact = DemoFact()
        fact.update(self.write("title=a=b=c\n"))
        self.assertEqual(fact.title, "a=b=c")

    def test_update_ignores_a_missing_file(self):
        fact = DemoFact(title="x")
        fact.update(self.dir / "还没有这个文件.txt")
        self.assertEqual(fact.title, "x")

    def test_update_rejects_an_unknown_key(self):
        fact = DemoFact()
        with self.assertRaises(FactFileError) as failure:
            fact.update(self.write("titl=x\n"))
        self.assertIn("titl", str(failure.exception))

    def test_update_rejects_a_line_without_equals(self):
        fact = DemoFact()
        with self.assertRaises(FactFileError):
            fact.update(self.write("title\n"))

    def test_update_rejects_a_non_numeric_counter(self):
        fact = DemoFact()
        with self.assertRaises(FactFileError):
            fact.update(self.write("count=三\n"))

    # ---------------- 重置 ----------------

    def test_reset_clears_strings_and_counters(self):
        fact = DemoFact(title="x", count=7, note="y")
        fact.reset()
        self.assertEqual((fact.title, fact.count, fact.note), ("", 0, ""))

    # ---------------- 写错了的三种情形 ----------------

    def test_rule_count_mismatch(self):
        with self.assertRaises(RuleMismatch) as failure:
            MissingRuleFact().validate()
        message = str(failure.exception)
        self.assertIn("2 个", message)      # 字段数
        self.assertIn("beta", message)      # 缺哪条规则

    def test_same_rule_count_but_wrong_name(self):
        with self.assertRaises(RuleMismatch) as failure:
            TypoRuleFact().validate()
        message = str(failure.exception)
        self.assertIn("bata", message)
        self.assertIn("beta", message)

    def test_field_without_default(self):
        with self.assertRaises(FactError) as failure:
            NoDefaultFact(alpha="x").reset()
        self.assertIn("alpha", str(failure.exception))


if __name__ == "__main__":
    unittest.main()
