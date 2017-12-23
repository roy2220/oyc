__all__ = (
    "FunctionPrototype",
    "Opcode",
    "BuiltinFunctionID",
    "ConversionID",
    "SourceLocation",
)


import typing

from .bytecode import *
from compiler.error import BytecodeTooLargeError
from compiler.source_location import SourceLocation


class FunctionPrototype:
    __slots__ = (
        "_number_of_regular_parameters",
        "_number_of_default_parameters",
        "_is_variadic",
        "_bytecode",
        "_instruction_offset_2_source_location",
        "_capture_infos",
        "_number_of_registers",
    )

    def __init__(self, number_of_regular_parameters: int, number_of_default_parameters: int
                 , is_variadic: bool, max_bytecode_length: int) -> None:
        self._number_of_regular_parameters = number_of_regular_parameters
        self._number_of_default_parameters = number_of_default_parameters
        self._is_variadic = is_variadic
        self._bytecode = Bytecode(max_bytecode_length)
        self._instruction_offset_2_source_location = {}
        self._capture_infos = []
        self._number_of_registers = 0

    @property
    def number_of_regular_parameters(self) -> int:
        return self._number_of_regular_parameters

    @property
    def number_of_default_parameters(self) -> int:
        return self._number_of_default_parameters

    @property
    def is_variadic(self) -> bool:
        return self._is_variadic

    def get_next_instruction_offset(self) -> int:
        return self._bytecode.get_next_instruction_offset()

    def add_instruction(self, source_location: SourceLocation, *args, **kwargs) -> int:
        try:
            instruction_offset = self._bytecode.add_instruction(*args, **kwargs)
        except TooManyInstructionsException:
            raise BytecodeTooLargeError(source_location) from None

        self._instruction_offset_2_source_location[instruction_offset] = source_location
        return instruction_offset

    def set_instruction(self, *args, **kwargs):
        return self._bytecode.set_instruction(*args, **kwargs)

    def get_instructions(self, *args, **kwargs):
        return self._bytecode.get_instructions(*args, **kwargs)

    def get_source_location(self, instruction_offset: int) -> SourceLocation:
        return self._instruction_offset_2_source_location[instruction_offset]

    @property
    def capture_infos(self) -> typing.List[typing.Tuple[bool, int]]:
        return self._capture_infos

    @property
    def number_of_registers(self) -> int:
        return self._number_of_registers

    @number_of_registers.setter
    def number_of_registers(self, value: int) -> None:
        self._number_of_registers = value
