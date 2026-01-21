import math
import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class MathResult:
    ok: bool
    value: float | None = None
    error: str | None = None


class MathEvaluator:
    def __init__(self, max_length: int = 200, max_depth: int = 6) -> None:
        self.max_length = max_length
        self.max_depth = max_depth

    def extract_expression(self, text: str) -> str:
        if not text:
            return ""
        cleaned = text.lower()
        cleaned = cleaned.replace("\u0451", "\u0435")
        replacements = [
            (r"\b\u0443\u043c\u043d\u043e\u0436\u0438\u0442\u044c \u043d\u0430\b", "*"),
            (r"\b\u0443\u043c\u043d\u043e\u0436\u0438\u0442\u044c\b", "*"),
            (r"\b\u0440\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u044c \u043d\u0430\b", "/"),
            (r"\b\u043f\u043e\u0434\u0435\u043b\u0438\u0442\u044c \u043d\u0430\b", "/"),
            (r"\b\u0434\u0435\u043b\u0438\u0442\u044c \u043d\u0430\b", "/"),
            (r"\b\u043f\u043b\u044e\u0441\b", "+"),
            (r"\b\u043c\u0438\u043d\u0443\u0441\b", "-"),
        ]
        for pattern, replacement in replacements:
            cleaned = re.sub(pattern, replacement, cleaned)
        cleaned = cleaned.replace("x", "*")
        cleaned = cleaned.replace("\u0445", "*")
        cleaned = re.sub(r"[^0-9\+\-\*/\(\)\.,]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def evaluate(self, text: str) -> MathResult:
        expr = self.extract_expression(text)
        if not expr:
            return MathResult(False, error="empty")
        if len(expr) > self.max_length:
            return MathResult(False, error="too_long")
        try:
            tokens = self._tokenize(expr)
            if not tokens:
                return MathResult(False, error="no_tokens")
            if self._max_parentheses_depth(tokens) > self.max_depth:
                return MathResult(False, error="too_deep")
            rpn = self._to_rpn(tokens)
            value = self._eval_rpn(rpn)
            return MathResult(True, value=value)
        except ZeroDivisionError:
            return MathResult(False, error="divide_by_zero")
        except Exception:
            return MathResult(False, error="invalid")

    def format_value(self, value: float) -> str:
        if value is None or math.isnan(value) or math.isinf(value):
            return ""
        if abs(value - round(value)) < 1e-9:
            return str(int(round(value)))
        return f"{value:.6f}".rstrip("0").rstrip(".")

    def _tokenize(self, expr: str) -> List[str]:
        expr = expr.replace(",", ".")
        tokens: List[str] = []
        number = ""
        prev = None
        for char in expr:
            if char.isdigit() or char == ".":
                number += char
                prev = char
                continue
            if number:
                tokens.append(number)
                number = ""
            if char in "+-*/()":
                tokens.append(char)
                prev = char
            elif char.isspace():
                continue
            else:
                raise ValueError("invalid")
        if number:
            tokens.append(number)
        return self._apply_unary(tokens)

    def _apply_unary(self, tokens: List[str]) -> List[str]:
        result: List[str] = []
        prev = None
        for token in tokens:
            if token == "-" and (prev is None or prev in "+-*/("):
                result.append("0")
                result.append("-")
            else:
                result.append(token)
            prev = token
        return result

    def _to_rpn(self, tokens: List[str]) -> List[str]:
        output: List[str] = []
        stack: List[str] = []
        precedence = {"+": 1, "-": 1, "*": 2, "/": 2}
        for token in tokens:
            if re.match(r"^\d+(?:\.\d+)?$", token):
                output.append(token)
            elif token in "+-*/":
                while stack and stack[-1] in precedence and precedence[stack[-1]] >= precedence[token]:
                    output.append(stack.pop())
                stack.append(token)
            elif token == "(":
                stack.append(token)
            elif token == ")":
                while stack and stack[-1] != "(":
                    output.append(stack.pop())
                if not stack:
                    raise ValueError("mismatch")
                stack.pop()
            else:
                raise ValueError("invalid")
        while stack:
            op = stack.pop()
            if op in "()":
                raise ValueError("mismatch")
            output.append(op)
        return output

    def _eval_rpn(self, tokens: List[str]) -> float:
        stack: List[float] = []
        for token in tokens:
            if token in "+-*/":
                if len(stack) < 2:
                    raise ValueError("invalid")
                b = stack.pop()
                a = stack.pop()
                if token == "+":
                    stack.append(a + b)
                elif token == "-":
                    stack.append(a - b)
                elif token == "*":
                    stack.append(a * b)
                elif token == "/":
                    if b == 0:
                        raise ZeroDivisionError("zero")
                    stack.append(a / b)
            else:
                stack.append(float(token))
        if len(stack) != 1:
            raise ValueError("invalid")
        return stack[0]

    def _max_parentheses_depth(self, tokens: List[str]) -> int:
        depth = 0
        max_depth = 0
        for token in tokens:
            if token == "(":
                depth += 1
                max_depth = max(max_depth, depth)
            elif token == ")":
                depth -= 1
                if depth < 0:
                    raise ValueError("mismatch")
        if depth != 0:
            raise ValueError("mismatch")
        return max_depth
