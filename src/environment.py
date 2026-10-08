"""环境：变量绑定表 + 指向外层环境的指针。

词法作用域靠"每个环境记住自己的父环境"实现；`lambda` 创建闭包时
保存的正是定义处的环境，因此闭包能看见定义时可见的名字。
"""

from __future__ import annotations

from values import SchemeError, to_source


class Environment:
    """一层作用域。查找沿 parent 链向上走。"""

    __slots__ = ("bindings", "parent", "name")

    def __init__(self, parent: "Environment | None" = None, name: str = "frame"):
        self.bindings: dict = {}
        self.parent = parent
        self.name = name

    # -- 查询 -------------------------------------------------------------

    def lookup(self, symbol):
        """取出符号绑定的值；未绑定则报错。"""
        env = self
        while env is not None:
            if symbol in env.bindings:
                return env.bindings[symbol]
            env = env.parent
        raise SchemeError("未定义的变量：%s" % (to_source(symbol),))

    def has(self, symbol) -> bool:
        env = self
        while env is not None:
            if symbol in env.bindings:
                return True
            env = env.parent
        return False

    # -- 修改 -------------------------------------------------------------

    def define(self, symbol, value) -> None:
        """在本层绑定名字（顶层 define 与函数参数都走这里）。"""
        self.bindings[symbol] = value

    def extend(self, name: str = "frame") -> "Environment":
        """以本环境为父环境新建一层。"""
        return Environment(parent=self, name=name)

    def __repr__(self) -> str:
        return "Environment(%s, %d bindings)" % (self.name, len(self.bindings))
