__all__ = (
    "BytecodeGenerator",
)


import contextlib
import enum
import typing

from .ast import ASTVisitor
from .error import LvalueRequiredError
from .expression import *
from .function_scope import *
from .parser import Parser
from .source_location import SourceLocation
from .statement import *
from .token import BasicTokenType, ExtraTokenType
from vm.executable import *
from vm.function_prototype import *


class BytecodeGenerator(ASTVisitor):
    __slots__ = (
        "_parser",
        "_executable",
        "_function_prototype",
        "_function_scope",
        "_context",
    )

    def __init__(self, parser: Parser) -> None:
        super().__init__()
        self._parser = parser
        self._executable = None
        self._function_prototype = None
        self._function_scope = None
        self._context = None

    def visit_null_statement(self, statement: NullStatement) -> None:
        pass

    def visit_block_statement(self, statement: BlockStatement) -> None:
        with self._enter_block_scope(statement.source_location):
            for statement1 in statement.statements:
                statement1.accept_visit(self)

    def visit_auto_statement(self, statement: AutoStatement) -> None:
        for variable_name, variable_value in statement.variables:
            if variable_value is None:
                self._function_prototype.add_instruction(
                    variable_name.source_location,
                    Opcode.LOAD_VOID,
                    operand1 = self._function_scope.create_local_variable(variable_name),
                )
            else:
                variable_value.accept_visit(self)
                register_id1 = self._function_scope.pop_target()
                register_id2 = self._function_scope.create_local_variable(variable_name)

                if register_id2 != register_id1:
                    self._function_prototype.add_instruction(
                        variable_name.source_location,
                        Opcode.MOVE,
                        operand1 = register_id2,
                        operand2 = register_id1,
                    )

    def visit_return_statement(self, statement: ReturnStatement) -> None:
        if statement.expression is None:
            self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.LOAD_VOID,
                operand1 = self._function_scope.push_target(statement.source_location),
            )
        else:
            statement.expression.accept_visit(self)

        register_id = self._function_scope.pop_target()

        self._function_prototype.add_instruction(
            statement.source_location,
            Opcode.RETURN,
            operand1 = register_id,
        )

    def visit_delete_statement(self, statement: DeleteStatement) -> None:
        statement.element_or_field[0].accept_visit(self);
        statement.element_or_field[1].accept_visit(self);
        register_id1 = self._function_scope.pop_target()
        register_id2 = self._function_scope.pop_target()

        self._function_prototype.add_instruction(
            statement.source_location,
            Opcode.CLEAR_SLOT,
            operand2 = register_id2,
            operand3 = register_id1,
        )

    def visit_break_statement(self, statement: BreakStatement) -> None:
        instruction_offset = self._function_prototype.add_instruction(
            statement.source_location,
            Opcode.JUMP,
            operand4 = 0,
        )

        self._context.break_instruction_offsets.append(instruction_offset)

    def visit_continue_statement(self, statement: ContinueStatement) -> None:
        instruction_offset = self._function_prototype.add_instruction(
            statement.source_location,
            Opcode.JUMP,
            operand4 = 0,
        )

        self._context.continue_instruction_offsets.append(instruction_offset)

    def visit_if_statement(self, statement: IfStatement) -> None:
        with contextlib.ExitStack() as stack:
            if statement.initialization is not None:
                stack.enter_context(self._enter_block_scope(statement.source_location))
                statement.initialization.accept_visit(self);

            statement.condition.accept_visit(self)
            register_id = self._function_scope.pop_target()

            instruction_offset1 = self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP_IF_FALSE,
                operand1 = register_id,
                operand4 = 0,
            )

            statement.then_body.accept_visit(self)

            if statement.else_body is not None:
                instruction_offset2 = self._function_prototype.add_instruction(
                    statement.source_location,
                    Opcode.JUMP,
                    operand4 = 0,
                )

                label1 = self._function_prototype.get_next_instruction_offset()

                self._function_prototype.set_instruction(
                    instruction_offset1,
                    operand4 = label1,
                )

                statement.else_body.accept_visit(self)
                label2 = self._function_prototype.get_next_instruction_offset()

                self._function_prototype.set_instruction(
                    instruction_offset2,
                    operand4 = label2,
                )
            else:
                label = self._function_prototype.get_next_instruction_offset()

                self._function_prototype.set_instruction(
                    instruction_offset1,
                    operand4 = label,
                )

    def visit_switch_statement(self, statement: SwitchStatement) -> None:
        with contextlib.ExitStack() as stack:
            if statement.initialization is not None:
                stack.enter_context(self._enter_block_scope(statement.source_location))
                statement.initialization.accept_visit(self);

            stack.enter_context(self._enter_switch())
            statement.expression.accept_visit(self)

            for switch_clause in statement.clauses:
                switch_clause.accept_visit(self)

            self._function_scope.pop_target()
            label = self._function_prototype.get_next_instruction_offset()

            for instruction_offset in self._context.break_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label,
                )

            for instruction_offset in self._context.fallthrough_instruction_offset:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label,
                )

    def visit_switch_clause(self, switch_clause: SwitchClause) -> None:
        if switch_clause.label is None:
            for statement in switch_clause.statements:
                statement.accept_visit(self)
        else:
            switch_clause.label.accept_visit(self)
            register_id1 = self._function_scope.pop_target()
            register_id2 = self._function_scope.peek_target()

            self._function_prototype.add_instruction(
                switch_clause.source_location,
                Opcode.EQUAL,
                operand1 = self._function_scope.push_target(switch_clause.source_location),
                operand2 = register_id1,
                operand3 = register_id2,
            )

            register_id = self._function_scope.pop_target()

            instruction_offset1 = self._function_prototype.add_instruction(
                switch_clause.source_location,
                Opcode.JUMP_IF_FALSE,
                operand1 = register_id,
                operand4 = 0,
            )

            for instruction_offset2 in self._context.fallthrough_instruction_offset:
                label1 = self._function_prototype.get_next_instruction_offset()

                self._function_prototype.set_instruction(
                    instruction_offset2,
                    operand4 = label1,
                )

            for statement in switch_clause.statements:
                statement.accept_visit(self)

            instruction_offset2 = self._function_prototype.add_instruction(
                switch_clause.source_location,
                Opcode.JUMP,
                operand4 = 0,
            )

            self._context.fallthrough_instruction_offset[:] = instruction_offset2,
            label2 = self._function_prototype.get_next_instruction_offset()

            self._function_prototype.set_instruction(
                instruction_offset1,
                operand4 = label2,
            )

    def visit_while_statement(self, statement: WhileStatement) -> None:
        with contextlib.ExitStack() as stack:
            if statement.initialization is not None:
                stack.enter_context(self._enter_block_scope(statement.source_location))
                statement.initialization.accept_visit(self);

            stack.enter_context(self._enter_loop())
            label1 = self._function_prototype.get_next_instruction_offset()
            statement.condition.accept_visit(self)
            register_id = self._function_scope.pop_target()

            instruction_offset = self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP_IF_FALSE,
                operand1 = register_id,
                operand4 = 0,
            )

            self._context.break_instruction_offsets.append(instruction_offset)
            statement.body.accept_visit(self)

            self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP,
                operand4 = label1,
            )

            label2 = self._function_prototype.get_next_instruction_offset()

            for instruction_offset in self._context.break_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label2,
                )

            for instruction_offset in self._context.continue_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label1,
                )

    def visit_do_while_statement(self, statement: DoWhileStatement) -> None:
        with contextlib.ExitStack() as stack:
            if statement.initialization is not None:
                stack.enter_context(self._enter_block_scope(statement.source_location))
                statement.initialization.accept_visit(self);

            stack.enter_context(self._enter_loop())
            label1 = self._function_prototype.get_next_instruction_offset()
            statement.body.accept_visit(self)
            label2 = self._function_prototype.get_next_instruction_offset()
            statement.condition.accept_visit(self)
            register_id = self._function_scope.pop_target()

            instruction_offset = self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP_IF_FALSE,
                operand1 = register_id,
                operand4 = 0,
            )

            self._context.break_instruction_offsets.append(instruction_offset)

            self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP,
                operand4 = label1,
            )

            label3 = self._function_prototype.get_next_instruction_offset()

            for instruction_offset in self._context.break_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label3,
                )

            for instruction_offset in self._context.continue_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label2,
                )

    def visit_for_statement(self, statement: ForStatement) -> None:
        with contextlib.ExitStack() as stack:
            if statement.initialization is not None:
                if isinstance(statement.initialization, AutoStatement):
                    stack.enter_context(self._enter_block_scope(statement.source_location))

                statement.initialization.accept_visit(self);

            stack.enter_context(self._enter_loop())
            label1 = self._function_prototype.get_next_instruction_offset()

            if statement.condition is not None:
                statement.condition.accept_visit(self)

                register_id = self._function_scope.pop_target()

                instruction_offset = self._function_prototype.add_instruction(
                    statement.source_location,
                    Opcode.JUMP_IF_FALSE,
                    operand1 = register_id,
                    operand4 = 0,
                )

                self._context.break_instruction_offsets.append(instruction_offset)

            statement.body.accept_visit(self)

            if statement.iteration is not None:
                statement.iteration.accept_visit(self)

            self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP,
                operand4 = label1,
            )

            label2 = self._function_prototype.get_next_instruction_offset()

            for instruction_offset in self._context.break_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label2,
                )

            for instruction_offset in self._context.continue_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label1,
                )

    def visit_foreach_statement(self, statement: ForeachStatement) -> None:
        with contextlib.ExitStack() as stack:
            stack.enter_context(self._enter_block_scope(statement.source_location))
            register_id1 = self._function_scope.create_local_variable(statement.iterator_name1)
            register_id2 = self._function_scope.create_local_variable(statement.iterator_name2)
            statement.container.accept_visit(self)
            register_id3 = self._function_scope.pop_target()

            self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.NEW_ITERATOR,
                operand1 = self._function_scope.push_target(statement.source_location),
                operand2 = register_id3,
            )

            register_id3 = self._function_scope.peek_target()
            stack.enter_context(self._enter_loop())
            label1 = self._function_prototype.get_next_instruction_offset()

            instruction_offset = self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP_IF_FALSE,
                operand1 = register_id3,
                operand4 = 0,
            )

            self._context.break_instruction_offsets.append(instruction_offset)

            self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.ITERATE,
                operand1 = register_id1,
                operand2 = register_id2,
                operand3 = register_id3,
            )

            statement.body.accept_visit(self)

            self._function_prototype.add_instruction(
                statement.source_location,
                Opcode.JUMP,
                operand4 = label1,
            )

            label2 = self._function_prototype.get_next_instruction_offset()

            for instruction_offset in self._context.break_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label2,
                )

            for instruction_offset in self._context.continue_instruction_offsets:
                self._function_prototype.set_instruction(
                    instruction_offset,
                    operand4 = label1,
                )

    def visit_expression_statement(self, statement: ExpressionStatement) -> None:
        statement.expression.accept_visit(self)
        self._function_scope.pop_target()

    def visit_nullary_expression(self, expression: NullaryExpression) -> None:
        if self._context.is_assigning_value:
            if expression.type is NullaryExpressionType.IDENTIFIER:
                pass
            else:
                raise LvalueRequiredError(expression.source_location)

        if expression.type is NullaryExpressionType.NULL:
            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.LOAD_NULL,
                operand1 = self._function_scope.push_target(expression.source_location),
            )
        elif expression.type is NullaryExpressionType.BOOLEAN:
            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.LOAD_BOOLEAN,
                operand1 = self._function_scope.push_target(expression.source_location),
                operand2 = 1 if expression.data else 0,
            )
        elif expression.type in (
            NullaryExpressionType.INTEGER,
            NullaryExpressionType.FLOATING_POINT,
            NullaryExpressionType.STRING,
        ):
            if expression.type is NullaryExpressionType.INTEGER \
               and expression.data in range(-0x80000000, 0x7fffffff):
                self._function_prototype.add_instruction(
                    expression.source_location,
                    Opcode.LOAD_INTEGER,
                    operand1 = self._function_scope.push_target(expression.source_location),
                    operand4 = expression.data,
                )
            else:
                if expression.type is NullaryExpressionType.INTEGER:
                    add_constant = self._executable.add_integer_constant
                elif expression.type is NullaryExpressionType.FLOATING_POINT:
                    add_constant = self._executable.add_floating_point_constant
                else:
                    add_constant = self._executable.add_string_constant

                constant_id = add_constant(expression.source_location, expression.data)

                self._function_prototype.add_instruction(
                    expression.source_location,
                    Opcode.LOAD_CONSTANT,
                    operand1 = self._function_scope.push_target(expression.source_location),
                    operand4 = constant_id,
                )
        elif expression.type is NullaryExpressionType.IDENTIFIER:
            variable_name = expression
            variable_type, variable_id = self._function_scope.find_variable(variable_name)

            if variable_type is VariableType.LOCAL:
                if self._context.is_assigning_value:
                    register_id1 = variable_id
                    register_id2 = self._function_scope.peek_target()

                    if register_id1 != register_id2:
                        self._function_prototype.add_instruction(
                            expression.source_location,
                            Opcode.MOVE,
                            operand1 = register_id1,
                            operand2 = register_id2,
                        )
                else:
                    register_id = variable_id
                    self._function_scope.push_target(expression.source_location, register_id)
            elif variable_type is VariableType.FOREIGN:
                capture_id = variable_id

                if self._context.is_assigning_value:
                    register_id = self._function_scope.peek_target()

                    self._function_prototype.add_instruction(
                        expression.source_location,
                        Opcode.SET_CAPTURE,
                        operand1 = register_id,
                        operand4 = capture_id,
                    )
                else:
                    self._function_prototype.add_instruction(
                        expression.source_location,
                        Opcode.GET_CAPTURE,
                        operand1 = self._function_scope.push_target(expression.source_location),
                        operand4 = capture_id,
                    )
            else:
                assert False
        elif expression.type is NullaryExpressionType.ARRAY_LITERAL:
            array_literal = expression.data

            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.NEW_ARRAY,
                operand1 = self._function_scope.push_target(expression.source_location),
            )

            register_id1 = self._function_scope.peek_target()
            default_element_index = 0

            for element_index, element_value in array_literal.elements:
                if element_index is None:
                    self._function_prototype.add_instruction(
                        element_value.source_location,
                        Opcode.LOAD_INTEGER,
                        operand1 = self._function_scope.push_target(expression.source_location),
                        operand4 = default_element_index,
                    )

                    default_element_index += 1
                else:
                    element_index.accept_visit(self)

                element_value.accept_visit(self)
                register_id2 = self._function_scope.pop_target()
                register_id3 = self._function_scope.pop_target()

                self._function_prototype.add_instruction(
                    element_value.source_location if element_index is None
                                                  else element_index.source_location,
                    Opcode.SET_SLOT,
                    operand1 = register_id2,
                    operand2 = register_id1,
                    operand3 = register_id3,
                )
        elif expression.type is NullaryExpressionType.STRUCTURE_LITERAL:
            structure_literal = expression.data

            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.NEW_STRUCTURE,
                operand1 = self._function_scope.push_target(expression.source_location),
            )

            register_id1 = self._function_scope.peek_target()

            for field_name, field_value in structure_literal.fields:
                field_name.accept_visit(self)
                field_value.accept_visit(self)
                register_id2 = self._function_scope.pop_target()
                register_id3 = self._function_scope.pop_target()

                self._function_prototype.add_instruction(
                    field_name.source_location,
                    Opcode.SET_SLOT,
                    operand1 = register_id2,
                    operand2 = register_id1,
                    operand3 = register_id3,
                )
        elif expression.type is NullaryExpressionType.FUNCTION_LITERAL:
            function_literal = expression.data
            register_id_start = self._function_scope.get_next_register_id()

            for _, argument in function_literal.parameters2:
                argument.accept_visit(self)
                self._ensure_temporary_register(argument.source_location)

            register_id_end = self._function_scope.get_next_register_id()
            function_prototype_id = self._create_function_prototype(function_literal)

            for _ in range(register_id_start, register_id_end):
                self._function_scope.pop_target()

            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.NEW_CLOSURE,
                operand1 = self._function_scope.push_target(expression.source_location),
                operand2 = register_id_start,
                operand3 = register_id_end,
                operand4 = function_prototype_id,
            )
        elif expression.type is NullaryExpressionType.BUILTIN_FUNCTION_NAME:
            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.LOAD_BUILTIN_FUNCTION,
                operand1 = self._function_scope.push_target(expression.source_location),

                operand2 = {
                    BasicTokenType.TRACE_KEYWORD: BuiltinFunctionID.TRACE,
                    BasicTokenType.REQUIRE_KEYWORD: BuiltinFunctionID.REQUIRE,
                }[expression.data],
            )
        else:
            assert False

    def visit_unary_expression(self, expression: UnaryExpression) -> None:
        if self._context.is_assigning_value:
            raise LvalueRequiredError(expression.source_location)

        if expression.operator in (ExtraTokenType("++"), ExtraTokenType("--")):
            assert expression.type in (UnaryExpressionType.PREFIX, UnaryExpressionType.POSTFIX)
            expression.operand.accept_visit(self)

            if expression.type is UnaryExpressionType.POSTFIX:
                self._ensure_temporary_register(expression.source_location)

            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.LOAD_INTEGER,
                operand1 = self._function_scope.push_target(expression.source_location),
                operand4 = 1,
            )

            register_id1 = self._function_scope.pop_target()
            register_id2 = self._function_scope.peek_target()

            self._function_prototype.add_instruction(
                expression.source_location,
                Opcode.ADD if expression.operator is ExtraTokenType("++") else Opcode.SUBSTRATE,
                operand1 = self._function_scope.push_target(expression.source_location)
                           if expression.type is UnaryExpressionType.POSTFIX
                           else register_id2,
                operand2 = register_id2,
                operand3 = register_id1,
            )

            with self._assign_value(True):
                expression.operand.accept_visit(self)

            if expression.type is UnaryExpressionType.POSTFIX:
                self._function_scope.pop_target()
        elif expression.operator is ExtraTokenType("-") \
             and isinstance(expression.operand, NullaryExpression) \
             and expression.operand.type in (NullaryExpressionType.INTEGER
                                             , NullaryExpressionType.FLOATING_POINT):
                expression.operand.data *= -1
                expression.operand.accept_visit(self)
        else:
            expression.operand.accept_visit(self)
            register_id = self._function_scope.pop_target()

            if expression.type is UnaryExpressionType.CONVERSION:
                self._function_prototype.add_instruction(
                    expression.source_location,
                    Opcode.CONVERT,
                    operand1 = self._function_scope.push_target(expression.source_location),
                    operand2 = register_id,

                    operand3 = {
                        BasicTokenType.BOOL_KEYWORD: ConversionID.BOOL,
                        BasicTokenType.INT_KEYWORD: ConversionID.INT,
                        BasicTokenType.FLOAT_KEYWORD: ConversionID.FLOAT,
                        BasicTokenType.STR_KEYWORD: ConversionID.STR,
                        BasicTokenType.SIZEOF_KEYWORD: ConversionID.SIZEOF,
                        BasicTokenType.TYPEOF_KEYWORD: ConversionID.TYPEOF,
                    }[expression.operator],
                )
            elif expression.type is UnaryExpressionType.PREFIX:
                if expression.operator in _OPERATOR_2_OPCODE1.keys():
                    opcode = _OPERATOR_2_OPCODE1[expression.operator]

                    if opcode is not Opcode.NO:
                        self._function_prototype.add_instruction(
                            expression.source_location,
                            opcode,
                            operand1 = self._function_scope.push_target(expression.source_location),
                            operand2 = register_id,
                        )
                else:
                    assert False
            else:
                assert False

    def visit_binary_expression(self, expression: BinaryExpression) -> None:
        if self._context.is_assigning_value:
            if expression.operator in (ExtraTokenType("."), ExtraTokenType("[")):
                pass
            else:
                raise LvalueRequiredError(expression.source_location)

        if expression.operator is ExtraTokenType(","):
            expression.operand1.accept_visit(self)
            self._function_scope.pop_target()
            expression.operand2.accept_visit(self)
        elif expression.operator in _OPERATOR_2_OPCODE2.keys():
            opcode = _OPERATOR_2_OPCODE2[expression.operator]

            if opcode is Opcode.NO:
                expression.operand2.accept_visit(self)
            else:
                expression.operand1.accept_visit(self)
                expression.operand2.accept_visit(self)
                register_id1 = self._function_scope.pop_target()
                register_id2 = self._function_scope.peek_target()

                self._function_prototype.add_instruction(
                    expression.source_location,
                    opcode,
                    operand1 = register_id2,
                    operand2 = register_id2,
                    operand3 = register_id1,
                )

            with self._assign_value(True):
                expression.operand1.accept_visit(self)
        elif expression.operator in _OPERATOR_2_OPCODE3.keys():
            opcode = _OPERATOR_2_OPCODE3[expression.operator]
            expression.operand1.accept_visit(self)
            self._ensure_temporary_register(expression.source_location)
            register_id = self._function_scope.pop_target()

            instruction_offset = self._function_prototype.add_instruction(
                expression.source_location,
                opcode,
                operand1 = register_id,
                operand4 = 0,
            )

            expression.operand2.accept_visit(self)
            self._ensure_temporary_register(expression.source_location)
            label = self._function_prototype.get_next_instruction_offset()

            self._function_prototype.set_instruction(
                instruction_offset,
                operand4 = label,
            )
        elif expression.operator in _OPERATOR_2_OPCODE4.keys():
            opcode = _OPERATOR_2_OPCODE4[expression.operator]
            expression.operand1.accept_visit(self)
            expression.operand2.accept_visit(self)
            register_id1 = self._function_scope.pop_target()
            register_id2 = self._function_scope.pop_target()

            self._function_prototype.add_instruction(
                expression.source_location,
                opcode,
                operand1 = self._function_scope.push_target(expression.source_location),
                operand2 = register_id2,
                operand3 = register_id1,
            )
        elif expression.operator in (ExtraTokenType("."), ExtraTokenType("[")):
            if self._context.is_assigning_value:
                with self._assign_value(False):
                    expression.operand1.accept_visit(self)
                    expression.operand2.accept_visit(self)

                register_id1 = self._function_scope.pop_target()
                register_id2 = self._function_scope.pop_target()
                register_id3 = self._function_scope.peek_target()

                self._function_prototype.add_instruction(
                    expression.source_location,
                    Opcode.SET_SLOT,
                    operand1 = register_id3,
                    operand2 = register_id2,
                    operand3 = register_id1,
                )
            else:
                expression.operand1.accept_visit(self)
                expression.operand2.accept_visit(self)
                register_id1 = self._function_scope.pop_target()
                register_id2 = self._function_scope.pop_target()

                self._function_prototype.add_instruction(
                    expression.source_location,
                    Opcode.GET_SLOT,
                    operand1 = self._function_scope.push_target(expression.source_location),
                    operand2 = register_id2,
                    operand3 = register_id1,
                )
        else:
            assert False

    def visit_ternary_expression(self, expression: TernaryExpression) -> None:
        expression.operand1.accept_visit(self)
        register_id = self._function_scope.pop_target()

        instruction_offset1 = self._function_prototype.add_instruction(
            expression.source_location,
            Opcode.JUMP_IF_FALSE,
            operand1 = register_id,
            operand4 = 0,
        )

        expression.operand2.accept_visit(self)
        self._ensure_temporary_register(expression.source_location)

        instruction_offset2 = self._function_prototype.add_instruction(
            expression.source_location,
            Opcode.JUMP,
            operand4 = 0,
        )

        label1 = self._function_prototype.get_next_instruction_offset()

        self._function_prototype.set_instruction(
            instruction_offset1,
            operand4 = label1,
        )

        self._function_scope.pop_target()
        expression.operand3.accept_visit(self)
        self._ensure_temporary_register(expression.source_location)
        label2 = self._function_prototype.get_next_instruction_offset()

        self._function_prototype.set_instruction(
            instruction_offset2,
            operand4 = label2,
        )

    def visit_variary_expression(self, expression: VariaryExpression) -> None:
        register_id_start = self._function_scope.get_next_register_id()

        for operand in expression.operands:
            operand.accept_visit(self)
            self._ensure_temporary_register(operand.source_location)

        register_id_end = self._function_scope.get_next_register_id()

        for _ in range(register_id_start, register_id_end):
            self._function_scope.pop_target()

        self._function_prototype.add_instruction(
            expression.source_location,
            Opcode.CALL,
            operand1 = self._function_scope.push_target(expression.source_location),
            operand2 = register_id_start,
            operand3 = register_id_end,
        )

    def get_executable(self) -> Executable:
        self._executable = Executable(_MAX_CONSTANT_TABLE_LENGTH)
        self._create_function_prototype(self._parser.get_program())
        return self._executable

    def _create_function_prototype(self, function_literal: FunctionLiteral) -> int:
        function_prototype = FunctionPrototype(len(function_literal.parameters1)
                                               , len(function_literal.parameters2)
                                               , function_literal.rest_parameter is not None
                                               , _MAX_BYTECODE_LENGTH)
        function_prototype_id = self._executable.add_function_prototype(function_prototype)
        function_scope = FunctionScope(self._function_scope, _REGISTER_POOL_SIZE
                                       , _MAX_CAPTURE_TABLE_LENGTH)

        for parameter in function_literal.parameters1:
            function_scope.create_local_variable(parameter)

        for parameter, _ in function_literal.parameters2:
            function_scope.create_local_variable(parameter)

        if function_literal.rest_parameter is not None:
            function_scope.create_local_variable(function_literal.rest_parameter)

        context = _BytecodeGeneratorContext()
        backup = self._function_prototype, self._function_scope, self._context
        self._function_prototype, self._function_scope, self._context = function_prototype \
                                                                        , function_scope, context

        for statement in function_literal.body.statements:
            statement.accept_visit(self)

            if isinstance(statement, ReturnStatement):
                break
        else:
            source_location = function_literal.body.source_location

            function_prototype.add_instruction(
                source_location,
                Opcode.LOAD_VOID,
                operand1 = function_scope.push_target(source_location),
            )

            register_id = function_scope.pop_target()

            function_prototype.add_instruction(
                source_location,
                Opcode.RETURN,
                operand1 = register_id,
            )

        self._function_prototype, self._function_scope, self._context = backup

        for variable_name in function_scope.get_foreign_variable_names():
            variable_type, variable_id = self._function_scope.get_variable(variable_name)
            capture_is_original = variable_type is VariableType.LOCAL
            register_id_or_capture_id = variable_id
            function_prototype.capture_infos.append((capture_is_original
                                                     , register_id_or_capture_id))

        function_prototype.number_of_registers = function_scope.get_max_register_id() + 1
        return function_prototype_id

    @contextlib.contextmanager
    def _enter_block_scope(self, source_location: SourceLocation) -> typing.ContextManager[None]:
        with self._function_scope.enter_block_scope():
            register_id = self._function_scope.get_next_register_id()
            yield

            if self._function_scope.has_original_captures():
                self._function_prototype.add_instruction(
                    source_location,
                    Opcode.KILL_ORIGINAL_CAPTURES,
                    operand1 = register_id,
                )

    @contextlib.contextmanager
    def _enter_switch(self) -> typing.ContextManager[None]:
        backup = self._context

        self._context = self._context._replace(
            break_instruction_offsets = [],
            fallthrough_instruction_offset = [],
        )

        yield
        self._context = backup

    @contextlib.contextmanager
    def _enter_loop(self) -> typing.ContextManager[None]:
        backup = self._context

        self._context = self._context._replace(
            break_instruction_offsets = [],
            continue_instruction_offsets = [],
        )

        yield
        self._context = backup

    @contextlib.contextmanager
    def _assign_value(self, on_off) -> typing.ContextManager[None]:
        backup = self._context

        self._context = self._context._replace(
            is_assigning_value = on_off,
        )

        yield
        self._context = backup

    def _ensure_temporary_register(self, source_location: SourceLocation) -> None:
        register_id1 = self._function_scope.pop_target()
        register_id2 = self._function_scope.push_target(source_location)

        if register_id2 != register_id1:
            self._function_prototype.add_instruction(
                source_location,
                Opcode.MOVE,
                operand1 = register_id2,
                operand2 = register_id1,
            )


