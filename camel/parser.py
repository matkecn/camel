from __future__ import annotations

from typing import Any

from .errors import CmlSyntaxError
from .lexer import Lexer, Token
from .nodes import (
    CmlDocument,
    CmlObject,
    CmlReference,
    Entry,
    Include,
    Parent,
    Rule,
    RuleField,
    Scope,
)

BLOCK_DECORATORS = {
    "deprecated",
    "experimental",
    "internal",
    "private",
    "public",
    "readonly",
    "frozen",
    "mutable",
}

ENTRY_MODIFIERS = {"const", "child", "optional"}

VALUE_KEYWORDS = {
    "true": True,
    "false": False,
    "null": None,
    "none": None,
    "nil": None,
}


class Parser:
    def __init__(self, tokens: list[Token], filename: str = "<string>") -> None:
        self.tokens = tokens
        self.filename = filename
        self.pos = 0

    def parse(self) -> CmlDocument:
        document = CmlDocument(filename=self.filename)
        while True:
            self._skip_separators()
            if self._check("EOF"):
                break
            decorators = self._parse_decorators()
            self._skip_separators()
            if self._check("EOF"):
                break
            if self._check("AT"):
                self._advance()
                keyword_token = self._expect("IDENT", "expected a keyword after '@'")
                keyword = keyword_token.value
                if keyword in ("required", "require"):
                    self._parse_required(document)
                elif keyword == "init":
                    self._parse_init(document)
                elif keyword == "include":
                    self._parse_include(document)
                elif keyword == "single":
                    self._parse_single(document, decorators)
                elif keyword in ("parent", "scope"):
                    self._parse_block(document, keyword, decorators)
                elif keyword == "alias":
                    self._parse_alias(document)
                elif keyword == "rule":
                    self._parse_rule(document, decorators)
                else:
                    self._error(f"unknown keyword '@{keyword}'", keyword_token)
            else:
                if decorators:
                    document.decorators.extend(decorators)
                entry = self._parse_entry()
                document.singles[entry.name] = entry
                self._consume_end()
        return document

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _peek(self, offset: int = 0) -> Token:
        index = self.pos + offset
        if index >= len(self.tokens):
            return self.tokens[-1]
        return self.tokens[index]

    def _advance(self) -> Token:
        token = self._current()
        if token.kind != "EOF":
            self.pos += 1
        return token

    def _check(self, kind: str) -> bool:
        return self._current().kind == kind

    def _match(self, kind: str) -> Token | None:
        if self._check(kind):
            return self._advance()
        return None

    def _expect(self, kind: str, message: str | None = None) -> Token:
        if not self._check(kind):
            self._error(message or f"expected {kind.lower()}")
        return self._advance()

    def _error(self, message: str, token: Token | None = None) -> None:
        token = token or self._current()
        raise CmlSyntaxError(
            message,
            filename=self.filename,
            line=token.line,
            column=token.column,
        )

    def _skip_separators(self) -> None:
        while self._check("SEMI") or self._check("COMMA") or self._check("NEWLINE"):
            self._advance()

    def _consume_end(self) -> None:
        self._skip_separators()

    def _parse_decorators(self) -> list[str]:
        decorators: list[str] = []
        while self._check("AT") and self._peek(1).kind == "IDENT" and self._peek(1).value in BLOCK_DECORATORS:
            self._advance()
            decorators.append(self._advance().value)
            self._skip_separators()
        return decorators

    def _parse_init(self, document: CmlDocument) -> None:
        document.init = self._parse_init_name()
        self._consume_end()

    def _parse_init_name(self) -> str:
        if self._match("LT"):
            parts: list[str] = []
            while not self._check("GT") and not self._check("EOF"):
                token = self._advance()
                if token.kind in ("IDENT", "NUMBER", "STRING", "REF"):
                    parts.append(str(token.value))
                elif token.kind == "COMMA":
                    parts.append(",")
                else:
                    self._error("invalid character in init name", token)
            self._expect("GT", "expected '>' to close init name")
            return "".join(parts)
        if self._check("IDENT") or self._check("STRING"):
            return self._advance().value
        self._error("expected an init name")

    def _parse_include(self, document: CmlDocument) -> None:
        path_token = self._expect("STRING", "expected a quoted path after '@include'")
        document.includes.append(Include(path_token.value, path_token.line))
        self._consume_end()

    def _parse_required(self, document: CmlDocument) -> None:
        names: list[str] = []
        while not self._check("SEMI") and not self._check("NEWLINE") and not self._check("EOF"):
            if self._check("IDENT") or self._check("STRING") or self._check("REF"):
                names.append(self._advance().value)
            else:
                self._error("expected a required key name")
            if self._match("PIPE") or self._match("COMMA"):
                continue
            break
        self._consume_end()
        document.required.extend(names)

    def _parse_single(self, document: CmlDocument, decorators: list[str]) -> None:
        if decorators:
            document.decorators.extend(decorators)
        modifiers: set[str] = set()
        while (
            self._check("AT")
            and self._peek(1).kind == "IDENT"
            and self._peek(1).value in ENTRY_MODIFIERS
        ):
            self._advance()
            modifiers.add(self._advance().value)
        entry = self._parse_entry()
        entry.const = entry.const or "const" in modifiers
        entry.child = entry.child or "child" in modifiers
        entry.optional = entry.optional or "optional" in modifiers
        document.singles[entry.name] = entry
        self._consume_end()

    def _parse_block(self, document: CmlDocument, keyword: str, decorators: list[str]) -> None:
        name_token = self._expect("IDENT", f"expected a {keyword} name")
        self._expect("LBRACE", f"expected '{{' after {keyword} name")
        entries, uses = self._parse_block_body()
        self._expect("RBRACE", f"expected '}}' to close {keyword}")
        self._consume_end()
        if keyword == "parent":
            document.parents[name_token.value] = Parent(
                name_token.value,
                entries,
                decorators=decorators,
                uses=uses,
                line=name_token.line,
            )
        else:
            document.scopes[name_token.value] = Scope(
                name_token.value,
                entries,
                decorators=decorators,
                uses=uses,
                line=name_token.line,
            )

    def _parse_block_body(self) -> tuple[dict[str, Entry], list[str]]:
        entries: dict[str, Entry] = {}
        uses: list[str] = []
        while not self._check("RBRACE") and not self._check("EOF"):
            self._skip_separators()
            if self._check("RBRACE") or self._check("EOF"):
                break
            if (
                self._check("AT")
                and self._peek(1).kind == "IDENT"
                and self._peek(1).value == "use"
            ):
                self._advance()
                self._advance()
                rule_token = self._expect("IDENT", "expected a rule name after '@use'")
                uses.append(rule_token.value)
                self._consume_end()
                continue
            self._parse_decorators()
            modifiers: set[str] = set()
            while (
                self._check("AT")
                and self._peek(1).kind == "IDENT"
                and self._peek(1).value in ENTRY_MODIFIERS
            ):
                self._advance()
                modifiers.add(self._advance().value)
            entry = self._parse_entry()
            entry.const = entry.const or "const" in modifiers
            entry.child = entry.child or "child" in modifiers
            entry.optional = entry.optional or "optional" in modifiers
            entries[entry.name] = entry
            self._consume_end()
        return entries, uses

    def _parse_entry(self) -> Entry:
        name_token = self._parse_key()
        type_name: str | None = None
        if self._match("COLON"):
            type_token = self._expect("TYPE", "expected a type after ':'")
            type_name = type_token.value
        value: Any = None
        has_value = False
        if self._match("EQ"):
            value = self._parse_value()
            has_value = True
        return Entry(
            name_token.value,
            value,
            type=type_name,
            has_value=has_value,
            line=name_token.line,
            column=name_token.column,
        )

    def _parse_key(self) -> Token:
        if self._check("IDENT") or self._check("STRING"):
            return self._advance()
        self._error("expected a key name")

    def _parse_alias(self, document: CmlDocument) -> None:
        target_token = self._parse_key()
        alias_token = self._parse_key()
        self._consume_end()
        document.aliases[alias_token.value] = target_token.value

    def _parse_rule(self, document: CmlDocument, decorators: list[str]) -> None:
        name_token = self._expect("IDENT", "expected a rule name")
        self._expect("LBRACE", "expected '{' after rule name")
        rule = Rule(name_token.value, decorators=decorators, line=name_token.line)
        while not self._check("RBRACE") and not self._check("EOF"):
            self._skip_separators()
            if self._check("RBRACE") or self._check("EOF"):
                break
            optional = False
            if (
                self._check("AT")
                and self._peek(1).kind == "IDENT"
                and self._peek(1).value == "optional"
            ):
                self._advance()
                self._advance()
                optional = True
            if self._check("REF") or self._check("IDENT") or self._check("STRING"):
                field_token = self._advance()
            else:
                self._error("expected a rule field")
            type_name: str | None = None
            if self._match("COLON"):
                type_name = self._expect("TYPE", "expected a type after ':'").value
            default: Any = None
            has_default = False
            if self._match("EQ"):
                default = self._parse_value()
                has_default = True
            rule.fields[field_token.value] = RuleField(
                field_token.value,
                type=type_name,
                optional=optional,
                default=default,
                has_default=has_default,
            )
            self._consume_end()
        self._expect("RBRACE", "expected '}' to close rule")
        self._consume_end()
        document.rules[name_token.value] = rule

    def _parse_value(self) -> Any:
        token = self._current()
        if token.kind == "STRING":
            self._advance()
            return token.value
        if token.kind == "NUMBER":
            self._advance()
            return token.value
        if token.kind == "IDENT":
            self._advance()
            lowered = token.value.lower()
            if lowered in VALUE_KEYWORDS:
                return VALUE_KEYWORDS[lowered]
            return token.value
        if token.kind == "REF":
            self._advance()
            args: list[Any] = []
            if self._match("LPAREN"):
                while not self._check("RPAREN") and not self._check("EOF"):
                    self._skip_separators()
                    if self._check("RPAREN"):
                        break
                    args.append(self._parse_value())
                    self._skip_separators()
                self._expect("RPAREN", "expected ')' to close reference call")
            return CmlReference(token.value, tuple(args))
        if token.kind == "LPAREN":
            self._advance()
            return self._parse_sequence("RPAREN")
        if token.kind == "LBRACKET":
            self._advance()
            return self._parse_sequence("RBRACKET")
        if token.kind == "LBRACE":
            self._advance()
            return self._parse_object()
        self._error("expected a value", token)

    def _parse_sequence(self, closing: str) -> list[Any]:
        items: list[Any] = []
        while not self._check(closing) and not self._check("EOF"):
            self._skip_separators()
            if self._check(closing):
                break
            items.append(self._parse_value())
            self._skip_separators()
        self._expect(closing, f"expected '{closing}' to close list")
        return items

    def _parse_object(self) -> CmlObject:
        result = CmlObject()
        while not self._check("RBRACE") and not self._check("EOF"):
            self._skip_separators()
            if self._check("RBRACE"):
                break
            key_token = self._parse_key()
            type_name: str | None = None
            value: Any = None
            if self._match("COLON"):
                if self._check("TYPE"):
                    type_name = self._advance().value
                    if self._match("EQ") or not (
                        self._check("SEMI")
                        or self._check("COMMA")
                        or self._check("NEWLINE")
                        or self._check("RBRACE")
                        or self._check("EOF")
                    ):
                        value = self._parse_value()
                else:
                    value = self._parse_value()
            elif self._match("EQ"):
                value = self._parse_value()
            result[key_token.value] = value
            if type_name:
                result.types[key_token.value] = type_name
            self._consume_end()
        self._expect("RBRACE", "expected '}' to close object")
        return result


def parse(text: str, filename: str = "<string>") -> CmlDocument:
    tokens = Lexer(text, filename=filename).tokenize()
    return Parser(tokens, filename=filename).parse()
