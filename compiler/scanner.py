__all__ = (
    "Scanner",
)


import collections
import copy
import io
import itertools
import typing

from . import utils
from .error import EndOfFileError, UnexpectedCharError
from .source_location import SourceLocation
from .token import *


class Scanner:
    __slots__ = (
        "_input_stream",
        "_file_name",
        "_line_number",
        "_column_number",
        "_line_lengths",
        "_char_buffer",
    )

    def __init__(self, input_stream: io.IOBase) -> None:
        self._input_stream = input_stream
        self._file_name = getattr(input_stream, "name", "<unnamed>")
        self._line_number = 1
        self._column_number = 1
        self._line_lengths = []
        self._char_buffer = collections.deque()

    def get_token(self) -> Token:
        char1 = self._peek_char(1)

        if char1 is "":
            return Token(BasicTokenType.NO, "", self.get_source_location())
        elif char1 in utils.WHITE_SPACES:
            return self._get_white_space_token()
        elif char1 in utils.DIGITS:
            return self._get_number_literal_token()
        elif char1 is "\"":
            return self._get_string_literal_token()
        elif char1 is "_" or char1 in utils.LETTERS:
            return self._get_name_token()
        else:
            return self._maybe_get_extra_token()

    def get_source_location(self) -> SourceLocation:
        return SourceLocation(self._file_name, self._line_number, self._column_number)

    def _get_comment_token(self) -> Token:
        char1 = self._peek_char(1)

        if char1 is "/":
            char2 = self._peek_char(2)

            if char2 is "/":
                return self._get_single_line_comment_token()
            elif char2 is "*":
                return self._get_multi_line_comment_token()

        self._unexpect_char(char1)

    def _get_single_line_comment_token(self) -> Token:
        source_location = self.get_source_location()
        token_data = self._get_expected_char(("/",))
        token_data += self._get_expected_char(("/",))

        while True:
            char1 = self._peek_char(1)

            if char1 is "\n":
                break

            token_data += self._get_char()

        return Token(BasicTokenType.COMMENT, token_data, source_location)

    def _get_multi_line_comment_token(self) -> Token:
        source_location = self.get_source_location()
        token_data = self._get_expected_char(("/",))
        token_data += self._get_expected_char(("*",))

        while True:
            char0 = self._get_char()
            token_data += char0

            if char0 is "*":
                char1 = self._peek_char(1)

                if char1 is "/":
                    break

        token_data += self._get_char()
        return Token(BasicTokenType.COMMENT, token_data, source_location)

    def _get_white_space_token(self) -> Token:
        source_location = self.get_source_location()
        token_data = self._get_expected_char(utils.WHITE_SPACES)

        while True:
            char1 = self._peek_char(1)

            if not char1 in utils.WHITE_SPACES:
                break

            token_data += self._get_char()

        return Token(BasicTokenType.WHITE_SPACE, token_data, source_location)

    def _get_number_literal_token(self) -> Token:
        char1 = self._peek_char(1)
        char2 = self._peek_char(2)

        if char1 is "0" and char2 in ("x", "X"):
            return self._get_number_literal_token16()
        else:
            return self._get_number_literal_token10()

    def _get_number_literal_token16(self) -> Token:
        source_location = self.get_source_location()
        token_data = self._get_expected_char(("0",))
        token_data += self._get_expected_char(("x", "X"))
        token_data += self._get_expected_char(utils.HEX_DIGITS)

        while True:
            char1 = self._peek_char(1)

            if not char1 in utils.HEX_DIGITS:
                break

            token_data += self._get_char()

        return Token(BasicTokenType.INTEGER_LITERAL, token_data, source_location)

    def _get_number_literal_token10(self) -> Token:
        source_location = self.get_source_location()
        token_data = ""
        token_type = BasicTokenType.INTEGER_LITERAL

        while True:
            char1 = self._peek_char(1)

            if not char1 in utils.DIGITS:
                break

            token_data += self._get_char()

        if char1 is ".":
            token_type =  BasicTokenType.FLOATING_POINT_LITERAL
            token_data += self._get_char()

            if len(token_data) == 1:
                token_data += self._get_expected_char(utils.DIGITS)

            while True:
                char1 = self._peek_char(1)

                if not char1 in utils.DIGITS:
                    break

                token_data += self._get_char()
        else:
            if len(token_data) == 0:
                self._unexpect_char(char1)

        if char1 in ("e", "E"):
            token_type =  BasicTokenType.FLOATING_POINT_LITERAL
            token_data += self._get_char()
            char1 = self._peek_char(1)

            if char1 in ("+", "-"):
                token_data += self._get_char()

            token_data += self._get_expected_char(utils.DIGITS)

            while True:
                char1 = self._peek_char(1)

                if not char1 in utils.DIGITS:
                    break

                token_data += self._get_char()

        return Token(token_type, token_data, source_location)

    def _get_string_literal_token(self) -> Token:
        source_location = self.get_source_location()
        token_data = self._get_expected_char(("\"",))

        while True:
            char1 = self._peek_char(1)

            if char1 is "\"":
                break

            if char1 is "\n":
                self._unexpect_char(char1)

            if char1 is "\\":
                token_data += self._get_escape_sequence()
            else:
                token_data += self._get_char()

        token_data += self._get_char()
        return Token(BasicTokenType.STRING_LITERAL, token_data, source_location)

    def _get_escape_sequence(self) -> str:
        escape_sequence = self._get_expected_char(("\\",))
        char1 = self._peek_char(1)

        if "\\" + char1 in utils.SIMPLE_ESCAPE_SEQUENCES:
            escape_sequence += self._get_char()
        elif char1 in utils.OCTAL_DIGITS:
            escape_sequence += self._get_char()
            escape_sequence += self._get_expected_char(utils.OCTAL_DIGITS)
            escape_sequence += self._get_expected_char(utils.OCTAL_DIGITS)
        elif char1 in ("x", "X"):
            escape_sequence += self._get_char()
            escape_sequence += self._get_expected_char(utils.HEX_DIGITS)
            escape_sequence += self._get_expected_char(utils.HEX_DIGITS)
        else:
            self._unexpect_char(char1)

        return escape_sequence

    def _get_name_token(self) -> Token:
        source_location = self.get_source_location()
        token_data = self._get_expected_char(itertools.chain(("_",), utils.LETTERS))

        while True:
            char1 = self._peek_char(1)

            if not (char1 is "_" or char1 in utils.LETTERS or char1 in utils.DIGITS):
                break

            token_data += self._get_char()

        token_type = _KEYWORD_2_BASIC_TOKEN_TYPE.get(token_data, BasicTokenType.IDENTIFIER)
        return Token(token_type, token_data, source_location)

    def _maybe_get_extra_token(self) -> Token:
        char1 = self._peek_char(1)

        if char1 == "/":
            char2 = self._peek_char(2)

            if char2 in ("/", "*"):
                return self._get_comment_token()

            source_location = self.get_source_location()
            token_data = self._get_char()
            char1 = char2

            if char1 is "=":
                token_data += self._get_char()
        elif char1 is ".":
            char2 = self._peek_char(2)

            if char2 in utils.DIGITS:
                return self._get_number_literal_token()

            source_location = self.get_source_location()
            token_data = self._get_char()
            char1 = char2
            char2 = self._peek_char(2)

            if char1 is "." and char2 is ".":
                token_data += self._get_char()
                token_data += self._get_char()
        elif char1 in ("<", ">"):
            source_location = self.get_source_location()
            char0 = self._get_char()
            token_data = char0
            char1 = self._peek_char(1)

            if char1 is char0:
                token_data += self._get_char()
                char1 = self._peek_char(1)

            if char1 is "=":
                token_data += self._get_char()
        elif char1 in ("+", "-", "&", "|"):
            source_location = self.get_source_location()
            char0 = self._get_char()
            token_data = char0
            char1 = self._peek_char(1)

            if char1 in (char0, "="):
                token_data += self._get_char()
        elif char1 in ("*", "%", "^", "=", "!"):
            source_location = self.get_source_location()
            token_data = self._get_char()
            char1 = self._peek_char(1)

            if char1 is "=":
                token_data += self._get_char()
        elif char1 in ("~", ",", ":", ";", "?", "(", ")", "[", "]", "{", "}"):
            source_location = self.get_source_location()
            token_data = self._get_char()
        else:
            self._unexpect_char(char1)

        return Token(ExtraTokenType(token_data), token_data, source_location)

    def _get_expected_char(self, expected_chars: typing.Iterable[str]) -> str:
        char = self._get_char()

        if not char in expected_chars:
            self._unget_char(char)
            self._unexpect_char(char)

        return char

    def _get_char(self) -> str:
        if len(self._char_buffer) == 0:
            char = self._do_get_char()

            if char is "":
                raise EndOfFileError(self.get_source_location())
        else:
            char = self._char_buffer.popleft()

        if char is "\n":
            self._line_lengths.append(self._column_number - 1)
            self._line_number += 1
            self._column_number = 1
        else:
            self._column_number += 1

        return char

    def _do_get_char(self) -> str:
        char = self._input_stream.read(1)
        return char

    def _unget_char(self, char: str) -> None:
        if char is "\n":
            self._line_number -= 1
            self._column_number = self._line_lengths.pop() + 1
        else:
            self._column_number -= 1

        self._char_buffer.append(char)

    def _peek_char(self, position: int) -> str:
        assert position >= 1

        while len(self._char_buffer) < position:
            char = self._do_get_char()

            if char is "":
                return char

            self._char_buffer.append(char)

        char = self._char_buffer[position - 1]
        return char

    def _unexpect_char(self, char: str) -> typing.NoReturn:
        raise UnexpectedCharError(self.get_source_location(), char)


