"""求值器：表达式 -> 值（解释器的心脏）。

evaluate 与 apply 互相调用：

    evaluate(expr, env)  符号查环境；基本值原样返回；组合式先看是不是
                         特殊形式，否则先求值操作符与全部实参再交给 apply。
    apply(proc, args)    内置过程直接调用；用户函数新建一层环境绑定实参
                         （外层指向函数定义时的环境），再回到 evaluate 求值函数体。
"""

from __future__ import annotations

from environment import Environment
from printer import write
from values import (NIL, Pair, SchemeError, Symbol, is_empty_list, is_symbol,
                    pair_to_list)

# --------------------------------------------------------------------------
# 过程
# --------------------------------------------------------------------------


class Primitive:
    """内置过程：名字 + Python 函数。"""

    __slots__ = ("name", "function")
    is_procedure = True

    def __init__(self, name: str, function):
        self.name = name
        self.function = function

    def __call__(self, args: list):
        return self.function(args)

    def __repr__(self) -> str:
        return "#<procedure %s>" % self.name


class UserFunction:
    """用户函数（闭包）：参数表 + 函数体 + 定义时的环境。"""

    __slots__ = ("params", "body", "env")
    is_procedure = True

    def __init__(self, params: list, body: list, env: Environment):
        self.params = params
        self.body = body
        self.env = env  # 闭包记住定义处环境，词法作用域的关键

    def __repr__(self) -> str:
        return "#<procedure (%s)>" % " ".join(p.name for p in self.params)


def is_procedure(value) -> bool:
    return getattr(value, "is_procedure", False)


def is_truthy(value) -> bool:
    """只有 #f 是假：0、()、""、None 都算真（None 只可能来自缺省分支）。"""
    return value is not False


# --------------------------------------------------------------------------
# 求值
# --------------------------------------------------------------------------

def evaluate(expr, env: Environment):
    """求值一个表达式。"""
    # 1. 基本值（数字/布尔/字符串/空表）：原样返回
    if expr is None or expr is NIL or expr is True or expr is False:
        return expr
    if isinstance(expr, (int, float, str)):
        return expr

    # 2. 符号：去环境里查
    if is_symbol(expr):
        return env.lookup(expr)

    # 3. 组合式
    if isinstance(expr, Pair):
        operator = expr.car
        if is_symbol(operator) and operator in SPECIAL_FORMS:
            return SPECIAL_FORMS[operator](expr.cdr, env)
        procedure = evaluate(operator, env)
        arguments = [evaluate(arg, env) for arg in pair_to_list(expr.cdr, "参数表")]
        return apply(procedure, arguments)

    raise SchemeError("无法求值的表达式：%s" % (write(expr),))


def apply(procedure, args: list):
    """调用一个过程。"""
    if isinstance(procedure, Primitive):
        return procedure(args)
    if isinstance(procedure, UserFunction):
        return _apply_user_function(procedure, args)
    raise SchemeError("%s 不是过程，无法调用" % (write(procedure),))


def _apply_user_function(function: UserFunction, args: list):
    if len(args) != len(function.params):
        raise SchemeError(
            "参数个数不符：期望 %d 个，实际给了 %d 个"
            % (len(function.params), len(args)))
    frame = function.env.extend("call")
    for name, value in zip(function.params, args):
        frame.define(name, value)
    return evaluate_body(function.body, frame)


def evaluate_body(body: list, env: Environment):
    """按 begin 语义依次求值一串表达式，返回最后一个的结果；空体返回 None。"""
    result = None
    for expression in body:
        result = evaluate(expression, env)
    return result


# --------------------------------------------------------------------------
# 特殊形式
# --------------------------------------------------------------------------

def _form_arguments(rest, name: str) -> list:
    """特殊形式的参数表（特殊形式只做个数检查，不做求值）。"""
    return pair_to_list(rest, "%s 的参数" % name)


def _require_count(args: list, low: int, high, name: str) -> None:
    """检查参数个数：high 为 None 表示不限上限。"""
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


def sf_quote(rest, env):
    """(quote 数据)：原样返回，不求值。"""
    args = _form_arguments(rest, "quote")
    _require_count(args, 1, 1, "quote")
    return args[0]


def sf_if(rest, env):
    """(if 测试 真分支 假分支?)：只求值命中的那个分支。"""
    args = _form_arguments(rest, "if")
    _require_count(args, 2, 3, "if")
    if is_truthy(evaluate(args[0], env)):
        return evaluate(args[1], env)
    if len(args) == 3:
        return evaluate(args[2], env)
    return None  # 缺省假分支：无值，不打印


