"""词法分析：把程序文本切成 token 列表。

只管识别"零件"，不关心零件怎么组合；组合是 parser 的事。
每个 Token 记住自己的行号与列号，便于报错时定位。
"""

from __future__ import annotations

from dataclasses import dataclass

from values import SchemeError

# token 类别
LPAREN = "LPAREN"      # (
RPAREN = "RPAREN"      # )
QUOTE = "QUOTE"        # '
DOT = "DOT"            # . （点对写法 (a . b)）
NUMBER = "NUMBER"      # 42 / -7 / 3.14
BOOLEAN = "BOOLEAN"    # #t / #f
STRING = "STRING"      # "hello"
SYMBOL = "SYMBOL"      # foo / + / list?

_DELIMITERS = set("()'\" \t\r\n\f\v;")
_SPECIALS = {
    "(": LPAREN,
    ")": RPAREN,
    "'": QUOTE,
    ".": DOT,
}
_HEX_DIGITS = set("0123456789abcdefABCDEF")


def _is_hex_digit(char: str) -> bool:
    return char in _HEX_DIGITS


@dataclass
class Token:
    kind: str
    text: str      # 原始文本
    value: object  # 已解释好的值（数字/布尔/字符串/符号名），部分类别为 None
    line: int
    column: int

    def __repr__(self) -> str:  # 调试用
        return "Token(%s, %r, line=%d, col=%d)" % (
            self.kind, self.text, self.line, self.column)


class Lexer:
    """一次扫描整个源文本，产出 token 列表。"""

    def __init__(self, source: str):
        # 统一换行符，之后行号统计才准确（Windows 上源文件常是 \r\n）
        self.source = source.replace("\r\n", "\n").replace("\r", "\n")
        self.index = 0
        self.line = 1
        self.column = 1
        self.length = len(self.source)

    # -- 基础动作 ---------------------------------------------------------

    def _peek(self, offset: int = 0) -> str:
        pos = self.index + offset
        if pos < self.length:
            return self.source[pos]
        return ""

    def _advance(self) -> str:
        char = self.source[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _skip_blank_and_comments(self) -> None:
        while self.index < self.length:
            char = self._peek()
            if char in " \t\n\f\v":
                self._advance()
            elif char == ";":  # 注释：; 到行尾
                while self.index < self.length and self._peek() != "\n":
                    self._advance()
            else:
                return

    # -- 主循环 -----------------------------------------------------------

    def tokenize(self) -> list:
        tokens = []
        while True:
            self._skip_blank_and_comments()
            if self.index >= self.length:
                return tokens
            tokens.append(self._next_token())

    def _next_token(self) -> Token:
        line, column = self.line, self.column
        char = self._peek()

        if char in _SPECIALS:
            self._advance()
            return Token(_SPECIALS[char], char, char, line, column)
        if char == '"':
            return self._read_string(line, column)
        if char == "#":
            return self._read_boolean(line, column)
        if char.isdigit():
            return self._read_number(line, column)
        if self._starts_number():
            return self._read_number(line, column)
        return self._read_symbol(line, column)

    def _starts_number(self) -> bool:
        """符号可能以 + - . 开头；只有后面紧跟数字时才当数字读。"""
        char = self._peek()
        if char not in "+-.":
            return False
        return self._peek(1).isdigit()

    # -- 各类零件 ---------------------------------------------------------

    def _read_string(self, line: int, column: int) -> Token:
        start = self.index
        self._advance()  # 开引号
        chars = []
        while True:
            if self.index >= self.length:
                raise SchemeError(
                    "第 %d 行第 %d 列：字符串缺少收尾的双引号" % (line, column))
            char = self._advance()
            if char == '"':
                break
            if char == "\\":
                if self.index >= self.length:
                    raise SchemeError(
                        "第 %d 行第 %d 列：转义符 \\ 出现在字符串末尾" % (line, column))
                escape = self._advance()
                if escape == "n":
                    chars.append("\n")
                elif escape == "t":
                    chars.append("\t")
                elif escape == "r":
                    chars.append("\r")
                elif escape == '"':
                    chars.append('"')
                elif escape == "\\":
                    chars.append("\\")
                elif escape == "x":
                    chars.append(self._read_hex_escape(line, column))
                else:  # 未知转义：原样保留反斜杠，尽量不制造信息丢失
                    chars.append("\\" + escape)
            else:
                chars.append(char)
        text = self.source[start:self.index]
        return Token(STRING, text, "".join(chars), line, column)

    def _read_hex_escape(self, line: int, column: int) -> str:
        """读 \\xHH; 形式的转义（printer 用它打印不可见控制字符）。"""
        digits = []
        while self.index < self.length and _is_hex_digit(self._peek()):
            digits.append(self._advance())
        if self.index < self.length and self._peek() == ";":
            self._advance()
        if not digits:
            raise SchemeError(
                "第 %d 行第 %d 列：\\x 转义后面缺少十六进制数字" % (line, column))
        return chr(int("".join(digits), 16))

    def _read_boolean(self, line: int, column: int) -> Token:
        start = self.index
        self._advance()  # '#'
        name = self._advance()
        if name == "t":
            value = True
        elif name == "f":
            value = False
        else:
            raise SchemeError(
                "第 %d 行第 %d 列：无法识别的布尔字面量 #%s（只有 #t 与 #f）"
                % (line, column, name))
        # 布尔字面量后面必须紧跟分隔符，避免把 #true 之类静默切开
        if self.index < self.length and self._peek() not in _DELIMITERS:
            raise SchemeError(
                "第 %d 行第 %d 列：无法识别的记号 %s"
                % (line, column, self.source[start:self._word_end()]))
        return Token(BOOLEAN, self.source[start:self.index], value, line, column)

    def _read_number(self, line: int, column: int) -> Token:
        start = self.index
        if self._peek() in "+-":
            self._advance()
        seen_dot = False
        while self.index < self.length:
            char = self._peek()
            if char.isdigit():
                self._advance()
            elif char == "." and not seen_dot:
                # 只有当点号后面还是数字时才算小数点，否则 "1." 之类的写法
                # 应当留着让 parser 报错，而不是悄悄吞掉
                following = self._peek(1)
                if not following.isdigit():
                    break
                seen_dot = True
                self._advance()
            else:
                break
        text = self.source[start:self.index]
        if self.index < self.length and self._peek() not in _DELIMITERS:
            raise SchemeError(
                "第 %d 行第 %d 列：无法识别的记号 %s"
                % (line, column, self.source[start:self._word_end()]))
        if seen_dot:
            value = float(text)
        else:
            value = int(text)
        return Token(NUMBER, text, value, line, column)

    def _read_symbol(self, line: int, column: int) -> Token:
        start = self.index
        while self.index < self.length and self._peek() not in _DELIMITERS:
            self._advance()
        text = self.source[start:self.index]
        if not text:
            raise SchemeError(
                "第 %d 行第 %d 列：无法识别的字符 %r" % (line, column, self._peek()))
        return Token(SYMBOL, text, text, line, column)

    def _word_end(self) -> int:
        pos = self.index
        while pos < self.length and self.source[pos] not in _DELIMITERS:
            pos += 1
        return pos


def tokenize(source: str) -> list:
    """把源文本切成 token 列表。"""
    return Lexer(source).tokenize()
