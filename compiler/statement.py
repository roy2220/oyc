__all__ = (
    "Statement",
    "ExpressionStatement",
    "NullStatement",
    "BlockStatement",
    "AutoStatement",
    "ReturnStatement",
    "DeleteStatement",
    "BreakStatement",
    "ContinueStatement",
    "IfStatement",
    "SwitchClause",
    "SwitchStatement",
    "WhileStatement",
    "DoWhileStatement",
    "ForStatement",
    "ForeachStatement",
)


import typing

from .ast import *
from .source_location import SourceLocation


class Statement(ASTNode):
    pass


class ExpressionStatement(Statement):
    __slots__ = (
        "_expression",
    )

    def __init__(self, source_location: SourceLocation, *
                 , expression: "expression.Expression") -> None:
        super().__init__(source_location)
        self._expression = expression

    @property
    def expression(self) -> "expression.Expression":
        return self._expression

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_expression_statement(self)


class NullStatement(Statement):
    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_null_statement(self)


class BlockStatement(Statement):
    __slots__ = (
        "_statements",
    )

    def __init__(self, source_location: SourceLocation, *
                 , statements: typing.List[Statement]) -> None:
        super().__init__(source_location)
        self._statements = statements

    @property
    def statements(self) -> typing.List[Statement]:
        return self._statements

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_block_statement(self)


class AutoStatement(Statement):
    __slots__ = (
        "_variables",
    )

    def __init__(self, source_location: SourceLocation, *, variables: typing.List[typing.Tuple[
        "expression.NullaryExpression",
        typing.Optional["expression.Expression"]
    ]]) -> None:
        super().__init__(source_location)
        self._variables = variables

    @property
    def variables(self) -> typing.List[typing.Tuple[
        "expression.NullaryExpression",
        typing.Optional["expression.Expression"]
    ]]:
        return self._variables

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_auto_statement(self)


class ReturnStatement(Statement):
    __slots__ = (
        "_expression",
    )

    def __init__(self, source_location: SourceLocation, *
                 , expression: typing.Optional["expression.Expression"]) -> None:
        super().__init__(source_location)
        self._expression = expression

    @property
    def expression(self) -> typing.Optional["expression.Expression"]:
        return self._expression

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_return_statement(self)


class DeleteStatement(Statement):
    __slots__ = (
        "_element_or_field",
    )

    def __init__(self, source_location: SourceLocation, *
                 , element_or_field: typing.Tuple["expression.Expression"
                                                  , "expression.Expression"]) -> None:
        super().__init__(source_location)
        self._element_or_field = element_or_field

    @property
    def element_or_field(self) -> typing.Tuple["expression.Expression", "expression.Expression"]:
        return self._element_or_field

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_delete_statement(self)


class BreakStatement(Statement):
    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_break_statement(self)


class ContinueStatement(Statement):
    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_continue_statement(self)


class IfStatement(Statement):
    __slots__ = (
        "_initialization",
        "_condition",
        "_then_body",
        "_else_body",
    )

    def __init__(self, source_location: SourceLocation, *
                 , initialization: typing.Optional[AutoStatement]
                 , condition: "expression.Expression"
                 , then_body: Statement
                 , else_body: typing.Optional[Statement]) -> None:
        super().__init__(source_location)
        self._initialization = initialization
        self._condition = condition
        self._then_body = then_body
        self._else_body = else_body

    @property
    def initialization(self) -> typing.Optional[AutoStatement]:
        return self._initialization

    @property
    def condition(self) -> "expression.Expression":
        return self._condition

    @property
    def then_body(self) -> Statement:
        return self._then_body

    @property
    def else_body(self) -> typing.Optional[Statement]:
        return self._else_body

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_if_statement(self)


class SwitchClause(ASTNode):
    __slots__ = (
        "_label",
        "_statements",
    )

    def __init__(self, source_location: SourceLocation, *
                 , label: typing.Optional["expression.Expression"]
                 , statements: typing.List[Statement]) -> None:
        super().__init__(source_location)
        self._label = label
        self._statements = statements

    @property
    def label(self) -> typing.Optional["expression.Expression"]:
        return self._label

    @property
    def statements(self) -> typing.List[Statement]:
        return self._statements

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_switch_clause(self)


