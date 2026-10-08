"""模块结构自测：确认 src/ 里的模块名不会破坏 Python 标准库。

背景：评分器以 `python3 src/main.py` 运行，Python 会把 src/ 放进模块搜索
路径。如果解释器自己的模块叫 builtins.py / parser.py，就会遮蔽标准库同名
模块。本脚本确认：

    src/stdlib.py    是内置过程库，可正常创建初始环境；
    src/reader.py    是语法分析器；
    src/builtins.py  旧名字的兼容层，转发到 stdlib；
    src/parser.py    旧名字的兼容层，转发到 reader；
    而且真正的标准库 builtins 模块没有被遮蔽（始终是标准库那一份）。

用法：python3 tests/check_modules.py
"""

from __future__ import annotations

import builtins as real_builtins
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
sys.path.insert(0, SRC)

import reader                             # noqa: E402
import stdlib                             # noqa: E402
from evaluator import evaluate            # noqa: E402
from printer import write                 # noqa: E402

checks = []


def check(title: str, ok: bool, detail: str = "") -> None:
    checks.append((title, ok, detail))


def load_by_path(name: str):
    """按文件路径加载 src/<name>.py（模拟"旧名字被 import"时的实际行为）。"""
    path = os.path.join(SRC, name + ".py")
    spec = importlib.util.spec_from_file_location("_probe_" + name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check("标准库 builtins 未被遮蔽", real_builtins is sys.modules["builtins"],
      "sys.modules['builtins'] 必须是标准库模块")
check("标准库 builtins 功能完好",
      hasattr(real_builtins, "len") and hasattr(real_builtins, "print"))

env = stdlib.create_global_environment()
check("stdlib 提供初始环境", len(env.bindings) >= 35,
      "内置过程数量 = %d" % len(env.bindings))
names = {getattr(name, "name", name) for name in stdlib.primitives()}
check("stdlib 含 car/display/newline", {"car", "display", "newline"} <= names)

shim_builtins = load_by_path("builtins")
shim_env = shim_builtins.create_global_environment()
check("builtins 兼容层转发到 stdlib", len(shim_env.bindings) == len(env.bindings))

check("parser 兼容层转发到 reader", load_by_path("parser").read is reader.read)
expressions = load_by_path("parser").parse("(+ 1 2)")
check("兼容层 parse 能求值", write(evaluate(expressions[0], env)) == "3")

failures = 0
for title, ok, detail in checks:
    print("%s %s%s" % ("[PASS]" if ok else "[FAIL]", title,
                       ("  (%s)" % detail) if detail and not ok else ""))
    failures += 0 if ok else 1

print("模块结构自测：%d 项失败" % failures)
sys.exit(1 if failures else 0)
