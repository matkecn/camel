from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import CmlSyntaxError


@dataclass(slots=True)
class Token:
    kind: str
    value: Any
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.kind!r}, {self.value!r}, {self.line}:{self.column})"


PUNCTUATION = {
    "{": "LBRACE",
    "}": "RBRACE",
    "(": "LPAREN",
    ")": "RPAREN",
    "[": "LBRACKET",
    "]": "RBRACKET",
    ":": "COLON",
    "=": "EQ",
    ";": "SEMI",
    ",": "COMMA",
    "|": "PIPE",
    "<": "LT",
    ">": "GT",
}

NAME_START = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_")
NAME_CHARS = NAME_START | set("0123456789.-")
DIGITS = set("0123456789")


class Lexer:
    def __init__(self, text: str, filename: str = "<string>") -> None:
        self.text = text
        self.filename = filename
        self.pos = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while self.pos < len(self.text):
            char = self._peek()
            if char in " \t\r\f\v":
                self._advance()
                continue
            if char == "\n":
                tokens.append(Token("NEWLINE", "\n", self.line, self.column))
                self._advance()
                continue
            if char == "#":
                self._skip_comment()
                continue
            if char in "\"'":
                tokens.append(self._read_string())
                continue
            if char == "%":
                tokens.append(self._read_type())
                continue
            if char == "$":
                tokens.append(self._read_reference())
                continue
            if char == "@":
                tokens.append(Token("AT", "@", self.line, self.column))
                self._advance()
                continue
            if char in DIGITS or (char == "." and self._peek(1) in DIGITS):
                tokens.append(self._read_number())
                continue
            if char == "-" and self._peek(1) in DIGITS:
                tokens.append(self._read_number())
                continue
            if char in NAME_START:
                tokens.append(self._read_identifier())
                continue
            if char in PUNCTUATION:
                tokens.append(Token(PUNCTUATION[char], char, self.line, self.column))
                self._advance()
                continue
            self._error(f"unexpected character {char!r}")
        tokens.append(Token("EOF", None, self.line, self.column))
        return tokens

    def _peek(self, offset: int = 0) -> str:
        index = self.pos + offset
        if index >= len(self.text):
            return ""
        return self.text[index]

    def _advance(self) -> str:
        char = self.text[self.pos]
        self.pos += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char

    def _error(self, message: str, line: int | None = None, column: int | None = None) -> None:
        raise CmlSyntaxError(
            message,
            filename=self.filename,
            line=self.line if line is None else line,
            column=self.column if column is None else column,
        )

    def _skip_comment(self) -> None:
        while self.pos < len(self.text) and self._peek() != "\n":
            self._advance()

    def _read_identifier(self) -> Token:
        line, column = self.line, self.column
        start = self.pos
        self._advance()
        while self.pos < len(self.text) and self._peek() in NAME_CHARS:
            self._advance()
        return Token("IDENT", self.text[start:self.pos], line, column)

    def _read_type(self) -> Token:
        line, column = self.line, self.column
        self._advance()
        if self._peek() not in NAME_START:
            self._error("expected a type name after '%'", line, column)
        start = self.pos
        self._advance()
        while self.pos < len(self.text) and self._peek() in NAME_CHARS:
            self._advance()
        return Token("TYPE", self.text[start:self.pos], line, column)

    def _read_reference(self) -> Token:
        line, column = self.line, self.column
        self._advance()
        if self._peek() not in NAME_START:
            self._error("expected a reference name after '$'", line, column)
        start = self.pos
        self._advance()
        while self.pos < len(self.text) and self._peek() in NAME_CHARS:
            self._advance()
        return Token("REF", self.text[start:self.pos], line, column)

    def _read_number(self) -> Token:
        line, column = self.line, self.column
        start = self.pos
        if self._peek() == "-":
            self._advance()
        while self._peek() in DIGITS:
            self._advance()
        is_float = False
        if self._peek() == "." and self._peek(1) in DIGITS:
            is_float = True
            self._advance()
            while self._peek() in DIGITS:
                self._advance()
        if self._peek() and self._peek() in "eE":
            next_char = self._peek(1)
            after_sign = self._peek(2)
            if next_char in DIGITS or (next_char in "+-" and after_sign in DIGITS):
                is_float = True
                self._advance()
                if self._peek() and self._peek() in "+-":
                    self._advance()
                while self._peek() in DIGITS:
                    self._advance()
        raw = self.text[start:self.pos]
        try:
            value: int | float = float(raw) if is_float else int(raw)
        except ValueError:
            self._error(f"invalid number {raw!r}", line, column)
        return Token("NUMBER", value, line, column)

    def _read_string(self) -> Token:
        line, column = self.line, self.column
        quote = self._advance()
        chars: list[str] = []
        while self.pos < len(self.text):
            char = self._advance()
            if char == quote:
                return Token("STRING", "".join(chars), line, column)
            if char == "\n":
                self._error("unterminated string", line, column)
            if char != "\\":
                chars.append(char)
                continue
            if self.pos >= len(self.text):
                self._error("unterminated escape sequence", line, column)
            escape = self._advance()
            simple = {
                "n": "\n",
                "t": "\t",
                "r": "\r",
                "b": "\b",
                "f": "\f",
                "v": "\v",
                "0": "\0",
                "\\": "\\",
                "\"": "\"",
                "'": "'",
                "/": "/",
            }
            if escape in simple:
                chars.append(simple[escape])
                continue
            if escape == "u":
                digits = self.text[self.pos:self.pos + 4]
                if len(digits) != 4 or any(char not in "0123456789abcdefABCDEF" for char in digits):
                    self._error("invalid unicode escape", line, column)
                chars.append(chr(int(digits, 16)))
                for _ in range(4):
                    self._advance()
                continue
            if escape == "x":
                digits = self.text[self.pos:self.pos + 2]
                if len(digits) != 2 or any(char not in "0123456789abcdefABCDEF" for char in digits):
                    self._error("invalid hex escape", line, column)
                chars.append(chr(int(digits, 16)))
                for _ in range(2):
                    self._advance()
                continue
            self._error(f"unknown escape sequence \\{escape}", line, column)
        self._error("unterminated string", line, column)
        raise AssertionError("unreachable")
