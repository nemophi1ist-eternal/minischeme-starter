"""内置过程库（spec §5）：实现全部标准函数，并放进初始环境。

每个内置过程都自己检查参数个数与类型，出错时给出可读的提示；
参数在进入这里之前已经被求值器全部求值完毕。

模块名用 stdlib 而不是 builtins：`src/` 会被放进模块搜索路径，
若取名 builtins.py 会遮蔽 Python 标准库的 builtins 模块，
导致 import 其他标准库时出错。
"""

from __future__ import annotations

import sys

from environment import Environment
from evaluator import is_procedure, Primitive
from printer import display as render_display
from printer import write as render_write
from values import (NIL, Pair, SchemeError, intern, is_empty_list, is_nil,
                    is_number, is_proper_list, is_symbol, make_list,
                    pair_to_list)

_PRIMITIVES: dict = {}


def _register(name: str):
    """把 Python 函数登记成名字为 name 的内置过程。"""
    def decorator(function):
        _PRIMITIVES[intern(name)] = Primitive(name, function)
        return function
    return decorator


def _wrong_type(name: str, value) -> SchemeError:
    return SchemeError("%s 的参数类型不对：%s" % (name, render_write(value)))


def _numbers(name: str, args: list) -> list:
    """全部参数都必须是数（bool 不算数）。"""
    for value in args:
        if not is_number(value):
            raise _wrong_type(name, value)
    return args


def _number(name: str, value):
    if not is_number(value):
        raise _wrong_type(name, value)
    return value


def _integers(name: str, args: list) -> list:
    """全部参数都必须是整数。"""
    for value in args:
        if isinstance(value, bool) or not isinstance(value, int):
            raise SchemeError("%s 只接受整数：%s" % (name, render_write(value)))
    return args


def _arity(name: str, args: list, low: int, high=None) -> None:
    count = len(args)
    if count < low or (high is not None and count > high):
        if high is None:
            expected = "至少 %d 个" % low
        elif low == high:
            expected = "%d 个" % low
        else:
            expected = "%d 到 %d 个" % (low, high)
        raise SchemeError(
            "%s 的参数个数不对：期望 %s，实际给了 %d 个" % (name, expected, count))


def _truncating_div(a: int, b: int) -> int:
    """整数除法：商向零截断（Python 的 // 是向下取整，不能直接用）。"""
    if b == 0:
        raise SchemeError("除数为 0")
    quotient = abs(a) // abs(b)
    return -quotient if (a < 0) != (b < 0) else quotient


# --------------------------------------------------------------------------
# 算术
# --------------------------------------------------------------------------

@_register("+")
def _add(args):
    _numbers("+", args)
    return sum(args)


@_register("-")
def _sub(args):
    _arity("-", args, 1)
    _numbers("-", args)
    if len(args) == 1:
        return -args[0]
    result = args[0]
    for value in args[1:]:
        result -= value
    return result


@_register("*")
def _mul(args):
    _numbers("*", args)
    result = 1
    for value in args:
        result *= value
    return result


@_register("/")
def _div(args):
    _arity("/", args, 1)
    _numbers("/", args)
    if len(args) == 1:  # 单参数求倒数，结果是浮点
        if args[0] == 0:
            raise SchemeError("除数为 0")
        return 1 / args[0]
    result = args[0]
    for value in args[1:]:
        if isinstance(result, int) and isinstance(value, int):
            result = _truncating_div(result, value)  # 整数相除得整数商
        else:
            if value == 0:
                raise SchemeError("除数为 0")
            result = result / value
    return result


@_register("modulo")
def _modulo(args):
    _arity("modulo", args, 2, 2)
    _integers("modulo", args)
    a, b = args
    if b == 0:
        raise SchemeError("modulo 的除数为 0")
    if b < 0:  # 与 Scheme 一致：结果符号跟随除数
        a, b = -a, -b
    return a % b


@_register("quotient")
def _quotient(args):
    _arity("quotient", args, 2, 2)
    _integers("quotient", args)
    return _truncating_div(args[0], args[1])


