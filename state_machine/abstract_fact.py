"""
    Abstract Fact
    事实基类
    支持从文本文件更新、按规则数组校验、重置。

    子类应当
    1. 只声明字段和规则数组
    2. 每个字段都必须有普通默认值。默认值是重置值，也是读入时转换类型依据
    3. 规则数组必须逐个覆盖字段
    4. 事实文件是 key=value 文本。只能增量写。
"""
from dataclasses import MISSING, dataclass, fields
from pathlib import Path
from typing import Any, Callable, ClassVar


class FactError(Exception):
    """事实类错误"""


class RuleMismatch(FactError):
    """规则数组与字段对不上。"""


class FactFileError(FactError):
    """事实文件形状不对：不是 key=value、键不认识、值转不过去。"""


@dataclass(frozen=True)
class Rule:
    """
    一条字段规则
    """
    name: str                                           #   字段名
    required: bool = True                               #   是否必填；False 时跳过
    condition: Callable[[Any], bool] | None = None      #   附加条件，收到整个事实实例（所以可以跨字段判断）；None 表示只要"非空"
    description: str = ""                               #   不符合条件时的描述


def _is_empty(value: object) -> bool:
    """
    必填项的空判定。
    字符串去掉空白后判空；计数器小于等于 0 算空
    """
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value <= 0
    return value is None


def _defaults(cls: type) -> dict[str, Any]:
    """
    字段默认值。
    没有默认值的字段报错
    """
    result: dict[str, Any] = {}
    for item in fields(cls):
        if item.default is MISSING:
            raise FactError(
                f"{cls.__name__}.{item.name} 缺失默认值"
            )
        result[item.name] = item.default
    return result


@dataclass
class AbstractFact:
    """
    事实基类
    """
    RULES: ClassVar[tuple[Rule, ...]] = ()

    # ---------------- 读 ----------------

    def update(self, path: str | Path) -> None:
        """
        从 key=value 文本增量读入：只覆盖文件里出现的键。

        文件不存在静默跳过更新
        文件里出现不认识的键或不成形状的行则报错
        """
        source = Path(path)
        if not source.exists():
            return

        known = {rule.name for rule in self._checked_rules()}
        lines = source.read_text(encoding="utf-8").splitlines()
        for number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator:
                raise FactFileError(f"{source}:{number}: 不是 key=value 形状: {line!r}")
            key = key.strip()
            if key not in known:
                raise FactFileError(f"{source}:{number}: 不认识的键 {key!r}")
            setattr(self, key, self._coerce(key, value.strip()))

    def _coerce(self, key: str, value: str) -> Any:
        """按字段默认值的类型转换文本。"""
        default = _defaults(type(self))[key]
        if isinstance(default, bool):
            return value.strip().lower() in ("true", "yes", "1", "y")
        if isinstance(default, int):
            try:
                return int(value)
            except ValueError:
                raise FactFileError(f"字段 {key} 需要整数, 读到 {value!r}") from None
        if default is None:
            raise FactError(
                "%s.%s 的默认值是 None，无法推断类型；给它一个同类型的默认值。"
                % (type(self).__name__, key)
            )
        return value

    # ---------------- 校验 ----------------

    def validate(self) -> tuple[bool, list[str]]:
        """
        按规则数组校验，返回 (是否通过, 未通过的字段名)。
        字段名按声明顺序排列
        """
        rules = {rule.name: rule for rule in self._checked_rules()}
        problems = [name for name in self._field_names()
                    if not _satisfied(self, rules[name])]
        return (not problems), problems

    @classmethod
    def explain(cls, names: list[str]) -> str:
        """把 validate() 给出的字段名变成给人看的一句话。"""
        description = {rule.name: rule.description for rule in cls._checked_rules()}
        return "; ".join(f"{name}: {description[name] or '必填项为空'}" for name in names)

    # ---------------- 重置 ----------------

    def reset(self) -> None:
        """恢复Fact默认值"""
        for name, default in _defaults(type(self)).items():
            setattr(self, name, default)

    # ---------------- 内部 ----------------

    @classmethod
    def _field_names(cls) -> list[str]:
        return [item.name for item in fields(cls)]

    @classmethod
    def _checked_rules(cls) -> tuple[Rule, ...]:
        """规则数组必须逐个覆盖字段，对不上就是程序写错了。"""
        names = cls._field_names()
        rule_names = [rule.name for rule in cls.RULES]
        extra = sorted(set(rule_names) - set(names))
        absent = sorted(set(names) - set(rule_names))
        if len(rule_names) != len(names) or extra or absent:
            raise RuleMismatch(
                "%s: 规则 %d 条, 字段 %d 个; 规则里多余 %s; 规则里缺少 %s"
                % (cls.__name__, len(rule_names), len(names),
                   extra or "无", absent or "无")
            )
        return cls.RULES


def _satisfied(fact: AbstractFact, rule: Rule) -> bool:
    if not rule.required:
        return True
    if rule.condition is not None:
        return rule.condition(fact)
    return not _is_empty(getattr(fact, rule.name))