class SwitchStatement(Statement):
    __slots__ = (
        "_initialization",
        "_expression",
        "_clauses",
    )

    def __init__(self, source_location: SourceLocation, *
                 , initialization: typing.Optional[AutoStatement]
                 , expression: "expression.Expression"
                 , clauses: typing.List[SwitchClause]) -> None:
        super().__init__(source_location)
        self._initialization = initialization
        self._expression = expression
        self._clauses = clauses

    @property
    def initialization(self) -> typing.Optional[AutoStatement]:
        return self._initialization

    @property
    def expression(self) -> "expression.Expression":
        return self._expression

    @property
    def clauses(self) -> typing.List[SwitchClause]:
        return self._clauses

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_switch_statement(self)


class WhileStatement(Statement):
    __slots__ = (
        "_initialization",
        "_condition",
        "_body",
    )

    def __init__(self, source_location: SourceLocation, *
                 , initialization: typing.Optional[AutoStatement]
                 , condition: "expression.Expression"
                 , body: Statement) -> None:
        super().__init__(source_location)
        self._initialization = initialization
        self._condition = condition
        self._body = body

    @property
    def initialization(self) -> typing.Optional[AutoStatement]:
        return self._initialization

    @property
    def condition(self) -> "expression.Expression":
        return self._condition

    @property
    def body(self) -> Statement:
        return self._body

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_while_statement(self)


class DoWhileStatement(Statement):
    __slots__ = (
        "_body",
        "_initialization",
        "_condition",
    )

    def __init__(self, source_location: SourceLocation, *
                 , body: Statement
                 , initialization: typing.Optional[AutoStatement]
                 , condition: "expression.Expression") -> None:
        super().__init__(source_location)
        self._body = body
        self._initialization = initialization
        self._condition = condition

    @property
    def body(self) -> Statement:
        return self._body

    @property
    def initialization(self) -> typing.Optional[AutoStatement]:
        return self._initialization

    @property
    def condition(self) -> "expression.Expression":
        return self._condition

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_do_while_statement(self)


class ForStatement(Statement):
    __slots__ = (
        "_initialization",
        "_condition",
        "_iteration",
        "_body",
    )

    def __init__(self, source_location: SourceLocation, *
                 , initialization: typing.Optional[typing.Union[AutoStatement, ExpressionStatement]]
                 , condition: typing.Optional["expression.Expression"]
                 , iteration: typing.Optional[ExpressionStatement], body: Statement) -> None:
        super().__init__(source_location)
        self._initialization = initialization
        self._condition = condition
        self._iteration = iteration
        self._body = body

    @property
    def initialization(self) -> typing.Optional[typing.Union[AutoStatement, ExpressionStatement]]:
        return self._initialization

    @property
    def condition(self) -> typing.Optional["expression.Expression"]:
        return self._condition

    @property
    def iteration(self) -> typing.Optional[ExpressionStatement]:
        return self._iteration

    @property
    def body(self) -> Statement:
        return self._body

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_for_statement(self)


class ForeachStatement(Statement):
    __slots__ = (
        "_iterator_name1",
        "_iterator_name2",
        "_container",
        "_body",
    )

    def __init__(self, source_location: SourceLocation, *
                 , iterator_name1: "expression.NullaryExpression"
                 , iterator_name2: typing.Optional["expression.NullaryExpression"]
                 , container: "expression.Expression"
                 , body: Statement) -> None:
        super().__init__(source_location)
        self._iterator_name1 = iterator_name1
        self._iterator_name2 = iterator_name2
        self._container = container
        self._body = body

    @property
    def iterator_name1(self) -> "expression.NullaryExpression":
        return self._iterator_name1

    @property
    def iterator_name2(self) -> typing.Optional["expression.NullaryExpression"]:
        return self._iterator_name2

    @property
    def container(self) -> "expression.Expression":
        return self._container

    @property
    def body(self) -> Statement:
        return self._body

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_foreach_statement(self)


from . import expression