@_register("expt")
def _expt(args):
    _arity("expt", args, 2, 2)
    _numbers("expt", args)
    base, exponent = args
    if isinstance(base, int) and isinstance(exponent, int) and exponent >= 0:
        return base ** exponent  # 整数结果保持整数，如 (expt 2 10) -> 1024
    return float(base) ** float(exponent)


@_register("abs")
def _abs(args):
    _arity("abs", args, 1, 1)
    return abs(_number("abs", args[0]))


# --------------------------------------------------------------------------
# 比较
# --------------------------------------------------------------------------

def _comparable(value) -> bool:
    return is_number(value) or isinstance(value, str) or is_symbol(value)


def _chain(name: str, args: list, compare) -> bool:
    """链式比较：相邻两两都成立才为真；只有一个参数时自然为真。"""
    for value in args:
        if not _comparable(value):
            raise _wrong_type(name, value)
    for left, right in zip(args, args[1:]):
        try:
            ok = compare(left, right)
        except TypeError:
            # 类型不能比较（如数字与符号）时视为不成立，而不是让整个程序崩掉
            return False
        if not ok:
            return False
    return True


@_register("=")
def _num_eq(args):
    """相等比较：数字、符号（乃至字符串）按值比较，链式成立才为真。

    spec §5 说明比较支持"数字与符号"，因此 (= 'a 'a) 为真；
    类型不同的两个值按 Python 规则得到 #f（如 (= 1 "")）。
    """
    _arity("=", args, 1)
    for value in args:
        if not _comparable(value):
            raise _wrong_type("=", value)
    return _chain("=", args, lambda a, b: a == b)


@_register("<")
def _less(args):
    _arity("<", args, 1)
    return _chain("<", args, lambda a, b: a < b)


@_register(">")
def _greater(args):
    _arity(">", args, 1)
    return _chain(">", args, lambda a, b: a > b)


@_register("<=")
def _less_equal(args):
    _arity("<=", args, 1)
    return _chain("<=", args, lambda a, b: a <= b)


@_register(">=")
def _greater_equal(args):
    _arity(">=", args, 1)
    return _chain(">=", args, lambda a, b: a >= b)


@_register("not")
def _not(args):
    _arity("not", args, 1, 1)
    return args[0] is False


# --------------------------------------------------------------------------
# 列表
# --------------------------------------------------------------------------

@_register("cons")
def _cons(args):
    _arity("cons", args, 2, 2)
    return Pair(args[0], args[1])


@_register("car")
def _car(args):
    _arity("car", args, 1, 1)
    pair = args[0]
    if not isinstance(pair, Pair):
        raise SchemeError("car 需要一个点对，得到 %s" % render_write(pair))
    return pair.car


@_register("cdr")
def _cdr(args):
    _arity("cdr", args, 1, 1)
    pair = args[0]
    if not isinstance(pair, Pair):
        raise SchemeError("cdr 需要一个点对，得到 %s" % render_write(pair))
    return pair.cdr


@_register("list")
def _list(args):
    return make_list(args)


@_register("length")
def _length(args):
    _arity("length", args, 1, 1)
    return len(pair_to_list(args[0], "length"))


@_register("append")
def _append(args):
    """最后一个参数当作结果的尾巴，前面的都拼接到前面。"""
    if not args:
        return NIL
    result = args[-1]
    for value in reversed(args[:-1]):
        result = _copy_onto(value, result)
    return result


def _copy_onto(source, tail):
    """把真列表 source 的元素复制一份接到 tail 前面（不改动原数据）。"""
    items = pair_to_list(source, "append")
    for item in reversed(items):
        tail = Pair(item, tail)
    return tail


@_register("null?")
def _null_p(args):
    _arity("null?", args, 1, 1)
    return is_empty_list(args[0])


@_register("pair?")
def _pair_p(args):
    _arity("pair?", args, 1, 1)
    return isinstance(args[0], Pair)