class _BytecodeGeneratorContext(typing.NamedTuple):
    is_assigning_value: bool = False
    break_instruction_offsets: typing.List[int] = []
    continue_instruction_offsets: typing.List[int] = []
    fallthrough_instruction_offset: typing.List[int] = []


_MAX_CONSTANT_TABLE_LENGTH = 1 << 31
_MAX_BYTECODE_LENGTH = 1 << 31
_REGISTER_POOL_SIZE = 1 << 8
_MAX_CAPTURE_TABLE_LENGTH = 1 << 31

_OPERATOR_2_OPCODE1: typing.Dict[ExtraTokenType, Opcode] = {
    ExtraTokenType("+"): Opcode.NO,
    ExtraTokenType("-"): Opcode.NEGATE,
    ExtraTokenType("!"): Opcode.LOGICAL_NOT,
    ExtraTokenType("~"): Opcode.BITWISE_NOT,
}

_OPERATOR_2_OPCODE2: typing.Dict[ExtraTokenType, Opcode] = {
    ExtraTokenType("="): Opcode.NO,
    ExtraTokenType("+="): Opcode.ADD,
    ExtraTokenType("-="): Opcode.SUBSTRATE,
    ExtraTokenType("*="): Opcode.MULTIPLY,
    ExtraTokenType("/="): Opcode.DIVIDE,
    ExtraTokenType("%="): Opcode.MODULO,
    ExtraTokenType("<<="): Opcode.BITWISE_SHIFT_LEFT,
    ExtraTokenType(">>="): Opcode.BITWISE_SHIFT_RIGHT,
    ExtraTokenType("&="): Opcode.BITWISE_AND,
    ExtraTokenType("^="): Opcode.BITWISE_XOR,
    ExtraTokenType("|="): Opcode.BITWISE_OR,
}

