__all__ = (
    "Executable",
    "ConstantType",
    "ConstantData",
    "Constant",
)


from .constant import *
from .function_prototype import FunctionPrototype, SourceLocation
from compiler.error import ConstantTableTooLargeError


class Executable:
    def __init__(self, max_constant_table_length: int) -> None:
        self._function_prototypes = []
        self._constant_table = ConstantTable(max_constant_table_length)

    def add_function_prototype(self, function_prototype: FunctionPrototype) -> int:
        function_prototype_id = len(self._function_prototypes)
        self._function_prototypes.append(function_prototype)
        return function_prototype_id

    def get_function_prototype(self, function_prototype_id: int) -> FunctionPrototype:
        assert function_prototype_id in range(0, len(self._function_prototypes))
        return self._function_prototypes[function_prototype_id]

    def add_integer_constant(self, source_location: SourceLocation, *args, **kwargs) -> int:
        try:
            return self._constant_table.add_integer_constant(*args, **kwargs)
        except TooManyConstantsException:
            raise ConstantTableTooLargeError(source_location) from None

    def add_floating_point_constant(self, source_location: SourceLocation, *args, **kwargs) -> int:
        try:
            return self._constant_table.add_floating_point_constant(*args, **kwargs)
        except TooManyConstantsException:
            raise ConstantTableTooLargeError(source_location) from None

    def add_string_constant(self, source_location: SourceLocation, *args, **kwargs) -> int:
        try:
            return self._constant_table.add_string_constant(*args, **kwargs)
        except TooManyConstantsException:
            raise ConstantTableTooLargeError(source_location) from None

    def get_constant(self, *args, **kwargs):
        return self._constant_table.get_constant(*args, **kwargs)