@_register("list?")
def _list_p(args):
    _arity("list?", args, 1, 1)
    return is_nil(args[0]) or is_proper_list(args[0])


# --------------------------------------------------------------------------
# 谓词
# --------------------------------------------------------------------------

@_register("number?")
def _number_p(args):
    _arity("number?", args, 1, 1)
    return is_number(args[0])


@_register("boolean?")
def _boolean_p(args):
    _arity("boolean?", args, 1, 1)
    return args[0] is True or args[0] is False


@_register("symbol?")
def _symbol_p(args):
    _arity("symbol?", args, 1, 1)
    return is_symbol(args[0])


@_register("string?")
def _string_p(args):
    _arity("string?", args, 1, 1)
    return isinstance(args[0], str)


@_register("procedure?")
def _procedure_p(args):
    _arity("procedure?", args, 1, 1)
    return is_procedure(args[0])


def _integer_value(name: str, value) -> int:
    """数值谓词要求整数；浮点但正好是整数也接受。"""
    value = _number(name, value)
    if isinstance(value, float):
        if not value.is_integer():
            raise SchemeError("%s 只接受整数：%s" % (name, render_write(value)))
        return int(value)
    return value


@_register("zero?")
def _zero_p(args):
    _arity("zero?", args, 1, 1)
    return _number("zero?", args[0]) == 0


@_register("even?")
def _even_p(args):
    _arity("even?", args, 1, 1)
    return _integer_value("even?", args[0]) % 2 == 0


@_register("odd?")
def _odd_p(args):
    _arity("odd?", args, 1, 1)
    return _integer_value("odd?", args[0]) % 2 != 0


@_register("eq?")
def _eq_p(args):
    """符号、数字、布尔按值比较；复合数据（点对）按同一性比较。"""
    _arity("eq?", args, 2, 2)
    return _eq_value(args[0], args[1])


def _eq_value(left, right) -> bool:
    if left is right:  # 同一对象：符号、NIL、True/False 都在此命中
        return True
    if isinstance(left, Pair) or isinstance(right, Pair):
        return False  # 不同对象即不 eq?
    if is_number(left) != is_number(right):
        return False  # 排除 (eq? #t 1) 这种跨类型比较
    if is_number(left) and is_number(right):
        return left == right
    return False


@_register("equal?")
def _equal_p(args):
    """结构相等：逐层比较，先比类型再比值。"""
    _arity("equal?", args, 2, 2)
    return _equal_value(args[0], args[1])


def _equal_value(left, right) -> bool:
    if left is right:
        return True
    if is_number(left) and is_number(right):
        return left == right
    # 符号与字符串必须区分：(equal? 'a "a") -> #f
    if is_symbol(left) or is_symbol(right):
        return False
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, Pair) and isinstance(right, Pair):
        return (_equal_value(left.car, right.car)
                and _equal_value(left.cdr, right.cdr))
    return is_empty_list(left) and is_empty_list(right)


# --------------------------------------------------------------------------
# 输出
# --------------------------------------------------------------------------

@_register("display")
def _display(args):
    """打印一个值，字符串不带引号、不换行；结果是 None（不打印）。"""
    _arity("display", args, 1, 1)
    sys.stdout.write(render_display(args[0]))
    sys.stdout.flush()
    return None


@_register("newline")
def _newline(args):
    """输出一个换行；结果是 None（不打印）。"""
    _arity("newline", args, 0, 0)
    sys.stdout.write("\n")
    sys.stdout.flush()
    return None


# --------------------------------------------------------------------------
# 初始环境
# --------------------------------------------------------------------------

def create_global_environment() -> Environment:
    """全新的全局环境（每个测试用例独立进程，初始环境为空）。"""
    env = Environment(name="global")
    for name, procedure in _PRIMITIVES.items():
        env.define(name, procedure)
    return env


def primitives() -> dict:
    """名字 -> 内置过程，便于查看与自测。"""
    return dict(_PRIMITIVES)