_OPERATOR_2_OPCODE3: typing.Dict[ExtraTokenType, Opcode] = {
    ExtraTokenType("||"): Opcode.JUMP_IF_TRUE,
    ExtraTokenType("&&"): Opcode.JUMP_IF_FALSE,
}

_OPERATOR_2_OPCODE4: typing.Dict[ExtraTokenType, Opcode] = {
    ExtraTokenType("|"): Opcode.BITWISE_OR,
    ExtraTokenType("^"): Opcode.BITWISE_XOR,
    ExtraTokenType("&"): Opcode.BITWISE_AND,
    ExtraTokenType("=="): Opcode.EQUAL,
    ExtraTokenType("!="): Opcode.NOT_EQUAL,
    ExtraTokenType("<"): Opcode.LESS,
    ExtraTokenType("<="): Opcode.NOT_GREATER,
    ExtraTokenType(">"): Opcode.GREATER,
    ExtraTokenType(">="): Opcode.NOT_LESS,
    ExtraTokenType("<<"): Opcode.BITWISE_SHIFT_LEFT,
    ExtraTokenType(">>"): Opcode.BITWISE_SHIFT_RIGHT,
    ExtraTokenType("+"): Opcode.ADD,
    ExtraTokenType("-"): Opcode.SUBSTRATE,
    ExtraTokenType("*"): Opcode.MULTIPLY,
    ExtraTokenType("/"): Opcode.DIVIDE,
    ExtraTokenType("%"): Opcode.MODULO,
}
