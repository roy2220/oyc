__all__ = (
    "Opcode",
    "Bytecode",
    "BuiltinFunctionID",
    "ConversionID",
    "TooManyInstructionsException",
)


import collections
import enum
import typing


class Opcode(enum.IntEnum):
    NO = 0

    LOAD_VOID = enum.auto()
    LOAD_NULL = enum.auto()
    LOAD_BOOLEAN = enum.auto()
    LOAD_INTEGER = enum.auto()
    LOAD_CONSTANT = enum.auto()
    LOAD_BUILTIN_FUNCTION = enum.auto()

    MOVE = enum.auto()
    CONVERT = enum.auto()

    GET_CAPTURE = enum.auto()
    SET_CAPTURE = enum.auto()
    GET_SLOT = enum.auto()
    SET_SLOT = enum.auto()
    CLEAR_SLOT = enum.auto()

    NEGATE = enum.auto()
    ADD = enum.auto()
    SUBSTRATE = enum.auto()
    MULTIPLY = enum.auto()
    DIVIDE = enum.auto()
    MODULO = enum.auto()

    LOGICAL_AND = enum.auto()
    LOGICAL_OR = enum.auto()
    LOGICAL_NOT = enum.auto()

    BITWISE_AND = enum.auto()
    BITWISE_OR = enum.auto()
    BITWISE_XOR = enum.auto()
    BITWISE_NOT = enum.auto()
    BITWISE_SHIFT_LEFT = enum.auto()
    BITWISE_SHIFT_RIGHT = enum.auto()

    EQUAL = enum.auto()
    NOT_EQUAL = enum.auto()
    LESS = enum.auto()
    NOT_LESS = enum.auto()
    GREATER = enum.auto()
    NOT_GREATER = enum.auto()

    JUMP = enum.auto()
    JUMP_IF_TRUE = enum.auto()
    JUMP_IF_FALSE = enum.auto()

    NEW_ARRAY = enum.auto()
    NEW_STRUCTURE = enum.auto()

    NEW_CLOSURE = enum.auto()
    KILL_ORIGINAL_CAPTURES = enum.auto()
    CALL = enum.auto()
    RETURN = enum.auto()

    NEW_ITERATOR = enum.auto()
    ITERATE = enum.auto()


class Bytecode:
    __slots__ = (
        "_max_length",
        "_instructions",
    )

    def __init__(self, max_length) -> None:
        self._max_length = max_length
        self._instructions = bytearray()

    def get_next_instruction_offset(self) -> int:
        return len(self._instructions)

    def add_instruction(self, opcode: Opcode, *, operand1: int = 0, operand2: int = 0
                        , operand3: int = 0, operand4: typing.Optional[int] = None) -> int:
        instruction_offset = len(self._instructions)
        self._instructions.append(operand1)
        self._instructions.append(operand2)
        self._instructions.append(operand3)

        if operand4 is None:
            self._instructions.append(opcode.value)
        else:
            self._instructions.append(opcode.value | 128)
            self._instructions.extend(operand4.to_bytes(4, "little", signed = True))

        if len(self._instructions) > self._max_length:
            del self._instructions[instruction_offset:]
            raise TooManyInstructionsException()

        return instruction_offset

    def set_instruction(self, instruction_offset: int, *, operand1: typing.Optional[int] = None
                        , operand2: typing.Optional[int] = None
                        , operand3: typing.Optional[int] = None
                        , operand4: typing.Optional[int] = None) -> None:
        if operand1 is not None:
            self._instructions[instruction_offset] = operand1

        if operand2 is not None:
            self._instructions[instruction_offset + 1] = operand2

        if operand3 is not None:
            self._instructions[instruction_offset + 2] = operand3

        if operand4 is not None:
            assert self._instructions[instruction_offset + 3] & 128 != 0
            self._instructions[instruction_offset + 4
                               : instruction_offset + 8] = operand4.to_bytes(4, "little"
                                                                             , signed = True)

    def get_instructions(self, next_instruction_offset: int) \
        -> typing.Iterable[typing.Tuple[int, Opcode, int, int, int, typing.Optional[int]]]:

        while next_instruction_offset < len(self._instructions):
            instruction_offset = next_instruction_offset
            operand1 = self._instructions[instruction_offset]
            operand2 = self._instructions[instruction_offset + 1]
            operand3 = self._instructions[instruction_offset + 2]
            byte = self._instructions[instruction_offset + 3]

            if byte & 128 == 0:
                opcode = Opcode(byte)
                operand4 = None
                next_instruction_offset += 4
            else:
                opcode = Opcode(byte & ~128)
                operand4 = int.from_bytes(self._instructions[instruction_offset + 4
                                                             : instruction_offset + 8], "little"
                                          , signed = True)
                next_instruction_offset += 8

            yield instruction_offset, opcode, operand1, operand2, operand3, operand4


class TooManyInstructionsException(Exception):
    pass


def BuiltinFunctionID():
    cls = collections.namedtuple("BuiltinFunctionID", (
        "TRACE",
        "REQUIRE",
    ))

    return cls._make(range(len(cls._fields)))

BuiltinFunctionID = BuiltinFunctionID()

def ConversionID():
    cls = collections.namedtuple("ConversionID", (
        "BOOL",
        "INT",
        "FLOAT",
        "STR",
        "SIZEOF",
        "TYPEOF",
    ))

    return cls._make(range(len(cls._fields)))

ConversionID = ConversionID()
