__all__ = (
    "SourceLocation",
)


import typing


class SourceLocation(typing.NamedTuple):
    file_name: str
    line_number: int
    column_number: int

    def __str__(self) -> str:
        return "{}:{}:{}".format(self.file_name, self.line_number, self.column_number)