def sf_cond(rest, env):
    """(cond (测试 表达式...) ...)：命中第一个真测试，按 begin 求值其函数体。"""
    clauses = _form_arguments(rest, "cond")
    for clause in clauses:
        parts = pair_to_list(clause, "cond 的子句")
        if not parts:
            raise SchemeError("cond 的子句不能为空，应写成 (测试 表达式...)")
        test = parts[0]
        if is_symbol(test) and test.name == "else":
            if len(parts) == 1:
                raise SchemeError("cond 的 else 子句至少要有一个表达式")
            return evaluate_body(parts[1:], env)
        result = evaluate(test, env)
        if is_truthy(result):
            if len(parts) == 1:
                return result  # 子句里没有表达式时，返回测试值本身
            return evaluate_body(parts[1:], env)
    return None


def sf_and(rest, env):
    """(and e1 e2 ...)：遇到第一个 #f 立刻返回 #f；全真返回最后一个的值。"""
    args = _form_arguments(rest, "and")
    result = True
    for arg in args:
        result = evaluate(arg, env)
        if not is_truthy(result):
            return False
    return result


def sf_or(rest, env):
    """(or e1 e2 ...)：遇到第一个真值立刻返回它；全假返回 #f。"""
    args = _form_arguments(rest, "or")
    for arg in args:
        result = evaluate(arg, env)
        if is_truthy(result):
            return result
    return False


def sf_begin(rest, env):
    """(begin e1 e2 ...)：顺序求值，返回最后一个。"""
    return evaluate_body(_form_arguments(rest, "begin"), env)


def sf_define(rest, env):
    """(define 名 表达式) 或 (define (函数名 参数...) 体...)。

    先求值右侧表达式，再绑定；结果是符号名。函数简写等价于 lambda，
    所以函数体内可以调用自己（递归）。
    """
    args = _form_arguments(rest, "define")
    _require_count(args, 1, None, "define")
    target = args[0]

    if isinstance(target, Pair):  # (define (f x) ...)
        name = target.car
        if not is_symbol(name):
            raise SchemeError("define 的函数名必须是符号：%s" % (write(name),))
        params = pair_to_list(target.cdr, "define 的参数表")
        _check_params(params, "define")
        if len(args) < 2:
            raise SchemeError("define 定义的函数 %s 缺少函数体" % (name.name,))
        env.define(name, UserFunction(params, args[1:], env))
        return name

    if not is_symbol(target):  # (define x 1)
        raise SchemeError("define 的名字必须是符号：%s" % (write(target),))
    _require_count(args, 2, 2, "define")
    value = evaluate(args[1], env)
    env.define(target, value)
    return target


def sf_lambda(rest, env):
    """(lambda (参数...) 体...)：函数体此时不求值，产生闭包。"""
    args = _form_arguments(rest, "lambda")
    _require_count(args, 2, None, "lambda")
    params = pair_to_list(args[0], "lambda 的参数表")
    _check_params(params, "lambda")
    return UserFunction(params, args[1:], env)


def _check_params(params: list, where: str) -> None:
    """参数名必须是符号且不重复（本语言不支持可变参数）。"""
    seen = set()
    for param in params:
        if not is_symbol(param):
            raise SchemeError(
                "%s 的参数必须是符号，不能是 %s" % (where, write(param)))
        if param in seen:
            raise SchemeError("%s 的参数 %s 重复了" % (where, param.name))
        seen.add(param)


def sf_let(rest, env):
    """(let ((名 表达式)...) 体...)：绑定表达式在外层环境求值（并行绑定）。"""
    args = _form_arguments(rest, "let")
    _require_count(args, 2, None, "let")
    bindings = pair_to_list(args[0], "let 的绑定表")

    # 先全部在外层环境求值，绑定之间互不可见
    pairs = []
    for binding in bindings:
        parts = pair_to_list(binding, "let 的绑定")
        _require_count(parts, 2, 2, "let 的每个绑定 (名 表达式)")
        name = parts[0]
        if not is_symbol(name):
            raise SchemeError("let 绑定的名字必须是符号：%s" % (write(name),))
        pairs.append((name, evaluate(parts[1], env)))

    frame = env.extend("let")
    for name, value in pairs:
        frame.define(name, value)
    return evaluate_body(args[1:], frame)


# 特殊形式名 -> 处理函数
SPECIAL_FORMS = {
    Symbol("quote"): sf_quote,
    Symbol("if"): sf_if,
    Symbol("cond"): sf_cond,
    Symbol("and"): sf_and,
    Symbol("or"): sf_or,
    Symbol("begin"): sf_begin,
    Symbol("define"): sf_define,
    Symbol("lambda"): sf_lambda,
    Symbol("let"): sf_let,
}


# --------------------------------------------------------------------------
# 顶层入口
# --------------------------------------------------------------------------

def evaluate_program(expressions: list, env: Environment) -> list:
    """按顺序求值顶层表达式，返回每个表达式的结果。"""
    return [evaluate(expression, env) for expression in expressions]
