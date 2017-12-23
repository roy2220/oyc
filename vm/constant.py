__all__ = (
    "ConstantType",
    "ConstantData",
    "Constant",
    "ConstantTable",
    "TooManyConstantsException",
)


import enum
import typing


class ConstantType(enum.IntEnum):
    INTEGER = enum.auto()
    FLOATING_POINT = enum.auto()
    STRING = enum.auto()


ConstantData = typing.Union[int, float, str]


class Constant(typing.NamedTuple):
    type: ConstantType
    data: ConstantData


class ConstantTable:
    __slots__ = (
        "_size",
        "_constants",
        "_integer_2_constant_id",
        "_floating_point_2_constant_id",
        "_string_2_constant_id",
    )

    def __init__(self, size: int) -> None:
        self._size = size
        self._constants = []
        self._integer_2_constant_id = {}
        self._floating_point_2_constant_id = {}
        self._string_2_constant_id = {}

    def add_integer_constant(self, integer: int) -> int:
        constant_id = self._integer_2_constant_id.get(integer, None)

        if constant_id is None:
            constant_id = self._do_add_constant(ConstantType.INTEGER, integer)
            self._integer_2_constant_id[integer] = constant_id

        return constant_id

    def add_floating_point_constant(self, floating_point: float) -> int:
        constant_id = self._floating_point_2_constant_id.get(floating_point, None)

        if constant_id is None:
            constant_id = self._do_add_constant(ConstantType.FLOATING_POINT, floating_point)
            self._floating_point_2_constant_id[floating_point] = constant_id

        return constant_id

    def add_string_constant(self, string: str) -> int:
        constant_id = self._string_2_constant_id.get(string, None)

        if constant_id is None:
            constant_id = self._do_add_constant(ConstantType.STRING, string)
            self._string_2_constant_id[string] = constant_id

        return constant_id

    def get_constant(self, constant_id) -> Constant:
        constant = self._constants[constant_id]
        return constant

    def _do_add_constant(self, constant_type: ConstantType
                              , constant_data: typing.Union[int, float, str]) -> int:
        constant_id = len(self._constants)

        if constant_id == self._size:
            raise TooManyConstantsException()

        self._constants.append(Constant(constant_type, constant_data))
        return constant_id


class TooManyConstantsException(Exception):
    pass
