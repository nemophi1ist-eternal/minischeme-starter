"""CLI 与健壮性自测：覆盖 spec §2 的运行约定与若干边界情况。

用法：python3 tests/check_cli.py
结果写入 tests/cli_report.txt（UTF-8），便于查看中文错误信息。
"""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable
MAIN = os.path.join(ROOT, "src", "main.py")

report = []


def write_temp(name: str, text: str) -> str:
    path = os.path.join(ROOT, "tests", name)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    return path


def run(args: list, stdin: str = ""):
    """运行解释器，返回 (退出码, 标准输出, 标准错误)。"""
    process = subprocess.run(
        [PY, MAIN] + args,
        input=stdin,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",   # 解释器输出已固定为 UTF-8；替换字符不影响断言
        cwd=ROOT,
    )
    return process.returncode, process.stdout or "", process.stderr or ""


def check(title: str, got, want) -> None:
    ok = got == want
    report.append("%s %s" % ("[PASS]" if ok else "[FAIL]", title))
    if not ok:
        report.append("   期望: %r" % (want,))
        report.append("   实际: %r" % (got,))


def main() -> int:
    a = write_temp("_cli_a.scm", "(define shared 10)\n(+ shared 1)\n")
    b = write_temp("_cli_b.scm", "(* shared 2)\n")

    # §2 多文件共享同一个全局环境
    code, out, err = run([a, b])
    check("多文件共享环境", (code, out, err), (0, "shared\n11\n20\n", ""))

    # §2 没有文件参数时从标准输入读取
    code, out, err = run([], stdin="(+ 1 2)\n(define f (lambda (x) (* x 3)))\n(f 4)\n")
    check("标准输入", (code, out, err), (0, "3\nf\n12\n", ""))

    # §2 每个结果独占一行；display 的 None 不打印
    code, out, err = run([], stdin='(display "x")(newline)(+ 1 1)\n')
    check("display 不额外打印", (code, out, err), (0, "x\n2\n", ""))

    # §8 字符串转义可以读回（round-trip）
    code, out, err = run([], stdin='"a\\nb"\n"q\\"q"\n"back\\\\slash"\n"t\\tt"\n')
    check("字符串转义打印", (code, out, err),
          (0, '"a\\nb"\n"q\\"q"\n"back\\\\slash"\n"t\\tt"\n', ""))

    # 注释与空行可以出现在任意位置
    code, out, err = run([], stdin="; 只有注释\n\n(+ 1 2) ; 行尾注释\n")
    check("注释与空行", (code, out, err), (0, "3\n", ""))

    # 文件不存在：给出可读错误并返回非零
    code, out, err = run([os.path.join(ROOT, "tests", "不存在的文件.scm")])
    check("文件不存在的退出码", (code, out), (1, ""))

    # 语法错误：缺少右括号
    bad = write_temp("_cli_bad.scm", "(+ 1 2\n")
    code, out, err = run([bad])
    check("缺少右括号的处理", (code, out), (1, ""))
    report.append("   错误信息: %s" % err.strip())

    # 未定义变量
    code, out, err = run([], stdin="(foo 1)\n")
    check("未定义变量的处理", (code, out), (1, ""))
    report.append("   错误信息: %s" % err.strip())

    # 调用非过程
    code, out, err = run([], stdin="(1 2)\n")
    check("调用非过程的处理", (code, out), (1, ""))
    report.append("   错误信息: %s" % err.strip())

    # 较深的递归
    code, out, err = run([], stdin=(
        "(define (sum n acc) (if (= n 0) acc (sum (- n 1) (+ acc n))))\n"
        "(sum 300 0)\n"))
    check("深递归 300", (code, out, err), (0, "sum\n45150\n", ""))

    # 点对写法与嵌套列表打印
    code, out, err = run([], stdin="'(1 . (2 . (3 . ())))\n'(1 . 2)\n'((1 2) . 3)\n'(1 . (2 . 3))\n")
    check("点对链打印", (code, out, err),
          (0, "(1 2 3)\n(1 . 2)\n((1 2) . 3)\n(1 2 . 3)\n", ""))

    # eq? / equal? 的同一性与结构比较
    code, out, err = run([], stdin=(
        "(define xs '(1 2))\n"
        "(eq? xs xs)\n"
        "(eq? '(1 2) '(1 2))\n"
        "(equal? '(1 2) (list 1 2))\n"
        "(eq? 'a \"a\")\n"
        "(equal? 'a \"a\")\n"
        "(equal? #t 1)\n"))
    check("eq?/equal? 语义", (code, out, err),
          (0, "xs\n#t\n#f\n#t\n#f\n#f\n#f\n", ""))

    for name in ("_cli_a.scm", "_cli_b.scm", "_cli_bad.scm"):
        path = os.path.join(ROOT, "tests", name)
        if os.path.exists(path):
            os.remove(path)

    with open(os.path.join(ROOT, "tests", "cli_report.txt"), "w",
              encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(report) + "\n")
    failures = sum(1 for line in report if line.startswith("[FAIL]"))
    print("CLI 自测：%d 项失败（详见 tests/cli_report.txt）" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
