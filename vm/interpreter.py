__all__ = (
    "Interpreter",
)


import typing

from .error import StackOverflowError \
                   , MissingArgumentError \
                   , TooManyArgumentsError \
                   , IncompatibleOperandTypesError \
                   , IndexOutOfRangeError \
                   , DivideByZeroError
from .executable import *
from .function_prototype import *
from .value import *


class CallFrame(typing.NamedTuple):
    parent: typing.Optional["CallFrame"]
    source_location: SourceLocation
    closure: Closure
    stack_base: int
    register_id_2_original_capture: typing.Dict[int, Capture] = {}


class Interpreter:
    __slots__ = (
        "_max_stack_depth",
        "_stack",
        "_call_frame",
        "_return_value",
        "_builtin_require_impl",
    )

    def __init__(self, max_stack_depth: int
                 , builtin_require_impl: typing.Callable[["Interpreter", int, typing.List[Value]]
                                                         , Value]) -> None:
        self._max_stack_depth = max_stack_depth
        self._stack = []
        self._call_frame = None
        self._return_value = None
        self._builtin_require_impl = builtin_require_impl

    def run(self, source_location: SourceLocation, executable: Executable, stack_base: int
            , arguments: typing.List[Value]) -> Value:
        closure = self._make_closure(executable, 0, [])
        self._reserve_stack(source_location, stack_base, len(arguments))

        for i, argument in enumerate(arguments):
            stack_pos = stack_base + i
            self._stack[stack_pos].assign(argument)

        return self._call_closure(source_location, closure, stack_base, len(arguments))

    def get_stack_trace(self) -> typing.List[SourceLocation]:
        stack_trace = []
        call_frame = self._call_frame

        while call_frame is not None:
            stack_trace.append(call_frame.source_location)
            call_frame = call_frame.parent

        return stack_trace

    def _reserve_stack(self, source_location: SourceLocation, stack_base: int
                       , relative_stack_depth: int) -> None:
        stack_depth = stack_base + relative_stack_depth

        if stack_depth > self._max_stack_depth:
            raise StackOverflowError(source_location)

        for _ in range(len(self._stack), stack_depth):
            self._stack.append(Value(ValueType.VOID, None))

    def _free_stack(self, stack_base: int, relative_stack_depth: int) -> None:
        for stack_pos in range(stack_base, stack_base + relative_stack_depth):
            self._stack[stack_pos].set(ValueType.VOID, None)

    def _make_closure(self, executable: Executable, function_prototype_id: int
                      , default_arguments: typing.List[Value]) -> Closure:
        function_prototype = executable.get_function_prototype(function_prototype_id)
        default_arguments = [default_argument.copy() for default_argument in default_arguments]
        captures = []

        for capture_is_original, register_id_or_capture_id \
            in function_prototype.capture_infos:

            if capture_is_original:
                register_id = register_id_or_capture_id
                capture = self._call_frame.register_id_2_original_capture.get(register_id)

                if capture is None:
                    stack_pos = self._call_frame.stack_base + register_id
                    value = self._stack[stack_pos]
                    capture = Capture(value)
                    self._call_frame.register_id_2_original_capture[register_id] = capture
            else:
                capture_id = register_id_or_capture_id
                capture = self._call_frame.closure.captures[capture_id]

            captures.append(capture)

        return Closure(executable, function_prototype_id, default_arguments, captures)

    def _call_closure(self, source_location: SourceLocation, closure: Closure, stack_base: int
                      , number_of_arguments: int) -> Value:
        function_prototype = closure.get_function_prototype()

        if number_of_arguments < function_prototype.number_of_regular_parameters:
            raise MissingArgumentError(source_location)

        number_of_parameters = function_prototype.number_of_regular_parameters \
                               + function_prototype.number_of_default_parameters

        if not function_prototype.is_variadic \
           and number_of_arguments > number_of_parameters:
            raise TooManyArgumentsError(source_location)

        self._reserve_stack(source_location, stack_base, function_prototype.number_of_registers)

        for i in range(number_of_arguments, number_of_parameters):
            stack_pos = stack_base + i
            default_argument = closure.default_arguments\
                               [i - function_prototype.number_of_regular_parameters]
            self._stack[stack_pos].assign(default_argument)

        if function_prototype.is_variadic:
            rest_arguments = []

            for i in range(number_of_parameters, number_of_arguments):
                stack_pos = stack_base + i
                rest_arguments.append(self._stack[stack_pos].copy())

            stack_pos = stack_base + number_of_parameters
            self._stack[stack_pos].set(ValueType.ARRAY, rest_arguments)

        call_frame = CallFrame(self._call_frame, source_location, closure, stack_base)
        backup = self._call_frame
        self._call_frame = call_frame
        self._execute_instructions()
        self._call_frame = backup
        return_value = self._return_value.copy()

        for capture in call_frame.register_id_2_original_capture.values():
            capture.value = capture.value.copy()

        self._free_stack(stack_base, function_prototype.number_of_registers)
        return return_value

    def _execute_instructions(self) -> None:
        function_prototype = self._call_frame.closure.get_function_prototype()
        next_instruction_offset = 0

        while True:
            for instruction_offset, opcode, operand1, operand2, operand3, operand4 \
                in function_prototype.get_instructions(next_instruction_offset):
                next_instruction_offset = _INSTRUCTION_EXECUTORS[opcode](self, instruction_offset
                                                                         , operand1, operand2
                                                                         , operand3, operand4)

                if next_instruction_offset is not None:
                    break
            else:
                break

    def _execute_no(self, instruction_offset: int, operand1: int, operand2: int
                    , operand3: int, operand4: None) -> None:
        pass

    def _execute_load_void(self, instruction_offset: int, operand1: int, operand2: int
                           , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        value.set(ValueType.VOID, None)

    def _execute_load_null(self, instruction_offset: int, operand1: int, operand2: int
                           , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        value.set(ValueType.NULL, None)

    def _execute_load_boolean(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        value.set(ValueType.BOOLEAN, operand2 != 0)

    def _execute_load_integer(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, operand4: int) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        integer = operand4
        value.set(ValueType.INTEGER, integer)

    def _execute_load_constant(self, instruction_offset: int, operand1: int, operand2: int
                               , operand3: int, operand4: int) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        constant_id = operand4
        constant = self._call_frame.closure.executable.get_constant(constant_id)
        value.set(_CONSTANT_TYPE_2_VALUE_TYPE[constant.type], constant.data)

    def _execute_load_builtin_function(self, instruction_offset: int, operand1: int, operand2: int
                                       , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        function_prototype_id = operand2
        builtin_function = _BUILTIN_FUNCTIONS[function_prototype_id]
        value.set(ValueType.BUILTIN_FUNCTION, builtin_function)

    def _execute_move(self, instruction_offset: int, operand1: int, operand2: int
                      , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]

        if value2.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type])

        value1.assign(value2)

    def _execute_convert(self, instruction_offset: int, operand1: int, operand2: int
                         , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        conversion_id = operand3

        if not _CONVERTERS[conversion_id](self, value2, value1):
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type])

    def _execute_get_capture(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: int) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        capture_id = operand4
        capture = self._call_frame.closure.captures[capture_id]

        if capture.value.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [capture.value.type])

        value.assign(capture.value)

    def _execute_set_capture(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: int) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        capture_id = operand4
        capture = self._call_frame.closure.captures[capture_id]

        if value.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value.type])

        capture.value.assign(value)

    def _execute_get_slot(self, instruction_offset: int, operand1: int, operand2: int
                          , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        container = self._stack[self._call_frame.stack_base + operand2]
        key = self._stack[self._call_frame.stack_base + operand3]

        if container.type not in (ValueType.STRING, ValueType.ARRAY, ValueType.STRUCTURE):
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [container.type])

        if container.type in (ValueType.STRING, ValueType.ARRAY):
            if key.type is not ValueType.INTEGER:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [key.type])

            if container.type is ValueType.STRING:
                string = container.data
                char_index = key.data

                if char_index in range(0, len(string)):
                    char = string[char_index]
                    value.set(ValueType.STRING, char)
                else:
                    value.set(ValueType.VOID, None)
            else:
                array = container.data
                element_index = key.data

                if element_index in range(0, len(array)):
                    element_value = array[element_index]
                    value.assign(element_value)
                else:
                    value.set(ValueType.VOID, None)
        else:
            if key.type is ValueType.VOID:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [key.type])

            structure = container.data
            field_name = key.data
            field_value = structure.get(field_name)

            if field_value is None:
                value.set(ValueType.VOID, None)
            else:
                value.assign(field_value)

    def _execute_set_slot(self, instruction_offset: int, operand1: int, operand2: int
                          , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        container = self._stack[self._call_frame.stack_base + operand2]
        key = self._stack[self._call_frame.stack_base + operand3]

        if container.type not in (ValueType.ARRAY, ValueType.STRUCTURE):
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [container.type])

        if container.type is ValueType.ARRAY:
            if key.type is not ValueType.INTEGER:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [key.type])

            if value.type is ValueType.VOID:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value.type])

            array = container.data
            element_index = key.data

            if element_index not in range(0, len(array) + 1):
                raise IndexOutOfRangeError(self._get_source_location(instruction_offset))

            if element_index == len(array):
                array.append(value.copy())
            else:
                array[element_index] = value.copy()
        else:
            if key.type not in range(ValueType.NULL, ValueType.STRING + 1):
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [key.type])

            if value.type is ValueType.VOID:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value.type])

            structure = container.data
            field_name = key.data
            structure[field_name] = value.copy()

    def _execute_clear_slot(self, instruction_offset: int, operand1: int, operand2: int
                            , operand3: int, operand4: None) -> None:
        container = self._stack[self._call_frame.stack_base + operand2]
        key = self._stack[self._call_frame.stack_base + operand3]

        if container.type not in (ValueType.ARRAY, ValueType.STRUCTURE):
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [container.type])

        if container.type is ValueType.ARRAY:
            if key.type is not ValueType.INTEGER:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [key.type])

            array = container.data
            element_index = key.data

            if element_index not in range(0, len(array) + 1):
                raise IndexOutOfRangeError(self._get_source_location(instruction_offset))

            del array[element_index:]
        else:
            if key.type is ValueType.VOID:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [key.type])

            structure = container.data
            field_name = key.data
            structure.pop(field_name, None)

    def _execute_negate(self, instruction_offset: int, operand1: int, operand2: int
                        , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand1]

        if value2.type not in (ValueType.INTEGER, ValueType.FLOATING_POINT):
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type])

        value1.set(value2.type, -value2.data)

    def _execute_add(self, instruction_offset: int, operand1: int, operand2: int
                     , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        value3 = self._stack[self._call_frame.stack_base + operand3]

        if value2.type is ValueType.STRING:
            if value3.type is not value2.type:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value2.type, value3.type])

            value1.set(value2.type, value2.data + value3.data)
        else:
            if value2.type not in (ValueType.INTEGER, ValueType.FLOATING_POINT):
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value2.type, value3.type])

            if value3.type not in (ValueType.INTEGER, ValueType.FLOATING_POINT):
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value2.type, value3.type])

            if value2.type is value3.type:
                value1.set(value2.type, value2.data + value3.data)
            else:
                value1.set(ValueType.FLOATING_POINT, value2.data + value3.data)

    def _execute_instruction1(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, f: typing.Callable[[typing.Union[int, float]
                                                                  , typing.Union[int, float]]
                                                                  , typing.Union[int, float]]) \
                              -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        value3 = self._stack[self._call_frame.stack_base + operand3]

        if value2.type not in (ValueType.INTEGER, ValueType.FLOATING_POINT):
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        if value3.type not in (ValueType.INTEGER, ValueType.FLOATING_POINT):
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        if value2.type is value3.type:
            value1.set(value2.type, f(value2.data, value3.data))
        else:
            value1.set(ValueType.FLOATING_POINT, f(value2.data, value3.data))

    def _execute_substrate(self, instruction_offset: int, operand1: int, operand2: int
                           , operand3: int, operand4: None) -> None:
        self._execute_instruction1(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x - y)

    def _execute_multiply(self, instruction_offset: int, operand1: int, operand2: int
                         , operand3: int, operand4: None) -> None:
        self._execute_instruction1(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x * y)

    def _execute_divide(self, instruction_offset: int, operand1: int, operand2: int, operand3: int
                        , operand4: None) -> None:
        def f(x, y):
            if y == 0:
                raise DivideByZeroError(self._get_source_location(instruction_offset))

            if type(x) is int and type(y) is int:
                return x // y
            else:
                return x / y

        self._execute_instruction1(instruction_offset, operand1, operand2, operand3, f)

    def _execute_modulo(self, instruction_offset: int, operand1: int, operand2: int, operand3: int
                        , operand4: None) -> None:
        self._execute_instruction1(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x % y)

    def _execute_instruction2(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, f: typing.Callable[[bool, bool], bool]) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        value3 = self._stack[self._call_frame.stack_base + operand3]

        if value2.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        if value3.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        value1.set(ValueType.BOOLEAN, f(bool(value2), bool(value3)))

    def _execute_logical_and(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: None) -> None:
        self._execute_instruction2(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x and y)

    def _execute_logical_or(self, instruction_offset: int, operand1: int, operand2: int
                            , operand3: int, operand4: None) -> None:
        self._execute_instruction2(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x or y)

    def _execute_logical_not(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]

        if value2.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type])

        value1.set(ValueType.BOOLEAN, not bool(value2))

    def _execute_instruction3(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, f: typing.Callable[[int, int], int]) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        value3 = self._stack[self._call_frame.stack_base + operand3]

        if value2.type is not ValueType.INTEGER:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        if value3.type is not ValueType.INTEGER:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        value1.set(ValueType.INTEGER, f(value2.data, value3.data))

    def _execute_bitwise_and(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: None) -> None:
        self._execute_instruction3(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x & y)

    def _execute_bitwise_or(self, instruction_offset: int, operand1: int, operand2: int
                            , operand3: int, operand4: None) -> None:
        self._execute_instruction3(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x | y)

    def _execute_bitwise_xor(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: None) -> None:
        self._execute_instruction3(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x ^ y)

    def _execute_bitwise_not(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand1]

        if value2.type is not ValueType.INTEGER:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type])

        value1.set(ValueType.INTEGER, ~value2.data)

    def _execute_bitwise_shift_left(self, instruction_offset: int, operand1: int, operand2: int
                                    , operand3: int, operand4: None) -> None:
        self._execute_instruction3(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x << y)

    def _execute_bitwise_shift_right(self, instruction_offset: int, operand1: int, operand2: int
                                     , operand3: int, operand4: None) -> None:
        self._execute_instruction3(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x >> y)

    def _execute_instruction4(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, f: typing.Callable[[bool], bool]) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        value3 = self._stack[self._call_frame.stack_base + operand3]

        if value2.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        if value3.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type, value3.type])

        if value2.type is value2.type:
            if value2.type is ValueType.NULL:
                value1.set(ValueType.BOOLEAN, f(True))
            elif value2.type in (ValueType.INTEGER, ValueType.FLOATING_POINT, ValueType.STRING):
                value1.set(ValueType.BOOLEAN, f(value2.data == value3.data))
            else:
                value1.set(ValueType.BOOLEAN, f(False))
        else:
            value1.set(ValueType.BOOLEAN, f(False))

    def _execute_equal(self, instruction_offset: int, operand1: int, operand2: int
                       , operand3: int, operand4: None) -> None:
        self._execute_instruction4(instruction_offset, operand1, operand2, operand3
                                   , lambda x: x)

    def _execute_not_equal(self, instruction_offset: int, operand1: int, operand2: int
                           , operand3: int, operand4: None) -> None:
        self._execute_instruction4(instruction_offset, operand1, operand2, operand3
                                   , lambda x: not x)

    def _execute_instruction5(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, f: typing.Callable[[typing.Union[int, float, str]
                                                                  , typing.Union[int, float, str]]
                                                                  , bool]) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        value3 = self._stack[self._call_frame.stack_base + operand3]

        if value2.type is ValueType.STRING:
            if value3.type is not value2.type:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value2.type, value3.type])
        else:
            if value2.type not in (ValueType.INTEGER, ValueType.FLOATING_POINT):
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value2.type, value3.type])

            if value3.type not in (ValueType.INTEGER, ValueType.FLOATING_POINT):
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [value2.type, value3.type])

        value1.set(ValueType.BOOLEAN, f(value2.data, value3.data))

    def _execute_less(self, instruction_offset: int, operand1: int, operand2: int
                      , operand3: int, operand4: None) -> None:
        self._execute_instruction5(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x < y)

    def _execute_not_less(self, instruction_offset: int, operand1: int, operand2: int
                          , operand3: int, operand4: None) -> None:
        self._execute_instruction5(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x >= y)

    def _execute_greater(self, instruction_offset: int, operand1: int, operand2: int
                         , operand3: int, operand4: None) -> None:
        self._execute_instruction5(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x > y)

    def _execute_not_greater(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: None) -> None:
        self._execute_instruction5(instruction_offset, operand1, operand2, operand3
                                   , lambda x, y: x <= y)

    def _execute_jump(self, instruction_offset: int, operand1: int, operand2: int
                      , operand3: int, operand4: int) -> int:
        instruction_offset = operand4
        return instruction_offset

    def _execute_instruction6(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, operand4: int
                              , f: typing.Callable[[bool], bool]) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        instruction_offset = operand4

        if value.type is ValueType.VOID:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value.type])

        if f(bool(value)):
            return instruction_offset
        else:
            return None

    def _execute_jump_if_true(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, operand4: int) -> typing.Optional[int]:
        return self._execute_instruction6(instruction_offset, operand1, operand2, operand3
                                          , operand4, lambda x: x)

    def _execute_jump_if_false(self, instruction_offset: int, operand1: int, operand2: int
                               , operand3: int, operand4: int) -> typing.Optional[int]:
        return self._execute_instruction6(instruction_offset, operand1, operand2, operand3
                                          , operand4, lambda x: not x)

    def _execute_new_array(self, instruction_offset: int, operand1: int, operand2: int
                           , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        value.set(ValueType.ARRAY, [])

    def _execute_new_structure(self, instruction_offset: int, operand1: int, operand2: int
                               , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        value.set(ValueType.STRUCTURE, {})

    def _execute_new_closure(self, instruction_offset: int, operand1: int, operand2: int
                             , operand3: int, operand4: int) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        default_arguments = self._stack[self._call_frame.stack_base + operand2
                                        : self._call_frame.stack_base + operand3]
        function_prototype_id = operand4

        for default_argument in default_arguments:
            if default_argument.type is ValueType.VOID:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [default_argument.type])

        closure = self._make_closure(self._call_frame.closure.executable, function_prototype_id
                                     , default_arguments)
        value.set(ValueType.CLOSURE, closure)

    def _execute_call(self, instruction_offset: int, operand1: int, operand2: int
                      , operand3: int, operand4: None) -> None:
        value = self._stack[self._call_frame.stack_base + operand1]
        stack_base = self._call_frame.stack_base + operand2 + 1
        callee = self._stack[stack_base - 1]
        arguments = self._stack[stack_base : self._call_frame.stack_base + operand3]

        for argument in arguments:
            if argument.type is ValueType.VOID:
                raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                    , [argument.type])

        if callee.type is ValueType.CLOSURE:
            return_value = self._call_closure(self._get_source_location(instruction_offset)
                                              , callee.data, stack_base, len(arguments))
        elif callee.type is ValueType.BUILTIN_FUNCTION:
            return_value = callee.data(self, self._get_source_location(instruction_offset)
                                       , stack_base, arguments)
        else:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [callee.type])

        value.assign(return_value)

    def _execute_return(self, instruction_offset: int, operand1: int, operand2: int
                        , operand3: int, operand4: None) -> int:
        value = self._stack[self._call_frame.stack_base + operand1]
        self._return_value = value.copy()
        return self._call_frame.closure.get_function_prototype().get_next_instruction_offset()

    def _execute_new_iterator(self, instruction_offset: int, operand1: int, operand2: int
                              , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]

        if value2.type is ValueType.ARRAY:
            iterator = Iterator(value2.get_elements())
        elif value2.type is ValueType.STRUCTURE:
            iterator = Iterator(value2.get_fields())
        else:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value2.type])

        value1.set(ValueType.ITERATOR, iterator)

    def _execute_iterate(self, instruction_offset: int, operand1: int, operand2: int
                         , operand3: int, operand4: None) -> None:
        value1 = self._stack[self._call_frame.stack_base + operand1]
        value2 = self._stack[self._call_frame.stack_base + operand2]
        value3 = self._stack[self._call_frame.stack_base + operand3]

        if value3.type is not ValueType.ITERATOR:
            raise IncompatibleOperandTypesError(self._get_source_location(instruction_offset)
                                                , [value3.type])

        key, value = next(value3.data)
        value1.assign(key)
        value2.assign(value)

    def _builtin_trace(self, source_location: SourceLocation, stack_base: int
                       , arguments: typing.List[Value]) -> Value:
        print(" ".join((str(argument) for argument in arguments)))
        return Value(ValueType.VOID, None)

    def _builtin_require(self, source_location: SourceLocation, stack_base: int
                         , arguments: typing.List[Value]) -> Value:
        return self._builtin_require_impl(self, source_location, stack_base, arguments)

    def _conversion_bool(self, in_value: Value, out_value: Value) -> bool:
        if in_value.type is ValueType.VOID:
            return False

        out_value.set(ValueType.BOOLEAN, bool(in_value))
        return True

    def _conversion_int(self, in_value: Value, out_value: Value) -> bool:
        if in_value.type is ValueType.INTEGER:
            out_value.assign(in_value)
        elif in_value.type is ValueType.FLOATING_POINT:
            integer = int(in_value.data)
            out_value.set(ValueType.INTEGER, integer)
        elif in_value.type is ValueType.STRING:
            try:
                integer = int(in_value.data)
            except:
                out_value.set(ValueType.VOID, None)
            else:
                out_value.set(ValueType.INTEGER, integer)
        else:
            return False

        return True

    def _conversion_float(self, in_value: Value, out_value: Value) -> bool:
        if in_value.type is ValueType.FLOATING_POINT:
            out_value.assign(in_value)
        elif in_value.type is ValueType.INTEGER:
            floating_point = float(in_value.data)
            out_value.set(ValueType.FLOATING_POINT, floating_point)
        elif in_value.type is ValueType.STRING:
            try:
                floating_point = float(in_value.data)
            except:
                out_value.set(ValueType.VOID, None)
            else:
                out_value.set(ValueType.FLOATING_POINT, floating_point)
        else:
            return False

        return True

    def _conversion_str(self, in_value: Value, out_value: Value) -> bool:
        if in_value.type is ValueType.STRING:
            out_value.assign(in_value)
        elif in_value.type in (ValueType.INTEGER, ValueType.FLOATING_POINT):
            string = str(in_value.data)
            out_value.set(ValueType.STRING, string)
        else:
            return False

        return True

    def _conversion_sizeof(self, in_value: Value, out_value: Value) -> bool:
        if in_value.type in (ValueType.STRING, ValueType.ARRAY, ValueType.STRUCTURE):
            size = len(in_value.data)
            out_value.set(ValueType.INTEGER, size)
        else:
            return False

        return True

    def _conversion_typeof(self, in_value: Value, out_value: Value) -> bool:
        type_name = str(in_value.type)
        out_value.set(ValueType.STRING, type_name)
        return True

    def _get_source_location(self, instruction_offset: int) -> SourceLocation:
        return self._call_frame.closure.get_function_prototype()\
                                       .get_source_location(instruction_offset)


