__all__ = (
    "VariableType",
    "FunctionScope",
)


import enum
import typing

from .capture import *
from .error import LocalVariableExistsError, VariableNotFoundError, StackTooDeepError \
                   , CaptureTableTooLargeError
from .expression import NullaryExpression
from .register import *
from .source_location import SourceLocation


class VariableType(enum.IntEnum):
    LOCAL = enum.auto()
    FOREIGN = enum.auto()


class FunctionScope:
    __slots__ = (
        "_parent",
        "_register_pool",
        "_register_stack",
        "_capture_table",
    )

    def __init__(self, parent: typing.Optional["FunctionScope"], register_pool_size: int
                 , max_capture_table_length: int) -> None:
        self._parent = parent
        self._register_pool = RegisterPool(register_pool_size)
        self._register_stack = RegisterStack(self._register_pool)
        self._capture_table = CaptureTable(max_capture_table_length)

    def create_local_variable(self, variable_name: NullaryExpression) -> int:
        try:
            return self._register_pool.allocate_register(variable_name.data)
        except DuplicateRegisterNameException:
            raise LocalVariableExistsError(variable_name.source_location
                                           , variable_name.data) from None
        except NoMoreRegisterException:
            raise StackTooDeepError(variable_name.source_location) from None

    def get_variable(self, variable_name: str) -> typing.Tuple[VariableType, int]:
        variable_info = self._try_get_variable(variable_name)
        assert variable_info is not None
        return variable_info

    def find_variable(self, variable_name: NullaryExpression) -> typing.Tuple[VariableType, int]:
        variable_info = self._try_get_variable(variable_name.data)

        if variable_info is None:
            if self._parent is None:
                raise VariableNotFoundError(variable_name.source_location, variable_name.data)

            variable_type, variable_id = self._parent.find_variable(variable_name)

            if variable_type is VariableType.LOCAL:
                register_id = variable_id
                self._parent._add_original_capture(register_id)

            capture_id = self._create_foreign_variable(variable_name)
            variable_info = VariableType.FOREIGN, capture_id

        return variable_info

    def get_foreign_variable_names(self) -> typing.List[str]:
        return self._capture_table.get_capture_names()

    def push_target(self, source_location: SourceLocation, register_id: typing.Optional[int] = None) -> int:
        try:
            return self._register_stack.push(register_id)
        except NoMoreRegisterException:
            raise StackTooDeepError(source_location) from None

    def pop_target(self) -> int:
        return self._register_stack.pop()

    def peek_target(self) -> int:
        return self._register_stack.peek()

    def get_max_register_id(self) -> int:
        return self._register_pool.get_max_register_id()

    def get_next_register_id(self) -> int:
        return self._register_pool.get_next_register_id()

    def has_original_captures(self) -> bool:
        return self._register_pool.has_marked_registers()

    def enter_block_scope(self) -> typing.ContextManager[None]:
        return self._register_pool.save()

    def _try_get_variable(self, variable_name: str) -> typing.Optional[typing.Tuple[VariableType
                                                                                    , int]]:
        register_id = self._try_find_local_variable(variable_name)

        if register_id is not None:
            return VariableType.LOCAL, register_id

        capture_id = self._try_find_foreign_variable(variable_name)

        if capture_id is not None:
            return VariableType.FOREIGN, capture_id

        return None

    def _try_find_local_variable(self, variable_name: str) -> typing.Optional[int]:
        try:
            return self._register_pool.find_register(variable_name)
        except RegisterNotFoundException:
            return None

    def _create_foreign_variable(self, variable_name: NullaryExpression) -> int:
        try:
            return self._capture_table.add_capture(variable_name.data)
        except TooManyCapturesException:
            raise CaptureTableTooLargeError(variable_name.source_location)

    def _try_find_foreign_variable(self, variable_name: str) -> typing.Optional[int]:
        try:
            return self._capture_table.find_capture(variable_name)
        except CaptureNotFoundException:
            return None

    def _add_original_capture(self, register_id: int) -> None:
        self._register_pool.mark_register(register_id)
