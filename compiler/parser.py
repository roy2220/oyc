__all__ = (
    "Parser",
    "Error",
    "UnexpectedTokenError",
    "EndOfFileError",
)


import collections
import contextlib
import ctypes
import typing

from . import utils
from .expression import *
from .scanner import Scanner
from .source_location import SourceLocation
from .statement import *
from .token import *
from .error import EndOfFileError, UnexpectedTokenError


class Parser:
    __slots__ = (
        "_scanner",
        "_token_buffer",
        "_context",
    )

    def __init__(self, scanner: Scanner) -> None:
        self._scanner = scanner
        self._token_buffer = collections.deque()
        self._context = _ParserContext()

    def get_program(self) -> FunctionLiteral:
        source_location = self._scanner.get_source_location()

        rest_parameter = NullaryExpression(
            source_location,
            type_ = NullaryExpressionType.IDENTIFIER,
            data = "argv",
        )

        statements = []

        while True:
            token1 = self._peek_token(1)

            if token1.type is BasicTokenType.NO:
                break

            statements.append(self._get_statement(auto_statement_is_allowed = True))

        body = BlockStatement(
            source_location,
            statements = statements,
        )

        return FunctionLiteral([], [], rest_parameter, body)

    @contextlib.contextmanager
    def _allow_break_statement(self) -> typing.ContextManager[None]:
        backup = self._context

        self._context = self._context._replace(
            break_statement_is_allowed = True,
        )

        yield
        self._context = backup

    @contextlib.contextmanager
    def _allow_break_and_continue_statement(self) -> typing.ContextManager[None]:
        backup = self._context

        self._context = self._context._replace(
            break_statement_is_allowed = True,
            continue_statement_is_allowed = True,
        )

        yield
        self._context = backup

    @contextlib.contextmanager
    def _reset_context(self) -> typing.ContextManager[None]:
        backup = self._context
        self._context = _ParserContext()
        yield
        self._context = backup

    def _get_statement(self, *, auto_statement_is_allowed: bool = False) -> Statement:
        token1 = self._peek_token(1)

        if token1.type is ExtraTokenType(";"):
            return self._get_null_statement()
        if token1.type is ExtraTokenType("{"):
            return self._get_block_statement()
        elif token1.type is BasicTokenType.RETURN_KEYWORD:
            return self._get_return_statement()
        elif token1.type is BasicTokenType.DELETE_KEYWORD:
            return self._get_delete_statement()
        elif token1.type is BasicTokenType.IF_KEYWORD:
            return self._get_if_statement()
        elif token1.type is BasicTokenType.SWITCH_KEYWORD:
            return self._get_switch_statement()
        elif token1.type is BasicTokenType.WHILE_KEYWORD:
            return self._get_while_statement()
        elif token1.type is BasicTokenType.DO_KEYWORD:
            return self._get_do_while_statement()
        elif token1.type is BasicTokenType.FOR_KEYWORD:
            return self._get_for_statement()
        elif token1.type is BasicTokenType.FOREACH_KEYWORD:
            return self._get_foreach_statement()
        else:
            if token1.type is BasicTokenType.AUTO_KEYWORD:
                if auto_statement_is_allowed:
                    return self._get_auto_statement()
            elif token1.type is BasicTokenType.BREAK_KEYWORD:
                if self._context.break_statement_is_allowed:
                    return self._get_break_statement()
            elif token1.type is BasicTokenType.CONTINUE_KEYWORD:
                if self._context.continue_statement_is_allowed:
                    return self._get_continue_statement()

            return self._get_expression_statement()

    def _get_null_statement(self) -> NullStatement:
        source_location = self._get_expected_token((ExtraTokenType(";"),)).source_location

        return NullStatement(
            source_location,
        )

    def _get_block_statement(self) -> BlockStatement:
        source_location = self._get_expected_token((ExtraTokenType("{"),)).source_location
        statements = []

        while True:
            token1 = self._peek_token(1)

            if token1.type is ExtraTokenType("}"):
                break

            statements.append(self._get_statement(auto_statement_is_allowed = True))

        self._get_token()

        return BlockStatement(
            source_location,
            statements = statements,
        )

    def _get_auto_statement(self) -> AutoStatement:
        source_location = self._get_expected_token((BasicTokenType.AUTO_KEYWORD,)).source_location
        variables = []
        variable_count = 0

        while True:
            if variable_count >= 1:
                token0 = self._get_expected_token((ExtraTokenType(";"), ExtraTokenType(",")))

                if token0.type is ExtraTokenType(";"):
                    break

            variable_name = self._get_user_defined_name()
            token1 = self._peek_token(1)

            if token1.type is ExtraTokenType("="):
                self._get_token()
                variable_value = self._get_expression2();
            else:
                variable_value = None

            variables.append((variable_name, variable_value))
            variable_count += 1

        return AutoStatement(
            source_location,
            variables = variables,
        )

    def _get_return_statement(self) -> ReturnStatement:
        source_location = self._get_expected_token((BasicTokenType.RETURN_KEYWORD,))\
                          .source_location

        token1 = self._peek_token(1)

        if token1.type is ExtraTokenType(";"):
            expression = None
            self._get_token()
        else:
            expression = self._get_expression1()
            self._get_expected_token((ExtraTokenType(";"),))

        return ReturnStatement(
            source_location,
            expression = expression,
        )

    def _get_delete_statement(self) -> DeleteStatement:
        source_location = self._get_expected_token((BasicTokenType.DELETE_KEYWORD,))\
                          .source_location
        element_or_field = self._get_expression7(), self._get_designator()
        self._get_expected_token((ExtraTokenType(";"),))

        return DeleteStatement(
            source_location,
            element_or_field = element_or_field,
        )

    def _get_break_statement(self) -> BreakStatement:
        source_location = self._get_expected_token((BasicTokenType.BREAK_KEYWORD,)).source_location
        self._get_expected_token((ExtraTokenType(";"),))

        return BreakStatement(
            source_location,
        )

    def _get_continue_statement(self) -> ContinueStatement:
        source_location = self._get_expected_token((BasicTokenType.CONTINUE_KEYWORD,))\
                          .source_location
        self._get_expected_token((ExtraTokenType(";"),))

        return ContinueStatement(
            source_location,
        )

    def _get_if_statement(self) -> IfStatement:
        source_location = self._get_expected_token((BasicTokenType.IF_KEYWORD,)).source_location
        self._get_expected_token((ExtraTokenType("("),))
        token1 = self._peek_token(1)

        if token1.type is BasicTokenType.AUTO_KEYWORD:
            initialization = self._get_auto_statement()
        else:
            initialization = None

        condition = self._get_expression1()
        self._get_expected_token((ExtraTokenType(")"),))
        then_body = self._get_statement()
        token1 = self._peek_token(1)

        if token1.type is BasicTokenType.ELSE_KEYWORD:
            self._get_token()
            else_body = self._get_statement()
        else:
            else_body = None

        return IfStatement(
            source_location,
            initialization = initialization,
            condition = condition,
            then_body = then_body,
            else_body = else_body,
        )

    def _get_switch_statement(self) -> SwitchStatement:
        source_location = self._get_expected_token((BasicTokenType.SWITCH_KEYWORD,)).source_location
        self._get_expected_token((ExtraTokenType("("),))
        token1 = self._peek_token(1)

        if token1.type is BasicTokenType.AUTO_KEYWORD:
            initialization = self._get_auto_statement()
        else:
            initialization = None

        expression = self._get_expression1()
        self._get_expected_token((ExtraTokenType(")"),))
        switch_clauses = self._get_switch_clauses()

        return SwitchStatement(
            source_location,
            initialization = initialization,
            expression = expression,
            clauses = switch_clauses,
        )

    def _get_switch_clauses(self) -> typing.List[SwitchClause]:
        self._get_expected_token((ExtraTokenType("{"),))
        switch_clauses = []

        while True:
            token1 = self._peek_token(1)

            if token1.type is ExtraTokenType("}"):
                break

            switch_clauses.append(self._get_switch_clause())

        self._get_token()
        return switch_clauses

    def _get_switch_clause(self) -> SwitchClause:
        token0 = self._get_expected_token((BasicTokenType.CASE_KEYWORD
                                           , BasicTokenType.DEFAULT_KEYWORD))
        source_location = token0.source_location

        if token0.type is BasicTokenType.CASE_KEYWORD:
            label = self._get_expression1()
            self._get_expected_token((ExtraTokenType(":"),))
            statements = []

            with self._allow_break_statement():
                while True:
                    token1 = self._peek_token(1)

                    if token1.type in (BasicTokenType.CASE_KEYWORD, BasicTokenType.DEFAULT_KEYWORD
                                       , ExtraTokenType("}")):
                        break

                    statements.append(self._get_statement())
        else:
            label = None
            self._get_expected_token((ExtraTokenType(":"),))
            statements = []

            with self._allow_break_statement():
                while True:
                    token1 = self._peek_token(1)

                    if token1.type is ExtraTokenType("}"):
                        break

                    statements.append(self._get_statement())

        switch_clause = SwitchClause(
            source_location,
            label = label,
            statements = statements,
        )

        return switch_clause

    def _get_while_statement(self) -> WhileStatement:
        source_location = self._get_expected_token((BasicTokenType.WHILE_KEYWORD,)).source_location
        self._get_expected_token((ExtraTokenType("("),))
        token1 = self._peek_token(1)

        if token1.type is BasicTokenType.AUTO_KEYWORD:
            initialization = self._get_auto_statement()
        else:
            initialization = None

        condition = self._get_expression1()
        self._get_expected_token((ExtraTokenType(")"),))

        with self._allow_break_and_continue_statement():
            body = self._get_statement()

        return WhileStatement(
            source_location,
            initialization = initialization,
            condition = condition,
            body = body,
        )

    def _get_do_while_statement(self) -> DoWhileStatement:
        source_location = self._get_expected_token((BasicTokenType.DO_KEYWORD,)).source_location

        with self._allow_break_and_continue_statement():
            body = self._get_statement()

        self._get_expected_token((BasicTokenType.WHILE_KEYWORD,))
        self._get_expected_token((ExtraTokenType("("),))
        token1 = self._peek_token(1)

        if token1.type is BasicTokenType.AUTO_KEYWORD:
            initialization = self._get_auto_statement()
        else:
            initialization = None

        condition = self._get_expression1()
        self._get_expected_token((ExtraTokenType(")"),))
        self._get_expected_token((ExtraTokenType(";"),))

        return DoWhileStatement(
            source_location,
            body = body,
            initialization = initialization,
            condition = condition,
        )

    def _get_for_statement(self) -> ForStatement:
        source_location = self._get_expected_token((BasicTokenType.FOR_KEYWORD,)).source_location
        self._get_expected_token((ExtraTokenType("("),))
        token1 = self._peek_token(1)

        if token1.type is ExtraTokenType(";"):
            initialization = None
            self._get_token()
        else:
            if token1.type is BasicTokenType.AUTO_KEYWORD:
                initialization = self._get_auto_statement()
            else:
                initialization = self._get_expression_statement()

        token1 = self._peek_token(1)

        if token1.type is ExtraTokenType(";"):
            condition = None
            self._get_token()
        else:
            condition = self._get_expression1()
            self._get_expected_token((ExtraTokenType(";"),))

        token1 = self._peek_token(1)

        if token1.type is ExtraTokenType(")"):
            iteration = None
            self._get_token()
        else:
            expression = self._get_expression1()

            iteration = ExpressionStatement(
                expression.source_location,
                expression = expression,
            )

            self._get_expected_token((ExtraTokenType(")"),))

        with self._allow_break_and_continue_statement():
            body = self._get_statement()

        return ForStatement(
            source_location,
            initialization = initialization,
            condition = condition,
            iteration = iteration,
            body = body,
        )

    def _get_foreach_statement(self) -> ForeachStatement:
        source_location = self._get_expected_token((BasicTokenType.FOREACH_KEYWORD,))\
                          .source_location
        self._get_expected_token((ExtraTokenType("("),))
        self._get_expected_token((BasicTokenType.AUTO_KEYWORD,))
        iterator_name1 = self._get_user_defined_name()
        token0 = self._get_expected_token((ExtraTokenType(","), ExtraTokenType(":")))

        if token0.type is ExtraTokenType(","):
            iterator_name2 = self._get_user_defined_name()
            self._get_expected_token((ExtraTokenType(":"),))
        else:
            iterator_name2 = None

        container = self._get_expression1()
        self._get_expected_token((ExtraTokenType(")"),))

        with self._allow_break_and_continue_statement():
            body = self._get_statement()

        return ForeachStatement(
            source_location,
            iterator_name1 = iterator_name1,
            iterator_name2 = iterator_name2,
            container = container,
            body = body,
        )

    def _get_expression_statement(self) -> ExpressionStatement:
        expression = self._get_expression1()
        source_location = expression.source_location
        self._get_expected_token((ExtraTokenType(";"),))

        return ExpressionStatement(
            source_location,
            expression = expression,
        )

    def _get_expression1(self) -> Expression:
        expression = self._get_expression2()

        while True:
            token1 = self._peek_token(1)

            if token1.type is not ExtraTokenType(","):
                break

            expression = BinaryExpression(
                expression.source_location,
                operand1 = expression,
                operator = self._get_token().type,
                operand2 = self._get_expression2(),
            )

        return expression

    def _get_expression2(self) -> Expression:
        expression = self._get_expression3()
        token1 = self._peek_token(1)

        if token1.type in _ASSIGNMENT_OPERATORS:
            expression = BinaryExpression(
                expression.source_location,
                operand1 = expression,
                operator = self._get_token().type,
                operand2 = self._get_expression2(),
            )

        return expression

    def _get_expression3(self) -> Expression:
        expression = self._get_expression4(1)
        token1 = self._peek_token(1)

        if token1.type is ExtraTokenType("?"):
            expression = TernaryExpression(
                expression.source_location,
                operand1 = expression,
                operator1 = self._get_token().type,
                operand2 = self._get_expression3(),
                operator2 = self._get_expected_token((ExtraTokenType(":"),)).type,
                operand3 = self._get_expression3(),
            )

        return expression

    def _get_expression4(self, min_operator_precedence: int) -> Expression:
        expression = self._get_expression5()

        while True:
            token1 = self._peek_token(1)
            operator_precedence = _OPERATOR_PRECEDENCES.get(token1.type, 0)

            if operator_precedence < min_operator_precedence:
                break

            expression = BinaryExpression(
                expression.source_location,
                operand1 = expression,
                operator = self._get_token().type,
                operand2 = self._get_expression4(operator_precedence + 1),
            )

        return expression

    def _get_expression5(self) -> Expression:
        token1 = self._peek_token(1)

        if token1.type in _CONVERSION_OPERATORS:
            expression = UnaryExpression(
                token1.source_location,
                type_ = UnaryExpressionType.CONVERSION,
                operator = self._get_token().type,

                operand = (
                    self._get_expected_token((ExtraTokenType("("),)),
                    self._get_expression2(),
                    self._get_expected_token((ExtraTokenType(")"),)),
                )[1]
            )
        elif token1.type in _PREFIX_OPERATORS:
            expression = UnaryExpression(
                token1.source_location,
                type_ = UnaryExpressionType.PREFIX,
                operator = self._get_token().type,
                operand = self._get_expression5(),
            )
        else:
            expression = self._get_expression6()

        return expression

    def _get_expression6(self) -> Expression:
        expression = self._get_expression7()

        while True:
            token1 = self._peek_token(1)

            if token1.type in _POSTFIX_OPERATORS:
                expression = UnaryExpression(
                    expression.source_location,
                    type_ = UnaryExpressionType.POSTFIX,
                    operand = expression,
                    operator = self._get_token().type,
                )
            elif token1.type in (ExtraTokenType("."), ExtraTokenType("[")):
                expression = BinaryExpression(
                    expression.source_location,
                    operand1 = expression,
                    operator = token1.type,
                    operand2 = self._get_designator(),
                )
            elif token1.type is ExtraTokenType("("):
                expression = VariaryExpression(
                    expression.source_location,
                    operands = [expression],
                )

                self._get_token()
                arguments = []
                argument_count = 0

                while True:
                    if argument_count >= 1:
                        token0 = self._get_expected_token((ExtraTokenType(")"), ExtraTokenType(",")))

                        if token0.type is ExtraTokenType(")"):
                            break

                    token1 = self._peek_token(1)

                    if token1.type is ExtraTokenType(")"):
                        self._get_token()
                        break

                    arguments.append(self._get_expression2())
                    argument_count += 1

                expression.operands.extend(arguments)
            else:
                break

        return expression

    def _get_expression7(self) -> Expression:
        token1 = self._peek_token(1)

        if token1.type is ExtraTokenType("("):
            token2 = self._peek_token(2)

            if token2.type in (BasicTokenType.AUTO_KEYWORD, ExtraTokenType("...")
                               , ExtraTokenType(")")):
                expression = NullaryExpression(
                    token1.source_location,
                    type_ = NullaryExpressionType.FUNCTION_LITERAL,
                    data = self._get_function_literal(),
                )
            else:
                self._get_token()
                expression = self._get_expression1()
                self._get_expected_token((ExtraTokenType(")"),))
        elif token1.type is BasicTokenType.NULL_KEYWORD:
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.NULL,
                data = self._get_null(),
            )
        elif token1.type in (BasicTokenType.TRUE_KEYWORD, BasicTokenType.FALSE_KEYWORD):
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.BOOLEAN,
                data = self._get_boolean(),
            )
        elif token1.type is BasicTokenType.INTEGER_LITERAL:
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.INTEGER,
                data = self._get_integer(),
            )
        elif token1.type is BasicTokenType.FLOATING_POINT_LITERAL:
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.FLOATING_POINT,
                data = self._get_floating_point(),
            )
        elif token1.type is BasicTokenType.STRING_LITERAL:
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.STRING,
                data = self._get_string(),
            )
        elif token1.type is BasicTokenType.IDENTIFIER:
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.IDENTIFIER,
                data = self._get_identifier(),
            )
        elif token1.type is ExtraTokenType("["):
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.ARRAY_LITERAL,
                data = self._get_array_literal(),
            )
        elif token1.type is BasicTokenType.STRUCT_KEYWORD:
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.STRUCTURE_LITERAL,
                data = self._get_structure_literal(),
            )
        elif token1.type in _BUILTIN_FUNCTION_NAMES:
            expression = NullaryExpression(
                token1.source_location,
                type_ = NullaryExpressionType.BUILTIN_FUNCTION_NAME,
                data = self._get_builtin_function_name(),
            )
        else:
            self._unexpect_token(token1)

        return expression

    def _get_designator(self) -> Expression:
        token0 = self._get_expected_token((ExtraTokenType("."), ExtraTokenType("[")))

        if token0.type is ExtraTokenType("."):
            token0 = self._get_expected_token((BasicTokenType.IDENTIFIER,))

            expression = NullaryExpression(
                token0.source_location,
                type_ = NullaryExpressionType.STRING,
                data = token0.data,
            )
        else:
            expression = self._get_expression1()
            self._get_expected_token((ExtraTokenType("]"),))

        return expression

    def _get_null(self) -> None:
        self._get_expected_token((BasicTokenType.NULL_KEYWORD,))
        return None

    def _get_boolean(self) -> bool:
        token0 = self._get_expected_token((BasicTokenType.TRUE_KEYWORD
                                         , BasicTokenType.FALSE_KEYWORD))
        boolean = token0.type is BasicTokenType.TRUE_KEYWORD
        return boolean

    def _get_integer(self) -> int:
        token0 = self._get_expected_token((BasicTokenType.INTEGER_LITERAL,))
        integer = _strtoull(token0.data.encode(), None, 0)
        return integer

    def _get_floating_point(self) -> float:
        token0 = self._get_expected_token((BasicTokenType.FLOATING_POINT_LITERAL,))
        floating_point = _strtold(token0.data.encode(), None)
        return floating_point

    def _get_string(self) -> str:
        string = self._do_get_string()

        while True:
            token1 = self._peek_token(1)

            if token1.type is not BasicTokenType.STRING_LITERAL:
                break

            string += self._do_get_string()

        return string

    def _do_get_string(self) -> str:
        token0 = self._get_expected_token((BasicTokenType.STRING_LITERAL,))
        string = ""
        raw_string = token0.data[1:-1]
        i = 0

        while i < len(raw_string):
            char0 = raw_string[i]

            if char0 is "\\":
                char1 = raw_string[i + 1]

                if "\\" + char1 in utils.SIMPLE_ESCAPE_SEQUENCES:
                    n = 2
                    ascii_ = utils.SIMPLE_ESCAPE_SEQUENCE_2_ASCII["\\" + char1]
                elif char1 in utils.OCTAL_DIGITS:
                    char2 = raw_string[i + 2]
                    char3 = raw_string[i + 3]
                    n = 4
                    ascii_ = ((utils.OCTAL_DIGIT_2_VALUE[char1] << 6) \
                              | (utils.OCTAL_DIGIT_2_VALUE[char2] << 3) \
                              | utils.OCTAL_DIGIT_2_VALUE[char3]) & 0xFF
                elif char1 in ("x", "X"):
                    char2 = raw_string[i + 2]
                    char3 = raw_string[i + 3]
                    n = 4
                    ascii_ = (utils.HEX_DIGIT_2_VALUE[char2] << 4) | utils.HEX_DIGIT_2_VALUE[char3]
                else:
                    assert False

                char = chr(ascii_)
            else:
                n = 1
                char = char0

            string += char
            i += n

        return string

    def _get_identifier(self) -> str:
        token0 = self._get_expected_token((BasicTokenType.IDENTIFIER,))
        identifier = token0.data
        return identifier

    def _get_array_literal(self) -> ArrayLiteral:
        self._get_expected_token((ExtraTokenType("["),))
        self._get_expected_token((ExtraTokenType("]"),))
        self._get_expected_token((ExtraTokenType("{"),))
        elements = []
        element_count = 0

        while True:
            if element_count >= 1:
                token0 = self._get_expected_token((ExtraTokenType("}"), ExtraTokenType(",")))

                if token0.type is ExtraTokenType("}"):
                    break

            token1 = self._peek_token(1)

            if token1.type is ExtraTokenType("}"):
                self._get_token()
                break

            if token1.type is ExtraTokenType("["):
                element_index = self._get_designator()
                self._get_expected_token((ExtraTokenType("="),))
                element_value = self._get_expression2()
            else:
                element_index = None
                element_value = self._get_expression2()

            elements.append((element_index, element_value))
            element_count += 1

        return ArrayLiteral(elements)

    def _get_structure_literal(self) -> StructureLiteral:
        self._get_expected_token((BasicTokenType.STRUCT_KEYWORD,))
        self._get_expected_token((ExtraTokenType("{"),))
        fields = []
        field_count = 0

        while True:
            if field_count >= 1:
                token0 = self._get_expected_token((ExtraTokenType("}"), ExtraTokenType(",")))

                if token0.type is ExtraTokenType("}"):
                    break

            token1 = self._peek_token(1)

            if token1.type is ExtraTokenType("}"):
                self._get_token()
                break

            field_name = self._get_designator()
            self._get_expected_token((ExtraTokenType("="),))
            field_value = self._get_expression2()
            fields.append((field_name, field_value))
            field_count += 1

        return StructureLiteral(fields)

    def _get_function_literal(self) -> FunctionLiteral:
        self._get_expected_token((ExtraTokenType("("),))
        parameters1 = []
        parameters2 = []
        parameter_count1 = 0
        parameter_count2 = 0
        rest_parameter = None

        while True:
            if parameter_count1 + parameter_count2 >= 1:
                token0 = self._get_expected_token((ExtraTokenType(")"), ExtraTokenType(",")))

                if token0.type is ExtraTokenType(")"):
                    break

            token1 = self._peek_token(1)

            if token1.type is ExtraTokenType(")"):
                self._get_token()
                break

            self._get_expected_token((BasicTokenType.AUTO_KEYWORD,))
            token1 = self._peek_token(1)

            if token1.type is ExtraTokenType("..."):
                self._get_token()
                rest_parameter = self._get_user_defined_name()
                self._get_expected_token((ExtraTokenType(")"),))
                break

            parameter = self._get_user_defined_name()

            if parameter_count2 == 0:
                token1 = self._peek_token(1)

                if token1.type is ExtraTokenType("="):
                    self._get_token()
                    default_argument = self._get_expression2()
                    parameters2.append((parameter, default_argument))
                    parameter_count2 += 1
                else:
                    parameters1.append(parameter)
                    parameter_count1 += 1
            else:
                self._get_expected_token((ExtraTokenType("="),))
                default_argument = self._get_expression2()
                parameters2.append((parameter, default_argument))
                parameter_count2 += 1

        with self._reset_context():
            body = self._get_block_statement()

        return FunctionLiteral(parameters1, parameters2, rest_parameter, body)

    def _get_builtin_function_name(self) -> BasicTokenType:
        token0 = self._get_expected_token(_BUILTIN_FUNCTION_NAMES)

        builtin_function_name = token0.type
        return builtin_function_name

    def _get_user_defined_name(self) -> NullaryExpression:
        token0 = self._get_expected_token((BasicTokenType.IDENTIFIER,))

        expression = NullaryExpression(
            token0.source_location,
            type_ = NullaryExpressionType.IDENTIFIER,
            data = token0.data,
        )

        return expression

    def _get_expected_token(self, expected_token_types: typing.Iterable[TokenType]) -> Token:
        token = self._get_token()

        if not token.type in expected_token_types:
            self._unget_token(token)
            self._unexpect_token(token, expected_token_types)

        return token

    def _get_token(self) -> Token:
        if len(self._token_buffer) == 0:
            token = self._do_get_token()
        else:
            token = self._token_buffer.popleft()

        if token.type is BasicTokenType.NO:
            raise EndOfFileError(token.source_location)

        return token

    def _do_get_token(self) -> Token:
        while True:
            token = self._scanner.get_token()

            if not token.type in (BasicTokenType.COMMENT, BasicTokenType.WHITE_SPACE):
                break

        return token

    def _unget_token(self, token: Token) -> None:
        self._token_buffer.append(token)

    def _peek_token(self, position: int) -> Token:
        assert position >= 1

        while len(self._token_buffer) < position:
            token = self._do_get_token()

            if token.type is BasicTokenType.NO:
                return token

            self._token_buffer.append(token)

        token = self._token_buffer[position - 1]
        return token

    def _unexpect_token(self, token: Token
                        , expected_token_types: typing.Iterable[TokenType] = ()) -> typing.NoReturn:
        raise UnexpectedTokenError(token.source_location, token.data, expected_token_types)


