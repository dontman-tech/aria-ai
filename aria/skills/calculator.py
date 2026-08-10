"""Calculator skill - evaluates math expressions safely."""

from __future__ import annotations

import ast
import operator
import re
from typing import Any

from aria.skills.base import Skill, SkillResult

# Word to symbol replacements
WORD_MAP = {
    "plus": "+", "minus": "-", "times": "*", "multiplied by": "*",
    "divided by": "/", "over": "/", "x": "*", "mod": "%", "modulo": "%",
    "power": "**", "to the power of": "**", "squared": "**2", "cubed": "**3",
}

# Safe operators for evaluation
SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class CalculatorSkill(Skill):
    name = "calculator"
    description = "Evaluate mathematical expressions"
    patterns = [
        r"\b(calculate|compute|what(?:'s| is))\b.*\d",
        r"\d\s*[+\-*/x]\s*\d",
        r"\b(sqrt|square root|factorial)\b",
    ]
    keywords = ["calculate", "compute", "times", "divided by", "plus", "minus"]

    def execute(self, text: str) -> SkillResult:
        lower = text.lower()

        # Special functions checked first (before expression extraction)
        if "sqrt" in lower or "square root" in lower:
            return self._sqrt(text)
        if "factorial" in lower:
            return self._factorial(text)

        expr = self._extract_expression(text)
        if not expr:
            return SkillResult(success=False, message="I couldn't find a math expression in that, Boss.")

        try:
            result = self._safe_eval(expr)
            if result is not None:
                # Clean up float display
                if isinstance(result, float) and result.is_integer():
                    result = int(result)
                return SkillResult(success=True, message=f"That's {result:,}, Boss.", data={"expression": expr, "result": result})
        except Exception as e:
            return SkillResult(success=False, message=f"I couldn't compute that: {e}")
        return SkillResult(success=False, message="That expression didn't compute, Boss.")

    def _extract_expression(self, text: str) -> str:
        expr = text.lower()
        # Remove trigger words
        for word in ("calculate", "compute", "what's", "what is", "equals", "="):
            expr = expr.replace(word, "")
        # Replace word operators
        for word, sym in sorted(WORD_MAP.items(), key=lambda x: -len(x[0])):
            expr = expr.replace(word, sym)
        # Extract just the math part
        match = re.search(r"[\d\s+\-*/().%^]+", expr)
        return match.group(0).strip() if match else ""

    def _safe_eval(self, expr: str) -> Any:
        """Safely evaluate a math expression using AST parsing."""
        expr = expr.replace("^", "**")
        node = ast.parse(expr, mode="eval").body
        return self._eval_node(node)

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Invalid constant: {node.value}")
        if isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op = SAFE_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
            return op(left, right)
        if isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op = SAFE_OPS.get(type(node.op))
            if op is None:
                raise ValueError(f"Unsupported unary op: {type(node.op).__name__}")
            return op(operand)
        raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    def _sqrt(self, text: str) -> SkillResult:
        import math

        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if match:
            n = float(match.group(1))
            result = math.sqrt(n)
            if result.is_integer():
                result = int(result)
            return SkillResult(success=True, message=f"The square root of {n} is {result}, Boss.")
        return SkillResult(success=False, message="Which number should I take the square root of, Boss?")

    def _factorial(self, text: str) -> SkillResult:
        import math

        match = re.search(r"(\d+)", text)
        if match:
            n = int(match.group(1))
            if n > 1000:
                return SkillResult(success=False, message="That's too large for factorial, Boss.")
            result = math.factorial(n)
            return SkillResult(success=True, message=f"{n} factorial is {result}, Boss.")
        return SkillResult(success=False, message="Which number's factorial, Boss?")
