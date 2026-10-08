"""语法分析：把 token 列表组装成表达式（嵌套的数据结构）。

表达式只有这几种形态：

    int / float / bool / str / Symbol   -- 自求值或变量引用
    Pair                                -- 组合（特殊形式或函数调用）

`quote` 的数据在解析阶段就被折成点对链，因此 `'(1 2 3)` 与
`(list 1 2 3)` 的表示完全一致（spec §11 最后一条）。

模块名用 reader 而不是 parser：`src/` 会被放进模块搜索路径，
若取名 parser.py 会遮蔽 Python 标准库的 parser 模块。
"""

from __future__ import annotations

from lexer import (BOOLEAN, DOT, LPAREN, NUMBER, QUOTE, RPAREN, STRING, SYMBOL,
                   tokenize)
from values import NIL, Pair, SchemeError, Symbol, intern, make_list

# 'x 会展开成 (quote x)
QUOTE_SYMBOL = Symbol("quote")


class Reader:
    """把 token 序列读成表达式序列。"""

    def __init__(self, tokens: list):
        self.tokens = tokens
        self.index = 0

    # -- 基础动作 ---------------------------------------------------------

    def _peek(self):
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None

    def _advance(self):
        token = self.tokens[self.index]
        self.index += 1
        return token

    def _at_end(self) -> bool:
        return self.index >= len(self.tokens)

    # -- 对外入口 ---------------------------------------------------------

    def read_program(self) -> list:
        """读入整个程序（0 个或多个顶层表达式）。"""
        expressions = []
        while not self._at_end():
            expressions.append(self.read_expression())
        return expressions

    def read_expression(self):
        """读入一个表达式。"""
        if self._at_end():
            raise SchemeError("程序意外结束：还有表达式没有写完")
        token = self._advance()
        if token.kind == LPAREN:
            return self._read_list(token)
        if token.kind == RPAREN:
            raise SchemeError(
                "第 %d 行第 %d 列：多出一个右括号 )" % (token.line, token.column))
        if token.kind == QUOTE:
            return make_list([QUOTE_SYMBOL, self.read_expression()])
        if token.kind == DOT:
            raise SchemeError(
                "第 %d 行第 %d 列：点号 . 只能出现在列表内部，如 (a . b)"
                % (token.line, token.column))
        if token.kind in (NUMBER, BOOLEAN, STRING):
            return token.value
        if token.kind == SYMBOL:
            return intern(token.value)
        raise SchemeError(
            "第 %d 行第 %d 列：无法解析的记号 %s"
            % (token.line, token.column, token.text))

    def _read_list(self, open_token) -> object:
        """已经吃掉了左括号，这里读到配对的右括号为止。"""
        items = []
        tail = NIL
        while True:
            token = self._peek()
            if token is None:
                raise SchemeError(
                    "第 %d 行第 %d 列：缺少与这个左括号配对的右括号"
                    % (open_token.line, open_token.column))
            if token.kind == RPAREN:
                self._advance()
                if tail is NIL:
                    return make_list(items)
                return _attach_tail(items, tail)
            if token.kind == DOT:
                if not items:
                    raise SchemeError(
                        "第 %d 行第 %d 列：点号 . 前面至少要有一个元素"
                        % (token.line, token.column))
                if tail is not NIL:
                    raise SchemeError(
                        "第 %d 行第 %d 列：一个列表里只能出现一个点号 ."
                        % (token.line, token.column))
                self._advance()
                tail = self.read_expression()
                continue
            items.append(self.read_expression())


def _attach_tail(items: list, tail) -> object:
    """把 (a b . tail) 组装成 (a . (b . tail))。"""
    result = tail
    for item in reversed(items):
        result = Pair(item, result)
    return result


def read(source: str) -> list:
    """源文本 -> 顶层表达式列表。"""
    return Reader(tokenize(source)).read_program()
