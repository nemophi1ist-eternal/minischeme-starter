"""mini-Scheme 的数据类型定义。

本模块只负责"值"长什么样，不涉及求值规则，供词法、语法、求值、
打印、内置库五个模块共用：

    int / float  -- 整数与浮点
    bool         -- #t / #f
    str          -- 字符串（当作基本值，不是字符数组）
    Symbol       -- 符号，与字符串是两种不同的类型
    Pair         -- 点对，列表由点对链构成
    NIL          -- 空表 ()，全局单例
    Primitive / UserFunction -- 过程（定义在 evaluator 中，这里只做判定）
"""

from __future__ import annotations

import math


class SchemeError(Exception):
    """解释器在词法/语法/求值阶段遇到的错误。"""


# --------------------------------------------------------------------------
# 符号
# --------------------------------------------------------------------------

class Symbol:
    """符号（名字）。

    刻意不用 str 的子类：那样 `Symbol('a') == 'a'` 会成立，
    违反 spec §11 中"(equal? 'a "a") 必须为 #f" 的要求。
    符号按名字 intern，因此相同的名字是同一个对象，eq? 成立。
    """

    __slots__ = ("name",)

    _pool: dict[str, "Symbol"] = {}

    def __new__(cls, name: str) -> "Symbol":
        cached = cls._pool.get(name)
        if cached is None:
            cached = super().__new__(cls)
            cached.name = name
            cls._pool[name] = cached
        return cached

    def __repr__(self) -> str:
        return "Symbol(%r)" % (self.name,)


def intern(name: str) -> Symbol:
    """取得名字对应的符号（相同名字返回同一个对象）。"""
    return Symbol(name)


def is_symbol(value) -> bool:
    return isinstance(value, Symbol)


# --------------------------------------------------------------------------
# 空表
# --------------------------------------------------------------------------

class _Nil:
    """空表 () 的唯一实例。

    不直接用 Python 的 None 表示空表：spec §2 规定"求值结果为 None
    时不打印"，而 `'()` 是需要打印成一行的值，两者必须区分开。
    """

    __slots__ = ()
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "()"


NIL = _Nil()


def is_nil(value) -> bool:
    return value is NIL


def is_empty_list(value) -> bool:
    """() 与 None 都表示"没有内容"的列表尾巴。"""
    return value is NIL or value is None


# --------------------------------------------------------------------------
# 点对与列表
# --------------------------------------------------------------------------

class Pair:
    """点对 (car . cdr)。列表 (1 2 3) 是 (1 . (2 . (3 . ()))) 。"""

    __slots__ = ("car", "cdr")

    def __init__(self, car, cdr):
        self.car = car
        self.cdr = cdr

    def __repr__(self) -> str:
        return "Pair(%r, %r)" % (self.car, self.cdr)


def cons(car, cdr) -> Pair:
    return Pair(car, cdr)


def make_list(items) -> object:
    """把 Python 序列折成点对链，空序列得到 NIL。"""
    result = NIL
    for item in reversed(list(items)):
        result = Pair(item, result)
    return result


def pair_to_list(value, context: str = "列表") -> list:
    """把"真列表"展开成 Python list；遇点对尾巴则报错。"""
    items = []
    node = value
    while isinstance(node, Pair):
        items.append(node.car)
        node = node.cdr
    if not is_empty_list(node):
        raise SchemeError("%s 不是真列表：%s" % (context, to_source(node)))
    return items


def is_proper_list(value) -> bool:
    """是否真列表（以 () 结尾）。带环的结构用快慢指针兜底。"""
    slow = value
    fast = value
    while True:
        if is_empty_list(fast):
            return True
        if not isinstance(fast, Pair):
            return False
        fast = fast.cdr
        if is_empty_list(fast):
            return True
        if not isinstance(fast, Pair):
            return False
        fast = fast.cdr
        slow = slow.cdr
        if fast is slow:
            return False


def is_pair(value) -> bool:
    return isinstance(value, Pair)


# --------------------------------------------------------------------------
# 数值
# --------------------------------------------------------------------------

def is_number(value) -> bool:
    """bool 在 Python 里是 int 的子类，必须排除，否则 (number? #t) 会为真。"""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_integer(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def format_float(value: float) -> str:
    """浮点打印：取最短且能还原的写法。"""
    if math.isnan(value):
        return "+nan.0"
    if math.isinf(value):
        return "+inf.0" if value > 0 else "-inf.0"
    text = repr(float(value))
    if text.endswith(".0"):
        text = text[:-2]
    return text


# --------------------------------------------------------------------------
# 前后引用（仅用于错误信息，避免与 printer 循环依赖）
# --------------------------------------------------------------------------

def to_source(value) -> str:
    """把一个值渲染成可读文本（含引号的字符串写法）。"""
    import printer  # 延迟导入：printer 依赖本模块的类型判定
    return printer.write(value)
