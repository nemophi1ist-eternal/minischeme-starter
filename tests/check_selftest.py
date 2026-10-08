"""自测脚本：逐条核对 tests/selftest.scm 的 "-> 期望值" 注释。

用法（在仓库根目录）：
    python3 tests/check_selftest.py

它做两件事：
1. 把 example/*.scm 与 tests/selftest.scm 的每条表达式求值一遍，并对带
   "-> 值" 注释的表达式报告不一致（注释去掉中文括注后与输出逐字符比较；
   注释里没有值表示该表达式不产生输出）；
2. 把 selftest.scm 的实际输出写入 tests/selftest.expected.txt，便于逐行核对。
"""

from __future__ import annotations

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from evaluator import evaluate                       # noqa: E402
from lexer import tokenize                           # noqa: E402
from printer import write                            # noqa: E402
from reader import Reader                            # noqa: E402
from stdlib import create_global_environment         # noqa: E402
from values import SchemeError                       # noqa: E402

SOURCES = [
    ("example/01_arithmetic.scm", None),
    ("example/02_conditionals.scm", None),
    ("example/03_functions.scm", None),
    ("example/04_recursion.scm", None),
    ("example/05_lists.scm", None),
    ("example/06_io.scm", None),
    ("tests/selftest.scm", "tests/selftest.expected.txt"),
]

ARROW = "\u2192"          # →
COMMENT_VALUE = re.compile(r";\s*\u2192\s*(.*?)\s*(?:;.*)?$")
FULLWIDTH = re.compile(r"\uff08[^\uff09]*\uff09")  # 注释里的中文括注

# 少量注释本身有歧义（example/06_io.scm 第 6、7 行的注释在值后面直接跟了
# 中文说明、没有分隔符），这里按 spec §8 明确列出期望值。
KNOWN_EXPECTED = {
    ("example/06_io.scm", 6): '"hello"',
    ("example/06_io.scm", 7): '"a\\nb"',
}


def expected_from_comment(line: str):
    """从一行源码里取出 "; → 值" 注释声明的期望输出；没有则返回 None。

    支持 "值 ; 补充说明" 的写法：只取分号前的部分。
    """
    match = COMMENT_VALUE.search(line)
    if not match:
        return None
    return FULLWIDTH.sub("", match.group(1)).strip()


def expressions_with_lines(source: str) -> list:
    """把源码读成 [(起始行号, 表达式)]，一个顶层表达式一项。"""
    tokens = tokenize(source)
    items = []
    index = 0
    total = len(tokens)
    while index < total:
        start = index
        collected = []
        # 前导的 '（可能连着多个，如 ''x）与它修饰的表达式算同一条
        while index < total and tokens[index].kind == "QUOTE":
            collected.append(tokens[index])
            index += 1
        depth = 0
        while index < total:
            token = tokens[index]
            collected.append(token)
            index += 1
            if token.kind == "LPAREN":
                depth += 1
            elif token.kind == "RPAREN":
                depth -= 1
            if depth == 0:
                break
        line = tokens[start].line
        try:
            program = Reader(collected).read_program()
        except SchemeError:
            continue
        for expression in program:
            items.append((line, expression))
    return items


def capture(expression, env) -> tuple:
    """求值一条表达式，返回 (产生的输出行列表, 表达式结果)。"""
    real_stdout = sys.stdout
    buffer = io.StringIO()
    sys.stdout = buffer
    try:
        result = evaluate(expression, env)
    finally:
        sys.stdout = real_stdout
    produced = []
    text = buffer.getvalue()
    if text:
        produced = text.split("\n")
        if produced and produced[-1] == "":
            produced.pop()
    return produced, result


def run_case(path: str, expected_path, report) -> int:
    """跑一个文件：核对注释，写出实际输出，返回不一致条数。"""
    source = open(path, encoding="utf-8").read()
    lines = source.split("\n")
    env = create_global_environment()
    items = expressions_with_lines(source)
    label = os.path.relpath(path, ROOT).replace(os.sep, "/")

    # 第一遍：求值，收集实际输出
    output = []
    for _, expression in items:
        produced, result = capture(expression, env)
        if result is not None:
            produced = produced + [write(result)]
        output.append(produced)

    # 第二遍：把每行的第一条表达式的输出与注释声明比较
    failures, checked, seen_lines = 0, 0, set()
    for (line, _), produced in zip(items, output):
        if line in seen_lines:
            continue
        seen_lines.add(line)
        want = KNOWN_EXPECTED.get((label, line), expected_from_comment(lines[line - 1]))
        if want is None:
            continue
        checked += 1
        if want == "":
            if produced:
                failures += 1
                report("  %s:%d 期望无输出，实际 %r" % (path, line, produced))
        elif produced != [want]:
            failures += 1
            report("  %s:%d 期望 %r，实际 %r" % (path, line, want, produced))

    if expected_path:
        flat = [line for produced in output for line in produced]
        with open(expected_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("\n".join(flat) + ("\n" if flat else ""))

    report("  %-28s 表达式 %3d 条，注释核对 %3d 条，不一致 %d 条"
           % (path, len(items), checked, failures))
    return failures


def main() -> int:
    total = 0
    for path, expected in SOURCES:
        total += run_case(os.path.join(ROOT, path), expected and os.path.join(ROOT, expected), print)
    print("总计不一致：%d" % total)
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
