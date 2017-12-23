import typing

from .function_prototype import SourceLocation
from .value import ValueType


class Error(Exception):
    def __init__(self, source_location: SourceLocation, description: str) -> None:
        super().__init__("{}: {}".format(str(source_location), description))


class StackOverflowError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "stack overflow")


class MissingArgumentError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "missing argument")


class TooManyArgumentsError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "too many arguments")


class IncompatibleOperandTypesError(Error):
    def __init__(self, source_location: SourceLocation, value_types: typing.List[ValueType]) \
        -> None:
        super().__init__(source_location, "incompatible operand type(s): {}"
                                          .format(", ".join((str(value_type)
                                                             for value_type in value_types))))


class IndexOutOfRangeError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "index out of range")


class DivideByZeroError(Error):
    def __init__(self, source_location: SourceLocation) -> None:
        super().__init__(source_location, "divide by zero")
