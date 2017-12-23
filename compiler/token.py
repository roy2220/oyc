__all__ = (
    "BasicTokenType",
    "ExtraTokenType",
    "TokenType",
    "Token",
)


import enum
import typing

from .source_location import SourceLocation


class BasicTokenType(enum.IntEnum):
    NO = 0

    ABSTRACT_BEGIN = enum.auto()
    COMMENT = ABSTRACT_BEGIN
    WHITE_SPACE = enum.auto()
    INTEGER_LITERAL = enum.auto()
    FLOATING_POINT_LITERAL = enum.auto()
    STRING_LITERAL = enum.auto()
    IDENTIFIER = enum.auto()
    ABSTRACT_END = IDENTIFIER + 1

    KEYWORD_BEGIN = enum.auto()
    AUTO_KEYWORD = KEYWORD_BEGIN
    BOOL_KEYWORD = enum.auto()
    BREAK_KEYWORD = enum.auto()
    CASE_KEYWORD = enum.auto()
    CONTINUE_KEYWORD = enum.auto()
    DEFAULT_KEYWORD = enum.auto()
    DELETE_KEYWORD = enum.auto()
    DO_KEYWORD = enum.auto()
    ELSE_KEYWORD = enum.auto()
    FALSE_KEYWORD = enum.auto()
    FLOAT_KEYWORD = enum.auto()
    FOREACH_KEYWORD = enum.auto()
    FOR_KEYWORD = enum.auto()
    IF_KEYWORD = enum.auto()
    INT_KEYWORD = enum.auto()
    NULL_KEYWORD = enum.auto()
    REQUIRE_KEYWORD = enum.auto()
    RETURN_KEYWORD = enum.auto()
    SIZEOF_KEYWORD = enum.auto()
    STRUCT_KEYWORD = enum.auto()
    STR_KEYWORD = enum.auto()
    SWITCH_KEYWORD = enum.auto()
    TRACE_KEYWORD = enum.auto()
    TRUE_KEYWORD = enum.auto()
    TYPEOF_KEYWORD = enum.auto()
    WHILE_KEYWORD = enum.auto()
    KEYWORD_END = WHILE_KEYWORD + 1

    def __str__(self) -> str:
        cls = self.__class__

        if self in range(cls.ABSTRACT_BEGIN, cls.ABSTRACT_END):
            result = "<{}>".format(self.name.lower().replace("_", "-"))
        elif self in range(cls.KEYWORD_BEGIN, cls.KEYWORD_END):
            result = "keyword '{}'".format(self.name.lower()[:-8])
        else:
            assert False, self

        return result


class ExtraTokenType(int):
    @staticmethod
    def __new__(cls, chars: str) -> "ExtraTokenType":
        instance = _CHARS_2_EXTRA_TOKEN_TYPE.get(chars)

        if instance is None:
            assert len(chars) in range(1, 4)
            value = int.from_bytes(chars.encode(), "big") << 8
            instance = super().__new__(cls, value)
            _CHARS_2_EXTRA_TOKEN_TYPE[chars] = instance

        return instance

    def __str__(self) -> str:
        chars = (self >> 8).to_bytes((self.bit_length() - 1) // 8, "big").decode()
        result = "`{}`".format(chars)
        return result


TokenType = typing.Union[BasicTokenType, ExtraTokenType]


class Token:
    __slots__ = (
        "_type",
        "_data",
        "_source_location",
    )

    def __init__(self, type_: TokenType, data: str, source_location: SourceLocation) -> None:
        self._type = type_
        self._data = data
        self._source_location = source_location

    @property
    def type(self) -> TokenType:
        return self._type

    @property
    def data(self) -> str:
        return self._data

    @data.setter
    def data(self, value: str) -> None:
        self._data = value

    @property
    def source_location(self) -> SourceLocation:
        return self._source_location


_CHARS_2_EXTRA_TOKEN_TYPE: typing.Dict[str, ExtraTokenType] = {}
