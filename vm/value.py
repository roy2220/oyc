__slots__ = (
    "ValueType",
    "Capture",
    "Closure",
    "BuiltinFunction",
    "Iterator",
    "ValueData",
    "Value",
)


import enum
import typing

from . executable import Executable
from . function_prototype import FunctionPrototype, SourceLocation


class ValueType(enum.IntEnum):
    VOID = enum.auto()
    NULL = enum.auto()
    BOOLEAN = enum.auto()
    INTEGER = enum.auto()
    FLOATING_POINT = enum.auto()
    STRING = enum.auto()
    ARRAY = enum.auto()
    STRUCTURE = enum.auto()
    CLOSURE = enum.auto()
    BUILTIN_FUNCTION = enum.auto()
    ITERATOR = enum.auto()

    def __str__(self) -> str:
        return _VALUE_TYPE_2_NAME[self]


class Capture:
    def __init__(self, value: "Value") -> None:
        self._value = value

    @property
    def value(self) -> "Value":
        return self._value

    @value.setter
    def value(self, value: "Value") -> None:
        self._value = value


class Closure(typing.NamedTuple):
    executable: Executable
    function_prototype_id: int
    default_arguments: typing.List["Value"]
    captures: typing.List[Capture]

    def get_function_prototype(self) -> FunctionPrototype:
        return self.executable.get_function_prototype(self.function_prototype_id)


class BuiltinFunction:
    __slots__ = (
        "_impl"
    )

    def __init__(self, impl: typing.Callable[[typing.Any, SourceLocation, int, typing.List["Value"]]
                                             , "Value"]) -> None:
        self._impl = impl

    def __call__(self, context, source_location: SourceLocation, stack_base: int
                 , arguments: typing.List["Value"]) -> "Value":
        return self._impl(context, source_location, stack_base, arguments)


class Iterator:
    __slots__ = (
        "_impl",
        "_buffer",
    )

    def __init__(self, impl: typing.Iterator[typing.Tuple["Value", "Value"]]) -> None:
        self._impl = impl
        self._buffer = []

    def __bool__(self) -> bool:
        try:
            key, value = next(self._impl)
        except StopIteration:
            return False
        else:
            self._buffer.append(key)
            self._buffer.append(value)
            return True

    def __next__(self) -> typing.Tuple["Value", "Value"]:
        if len(self._buffer) == 0:
            raise StopIteration()

        value = self._buffer.pop()
        key = self._buffer.pop()
        return key, value


ValueData = typing.Union[
    None,
    bool,
    int,
    float,
    str,
    typing.List["Value"],
    typing.Dict["ValueData", "Value"],
    Closure,
]


class Value:
    __slots__ = (
        "_type",
        "_data",
    )

    def __init__(self, type_: ValueType, data: ValueData) -> None:
        self._type = type_
        self._data = data

    def set(self, type_: ValueType, data: ValueData) -> None:
        self._type = type_
        self._data = data

    def copy(self) -> "Value":
        return self.__class__(self._type, self._data)

    def assign(self, other: "Value") -> None:
        self.set(other._type, other._data)

    @property
    def type(self) -> ValueType:
        return self._type

    @property
    def data(self) -> ValueData:
        return self._data

    def get_elements(self) -> typing.Iterator[typing.Tuple["Value", "Value"]]:
        assert self._type is ValueType.ARRAY
        array = self._data

        def make_iterator(array):
            for element_index_data, element_value in enumerate(array):
                element_index = Value(ValueType.INTEGER, element_index_data)
                yield element_index, element_value

        return make_iterator(array)

    def get_fields(self) -> typing.Iterator[typing.Tuple["Value", "Value"]]:
        assert self._type is ValueType.STRUCTURE
        structure = self._data

        def make_iterator(structure):
            for field_name_data, field_value in structure.items():
                field_name_type = _VALUE_DATA_TYPE_2_VALUE_TYPE[type(field_name_data)]
                field_name = Value(field_name_type, field_name_data)
                yield field_name, field_value

        return make_iterator(structure)

    def __bool__(self) -> bool:
        assert self._type is not ValueType.VOID

        if self._type is ValueType.NULL:
            return False
        elif self._type is ValueType.BOOLEAN:
            return self.data
        elif self._type in (ValueType.INTEGER, ValueType.FLOATING_POINT):
            return self.data != 0
        elif self._type in (ValueType.STRING, ValueType.ARRAY, ValueType.STRUCTURE):
            return len(self.data) >= 1
        elif self._type is ValueType.ITERATOR:
            return bool(self._data)
        else:
            return True

    def __str__(self) -> str:
        return self._to_string(set())

    def _to_string(self, value_ids: typing.Set[int]) -> str:
        if self._type is ValueType.VOID:
            return ""
        elif self._type is ValueType.NULL:
            return "null"
        elif self._type is ValueType.BOOLEAN:
            return "true" if self.data else "false"
        elif self._type in (ValueType.INTEGER, ValueType.FLOATING_POINT):
            return str(self.data)
        elif self._type is ValueType.STRING:
            return "\"" + self.data + "\""
        elif self._type in (ValueType.ARRAY, ValueType.STRUCTURE):
            value_id = id(self._data)

            if value_id in value_ids:
                return "..."

            value_ids.add(value_id)

            if self._type is ValueType.ARRAY:
                string = "[] {{{}}}".format(", ".join((element_value._to_string(value_ids)
                                                       for element_value in self._data)))
            else:
                string = "struct {{{}}}".format(", ".join(("[{}] = {}".format(
                    field_name._to_string(value_ids),
                    field_value._to_string(value_ids),
                ) for field_name, field_value in self.get_fields())))

            value_ids.remove(value_id)
            return string
        else:
            return "<" + str(self._type) + ">"


_VALUE_TYPE_2_NAME: typing.Dict[ValueType, str] = {
    ValueType.VOID: "void",
    ValueType.NULL: "null",
    ValueType.BOOLEAN: "bool",
    ValueType.INTEGER: "int",
    ValueType.FLOATING_POINT: "float",
    ValueType.STRING: "str",
    ValueType.ARRAY: "array",
    ValueType.STRUCTURE: "struct",
    ValueType.CLOSURE: "closure",
    ValueType.BUILTIN_FUNCTION: "builtin-function",
}

_VALUE_DATA_TYPE_2_VALUE_TYPE: typing.Dict[ValueData, ValueType] = {
    type(None): ValueType.NULL,
    bool: ValueType.BOOLEAN,
    int: ValueType.INTEGER,
    float: ValueType.FLOATING_POINT,
    str: ValueType.STRING,
    list: ValueType.ARRAY,
    dict: ValueType.STRUCTURE,
    Closure: ValueType.CLOSURE,
    BuiltinFunction: ValueType.BUILTIN_FUNCTION,
}