class _ParserContext(typing.NamedTuple):
    break_statement_is_allowed: bool = False;
    continue_statement_is_allowed: bool = False;


_ASSIGNMENT_OPERATORS: typing.Set[ExtraTokenType] = {
    ExtraTokenType("="),
    ExtraTokenType("+="), ExtraTokenType("-="),
    ExtraTokenType("*="), ExtraTokenType("/="), ExtraTokenType("%="),
    ExtraTokenType("<<="), ExtraTokenType(">>="),
    ExtraTokenType("&="), ExtraTokenType("^="), ExtraTokenType("|="),
}

_CONVERSION_OPERATORS: typing.Set[BasicTokenType] = {
    BasicTokenType.BOOL_KEYWORD,
    BasicTokenType.INT_KEYWORD,
    BasicTokenType.FLOAT_KEYWORD,
    BasicTokenType.STR_KEYWORD,
    BasicTokenType.SIZEOF_KEYWORD,
    BasicTokenType.TYPEOF_KEYWORD,
}

_PREFIX_OPERATORS: typing.Set[ExtraTokenType] = {
    ExtraTokenType("++"), ExtraTokenType("--"),
    ExtraTokenType("+"), ExtraTokenType("-"),
    ExtraTokenType("!"), ExtraTokenType("~"),
}

