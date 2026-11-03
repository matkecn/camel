from __future__ import annotations


class CmlError(Exception):
    """Base exception for every CamelConfig error."""


class CmlSyntaxError(CmlError):
    def __init__(
        self,
        message: str,
        *,
        filename: str = "<string>",
        line: int = 0,
        column: int = 0,
    ) -> None:
        self.message = message
        self.filename = filename
        self.line = line
        self.column = column
        location = filename
        if line:
            location += f":{line}"
            if column:
                location += f":{column}"
        super().__init__(f"{location}: {message}")


class CmlTypeError(CmlError):
    pass


class CmlRequiredError(CmlError):
    pass


class CmlValidationError(CmlError):
    def __init__(self, report: object) -> None:
        self.report = report
        issues = getattr(report, "issues", [])
        lines = [str(issue) for issue in issues if getattr(issue, "level", "") == "error"]
        message = "\n".join(lines) if lines else "CamelConfig validation failed"
        super().__init__(message)


class CmlPathError(CmlError):
    pass
