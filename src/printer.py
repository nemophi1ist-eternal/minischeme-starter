"""打印：把值渲染成文本。

两种场合的区别只有一个——字符串要不要带引号：

    write   字符串带引号、带转义        （顶层结果的打印）
    display 字符串原样输出              （display 内置过程）
"""

from __future__ import annotations

from values import NIL, Pair, Symbol, format_float, is_nil

# 需要转义成 \x 形式的控制字符
_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\t": "\\t",
    "\r": "\\r",
}


def escape_string(text: str) -> str:
    """把字符串内容转成带转义的可打印形式（不含两端的引号）。"""
    parts = []
    for char in text:
        if char in _ESCAPES:
            parts.append(_ESCAPES[char])
        elif ord(char) < 32 or ord(char) == 127:
            parts.append("\\x%02x;" % ord(char))
        else:
            parts.append(char)
    return "".join(parts)


def write(value) -> str:
    """渲染成"可被读回"的文本：字符串带引号与转义。"""
    if is_nil(value):
        return "()"
    if value is None:
        return ""
    if value is True:
        return "#t"
    if value is False:
        return "#f"
    if isinstance(value, Symbol):
        return value.name
    if isinstance(value, str):
        return '"%s"' % escape_string(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format_float(value)
    if isinstance(value, Pair):
        return _write_pair(value)
    if getattr(value, "is_procedure", False):  # 内置过程与用户函数统一表示
        return "#<procedure>"
    return str(value)


def display(value) -> str:
    """渲染成"给人看"的文本：字符串不带引号。"""
    if isinstance(value, str):
        return value
    return write(value)


def _write_pair(value: Pair) -> str:
    """点对链：真列表打印成 (1 2 3)，否则用点号 (1 . 2)。"""
    parts = []
    node = value
    seen = set()
    while isinstance(node, Pair):
        if id(node) in seen:  # 防御性：结构成环时不至于卡死
            parts.append(". #<cycle>")
            return "(%s)" % " ".join(parts)
        seen.add(id(node))
        parts.append(write(node.car))
        node = node.cdr
    if not is_nil(node):
        parts.append(". " + write(node))
    return "(%s)" % " ".join(parts)


def write_line(value) -> str:
    """顶层结果的一行文本（结果为空值时不打印，由调用方判断）。"""
    return write(value)
