"""Template and condition helpers."""

from __future__ import annotations

import ast
import operator
import re
from collections.abc import Mapping
from string import Formatter
from typing import Any

_FIELD_RE = re.compile(r"{([^{}]+)}")


class MissingValueError(KeyError):
    """Raised when a template references an unknown value."""


def get_value(path: str, data: Mapping[str, Any]) -> Any:
    """Read a dotted value from a nested mapping."""
    current: Any = data
    for part in path.split("."):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
            continue
        raise MissingValueError(path)
    return current


class _FormatValues(dict[str, Any]):
    def __init__(self, data: Mapping[str, Any]) -> None:
        super().__init__()
        self._data = data

    def __missing__(self, key: str) -> Any:
        return get_value(key, self._data)


def render(value: Any, context: Mapping[str, Any]) -> Any:
    """Render strings containing ``{name}`` placeholders."""
    if isinstance(value, str):
        # Preserve native types when the entire value is a single placeholder.
        fields = list(Formatter().parse(value))
        if (
            len(fields) == 1
            and fields[0][0] == ""
            and fields[0][1]
            and fields[0][2] == ""
            and fields[0][3] is None
        ):
            return get_value(fields[0][1], context)
        return value.format_map(_FormatValues(context))
    if isinstance(value, list):
        return [render(item, context) for item in value]
    if isinstance(value, dict):
        return {key: render(item, context) for key, item in value.items()}
    return value


def render_condition(expr: str, context: Mapping[str, Any]) -> str:
    """Render placeholders for Python expression evaluation."""
    return _FIELD_RE.sub(lambda m: repr(get_value(m.group(1), context)), expr)


class ConditionEvaluator:
    """Safely evaluate simple boolean expressions."""

    _compare_ops = {
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda left, right: left in right,
        ast.NotIn: lambda left, right: left not in right,
    }

    def evaluate(self, expr: str | None, context: Mapping[str, Any]) -> bool:
        """Return True when an empty or rendered expression is truthy."""
        if not expr:
            return True
        rendered = render_condition(expr, context)
        tree = ast.parse(rendered, mode="eval")
        return bool(self._eval(tree.body))

    def _eval(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.List):
            return [self._eval(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(self._eval(item) for item in node.elts)
        if isinstance(node, ast.BoolOp):
            values = [bool(self._eval(value)) for value in node.values]
            return all(values) if isinstance(node.op, ast.And) else any(values)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not bool(self._eval(node.operand))
        if isinstance(node, ast.Compare):
            left = self._eval(node.left)
            for op_node, comparator in zip(node.ops, node.comparators, strict=True):
                right = self._eval(comparator)
                op = self._compare_ops.get(type(op_node))
                if op is None or not op(left, right):
                    return False
                left = right
            return True
        raise ValueError(f"Unsupported condition expression: {ast.dump(node)}")