_KEYWORD_2_BASIC_TOKEN_TYPE: typing.Dict[str, BasicTokenType] = {
    "auto": BasicTokenType.AUTO_KEYWORD,
    "bool": BasicTokenType.BOOL_KEYWORD,
    "break": BasicTokenType.BREAK_KEYWORD,
    "case": BasicTokenType.CASE_KEYWORD,
    "continue": BasicTokenType.CONTINUE_KEYWORD,
    "default": BasicTokenType.DEFAULT_KEYWORD,
    "delete": BasicTokenType.DELETE_KEYWORD,
    "do": BasicTokenType.DO_KEYWORD,
    "else": BasicTokenType.ELSE_KEYWORD,
    "false": BasicTokenType.FALSE_KEYWORD,
    "float": BasicTokenType.FLOAT_KEYWORD,
    "for": BasicTokenType.FOR_KEYWORD,
    "foreach": BasicTokenType.FOREACH_KEYWORD,
    "if": BasicTokenType.IF_KEYWORD,
    "int": BasicTokenType.INT_KEYWORD,
    "null": BasicTokenType.NULL_KEYWORD,
    "require": BasicTokenType.REQUIRE_KEYWORD,
    "return": BasicTokenType.RETURN_KEYWORD,
    "sizeof": BasicTokenType.SIZEOF_KEYWORD,
    "str": BasicTokenType.STR_KEYWORD,
    "struct": BasicTokenType.STRUCT_KEYWORD,
    "switch": BasicTokenType.SWITCH_KEYWORD,
    "trace": BasicTokenType.TRACE_KEYWORD,
    "true": BasicTokenType.TRUE_KEYWORD,
    "typeof": BasicTokenType.TYPEOF_KEYWORD,
    "while": BasicTokenType.WHILE_KEYWORD,
}

assert len(_KEYWORD_2_BASIC_TOKEN_TYPE) == BasicTokenType.KEYWORD_END - BasicTokenType.KEYWORD_BEGIN