_INSTRUCTION_EXECUTORS: typing.List[typing.Callable[
    [Interpreter, int, int, int, int, typing.Optional[int]],
    typing.Optional[int]
]] = len(Opcode.__members__) * [None]

_INSTRUCTION_EXECUTORS[Opcode.NO] = Interpreter._execute_no
_INSTRUCTION_EXECUTORS[Opcode.LOAD_VOID] = Interpreter._execute_load_void
_INSTRUCTION_EXECUTORS[Opcode.LOAD_NULL] = Interpreter._execute_load_null
_INSTRUCTION_EXECUTORS[Opcode.LOAD_BOOLEAN] = Interpreter._execute_load_boolean
_INSTRUCTION_EXECUTORS[Opcode.LOAD_INTEGER] = Interpreter._execute_load_integer
_INSTRUCTION_EXECUTORS[Opcode.LOAD_CONSTANT] = Interpreter._execute_load_constant
_INSTRUCTION_EXECUTORS[Opcode.LOAD_BUILTIN_FUNCTION] = Interpreter._execute_load_builtin_function
_INSTRUCTION_EXECUTORS[Opcode.MOVE] = Interpreter._execute_move
_INSTRUCTION_EXECUTORS[Opcode.CONVERT] = Interpreter._execute_convert
_INSTRUCTION_EXECUTORS[Opcode.GET_CAPTURE] = Interpreter._execute_get_capture
_INSTRUCTION_EXECUTORS[Opcode.SET_CAPTURE] = Interpreter._execute_set_capture
_INSTRUCTION_EXECUTORS[Opcode.GET_SLOT] = Interpreter._execute_get_slot
_INSTRUCTION_EXECUTORS[Opcode.SET_SLOT] = Interpreter._execute_set_slot
_INSTRUCTION_EXECUTORS[Opcode.CLEAR_SLOT] = Interpreter._execute_clear_slot
_INSTRUCTION_EXECUTORS[Opcode.NEGATE] = Interpreter._execute_negate
_INSTRUCTION_EXECUTORS[Opcode.ADD] = Interpreter._execute_add
_INSTRUCTION_EXECUTORS[Opcode.SUBSTRATE] = Interpreter._execute_substrate
_INSTRUCTION_EXECUTORS[Opcode.MULTIPLY] = Interpreter._execute_multiply
_INSTRUCTION_EXECUTORS[Opcode.DIVIDE] = Interpreter._execute_divide
_INSTRUCTION_EXECUTORS[Opcode.MODULO] = Interpreter._execute_modulo
_INSTRUCTION_EXECUTORS[Opcode.LOGICAL_AND] = Interpreter._execute_logical_and
_INSTRUCTION_EXECUTORS[Opcode.LOGICAL_OR] = Interpreter._execute_logical_or
_INSTRUCTION_EXECUTORS[Opcode.LOGICAL_NOT] = Interpreter._execute_logical_not
_INSTRUCTION_EXECUTORS[Opcode.BITWISE_AND] = Interpreter._execute_bitwise_and
_INSTRUCTION_EXECUTORS[Opcode.BITWISE_OR] = Interpreter._execute_bitwise_or
_INSTRUCTION_EXECUTORS[Opcode.BITWISE_XOR] = Interpreter._execute_bitwise_xor
_INSTRUCTION_EXECUTORS[Opcode.BITWISE_NOT] = Interpreter._execute_bitwise_not
_INSTRUCTION_EXECUTORS[Opcode.BITWISE_SHIFT_LEFT] = Interpreter._execute_bitwise_shift_left
_INSTRUCTION_EXECUTORS[Opcode.BITWISE_SHIFT_RIGHT] = Interpreter._execute_bitwise_shift_right
_INSTRUCTION_EXECUTORS[Opcode.EQUAL] = Interpreter._execute_equal
_INSTRUCTION_EXECUTORS[Opcode.NOT_EQUAL] = Interpreter._execute_not_equal
_INSTRUCTION_EXECUTORS[Opcode.LESS] = Interpreter._execute_less
_INSTRUCTION_EXECUTORS[Opcode.NOT_LESS] = Interpreter._execute_not_less
_INSTRUCTION_EXECUTORS[Opcode.GREATER] = Interpreter._execute_greater
_INSTRUCTION_EXECUTORS[Opcode.NOT_GREATER] = Interpreter._execute_not_greater
_INSTRUCTION_EXECUTORS[Opcode.JUMP] = Interpreter._execute_jump
_INSTRUCTION_EXECUTORS[Opcode.JUMP_IF_TRUE] = Interpreter._execute_jump_if_true
_INSTRUCTION_EXECUTORS[Opcode.JUMP_IF_FALSE] = Interpreter._execute_jump_if_false
_INSTRUCTION_EXECUTORS[Opcode.NEW_ARRAY] = Interpreter._execute_new_array
_INSTRUCTION_EXECUTORS[Opcode.NEW_STRUCTURE] = Interpreter._execute_new_structure
_INSTRUCTION_EXECUTORS[Opcode.NEW_CLOSURE] = Interpreter._execute_new_closure
_INSTRUCTION_EXECUTORS[Opcode.CALL] = Interpreter._execute_call
_INSTRUCTION_EXECUTORS[Opcode.RETURN] = Interpreter._execute_return
_INSTRUCTION_EXECUTORS[Opcode.NEW_ITERATOR] = Interpreter._execute_new_iterator
_INSTRUCTION_EXECUTORS[Opcode.ITERATE] = Interpreter._execute_iterate