_POSTFIX_OPERATORS: typing.Set[ExtraTokenType] = {
    ExtraTokenType("++"), ExtraTokenType("--"),
}

def _OPERATOR_PRECEDENCES() -> typing.Dict[ExtraTokenType, int]:
    counter = utils.make_counter(0)

    return {
        ExtraTokenType("||"): counter(1),

        ExtraTokenType("&&"): counter(1),

        ExtraTokenType("|"): counter(1),

        ExtraTokenType("^"): counter(1),

        ExtraTokenType("&"): counter(1),

        ExtraTokenType("=="): counter(1),
        ExtraTokenType("!="): counter(0),

        ExtraTokenType("<"): counter(1),
        ExtraTokenType("<="): counter(0),
        ExtraTokenType(">"): counter(0),
        ExtraTokenType(">="): counter(0),

        ExtraTokenType("<<"): counter(1),
        ExtraTokenType(">>"): counter(0),

        ExtraTokenType("+"): counter(1),
        ExtraTokenType("-"): counter(0),

        ExtraTokenType("*"): counter(1),
        ExtraTokenType("/"): counter(0),
        ExtraTokenType("%"): counter(0),
    }

_OPERATOR_PRECEDENCES = _OPERATOR_PRECEDENCES()

_BUILTIN_FUNCTION_NAMES = {
    BasicTokenType.TRACE_KEYWORD,
    BasicTokenType.REQUIRE_KEYWORD,
}

def _strtoull():
    libc = ctypes.CDLL("libc.so.6")
    strtoull = libc.strtoull
    strtoull.argtypes = (ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int)
    strtoull.restype = ctypes.c_ulonglong
    return strtoull

_strtoull = _strtoull()

def _strtold():
    libc = ctypes.CDLL("libc.so.6")
    strtold = libc.strtold
    strtold.argtypes = (ctypes.c_char_p, ctypes.c_void_p)
    strtold.restype = ctypes.c_longdouble
    return strtold

_strtold = _strtold()
