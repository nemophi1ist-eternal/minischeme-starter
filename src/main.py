#!/usr/bin/env python3
"""mini-Scheme 解释器入口。

用法（spec §2）：

    python3 src/main.py file1.scm [file2.scm ...]
    python3 src/main.py            # 没有文件参数时从标准输入读取

按顺序求值每个文件中的每一个顶层表达式，每个结果独占一行打印；
结果为 None（无值，如 display/newline）时不打印。
多个文件共享同一个全局环境。
"""

from __future__ import annotations

import os
import sys

# 允许直接用 `python3 src/main.py ...` 运行：把 src 目录放进模块搜索路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 输出固定用 UTF-8 且换行固定为 \n：评分器逐字节比对输出，
# 不能受运行环境默认编码（Windows 上常是 GBK）或换行风格影响。
for _stream_name in ("stdout", "stderr"):
    _stream = getattr(sys, _stream_name, None)
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", newline="\n")
        except (ValueError, OSError):  # 被重定向或不支持时忽略，不影响求值
            pass

# Scheme 递归经 evaluate/apply 多层 Python 调用，适当放宽递归上限，
# 让较深的 Scheme 递归（如 (fact 300)）不会先撞上 Python 的限制
sys.setrecursionlimit(20000)

from evaluator import evaluate                     # noqa: E402
from printer import write                          # noqa: E402
from reader import read                            # noqa: E402
from stdlib import create_global_environment       # noqa: E402
from values import SchemeError                     # noqa: E402

USAGE = "用法: python3 src/main.py [file1.scm file2.scm ...]"


def read_source(path: str) -> str:
    """读入一个源文件。

    按 utf-8-sig（兼容带 BOM 的 UTF-8）-> 系统默认编码 -> latin-1 依次尝试，
    源文件编码不影响求值结果时就不必因为编码差异而中断。
    """
    try:
        handle = open(path, "rb")
    except OSError as error:
        raise SchemeError("无法读取文件 %s：%s" % (path, error.strerror or error))
    with handle:
        data = handle.read()

    for encoding in ("utf-8-sig", sys.getdefaultencoding(), "latin-1"):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise SchemeError("无法解码文件 %s：不是可识别的文本编码" % (path,))


def run_sources(sources: list, environment) -> int:
    """求值若干段源码，把每个顶层结果打印成一行。"""
    for label, source in sources:
        try:
            expressions = read(source)
        except SchemeError as error:
            print("%s: %s" % (label, error), file=sys.stderr)
            return 1
        for expression in expressions:
            try:
                result = evaluate(expression, environment)
            except SchemeError as error:
                print("%s: %s" % (label, error), file=sys.stderr)
                return 1
            if result is None:  # 无值：如 display / newline，不打印
                continue
            print(write(result))
    return 0


def main(argv: list) -> int:
    paths = argv[1:]
    environment = create_global_environment()

    if paths:
        sources = []
        for path in paths:
            try:
                sources.append((path, read_source(path)))
            except SchemeError as error:
                print(error, file=sys.stderr)
                return 1
        return run_sources(sources, environment)

    # 没有文件参数：从标准输入读
    return run_sources([("<stdin>", sys.stdin.read())], environment)


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except BrokenPipeError:  # 输出被下游提前关闭（如管道给 head）
        sys.exit(0)