_CONSTANT_TYPE_2_VALUE_TYPE: typing.Dict[ConstantType, ValueType] = {
    ConstantType.INTEGER: ValueType.INTEGER,
    ConstantType.FLOATING_POINT: ValueType.FLOATING_POINT,
    ConstantType.STRING: ValueType.STRING,
}

_CONVERTERS: typing.List[typing.Callable[[Interpreter, Value, Value]
                                         , bool]] = len(ConversionID._fields) * [None]

_CONVERTERS[ConversionID.BOOL] = Interpreter._conversion_bool
_CONVERTERS[ConversionID.INT] = Interpreter._conversion_int
_CONVERTERS[ConversionID.FLOAT] = Interpreter._conversion_float
_CONVERTERS[ConversionID.STR] = Interpreter._conversion_str
_CONVERTERS[ConversionID.SIZEOF] = Interpreter._conversion_sizeof
_CONVERTERS[ConversionID.TYPEOF] = Interpreter._conversion_typeof

_BUILTIN_FUNCTIONS: typing.List[BuiltinFunction] = len(BuiltinFunctionID._fields) * [None]

_BUILTIN_FUNCTIONS[BuiltinFunctionID.TRACE] = BuiltinFunction(Interpreter._builtin_trace)
_BUILTIN_FUNCTIONS[BuiltinFunctionID.REQUIRE] = BuiltinFunction(Interpreter._builtin_require)
