import typing

from .source_location import SourceLocation
from .token import TokenType


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        super().__init__("{}: {}".format(str(source_location), description))


class EndOfFileError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "end of file")


class UnexpectedCharError(Error):
    def __init__(self, source_location: SourceLocation, char: str) -> None:
        super().__init__(source_location, "unexpected char {}".format(repr(char)))


class UnexpectedTokenError(Error):
    def __init__(self, source_location: SourceLocation, token_data: str
                 , expected_token_types: typing.Iterable[TokenType]) -> None:
        description = "unexpected token {}".format(repr(token_data))

        if len(expected_token_types) >= 1:
            description += ", expect {}".format\
                           (" or ".join((str(expected_token_type)
                                         for expected_token_type in expected_token_types)))

        super().__init__(source_location, description)


class LocalVariableExistsError(Error):
    def __init__(self, source_location: SourceLocation, variable_name: str):
        super().__init__(source_location, "local variable `{}` exists".format(variable_name))


class VariableNotFoundError(Error):
    def __init__(self, source_location: SourceLocation, variable_name: str):
        super().__init__(source_location, "variable `{}` not found".format(variable_name))


class StackTooDeepError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "stack too deep")


class CaptureTableTooLargeError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "capture table too large")


class ConstantTableTooLargeError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "constant table too large")


class BytecodeTooLargeError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "bytecode too large")


class LvalueRequiredError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "lvalue required")
