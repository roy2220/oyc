__all__ = (
    "Expression",
    "NullaryExpressionType",
    "NullaryExpressionData",
    "NullaryExpression",
    "UnaryExpressionType",
    "UnaryExpression",
    "BinaryExpression",
    "TernaryExpression",
    "VariaryExpression",
    "ArrayLiteral",
    "StructureLiteral",
    "FunctionLiteral",
)


import enum
import typing

from .ast import *
from .source_location import SourceLocation
from .token import BasicTokenType, TokenType


class Expression(ASTNode):
    pass


class NullaryExpressionType(enum.IntEnum):
    NULL = enum.auto()
    BOOLEAN = enum.auto()
    INTEGER = enum.auto()
    FLOATING_POINT = enum.auto()
    STRING = enum.auto()
    IDENTIFIER = enum.auto()

    ARRAY_LITERAL = enum.auto()
    STRUCTURE_LITERAL = enum.auto()
    FUNCTION_LITERAL = enum.auto()

    BUILTIN_FUNCTION_NAME = enum.auto()


class ArrayLiteral(typing.NamedTuple):
    elements: typing.List[typing.Tuple[Expression, typing.Optional[Expression]]]


class StructureLiteral(typing.NamedTuple):
    fields: typing.List[typing.Tuple[Expression, Expression]]


class FunctionLiteral(typing.NamedTuple):
    parameters1: typing.List["NullaryExpression"]
    parameters2: typing.List[typing.Tuple["NullaryExpression", Expression]]
    rest_parameter: typing.Optional["NullaryExpression"]
    body: "statement.BlockStatement"


NullaryExpressionData = typing.Union[
    None,
    bool,
    int,
    float,
    str,
    ArrayLiteral,
    StructureLiteral,
    FunctionLiteral,
    BasicTokenType,
]


class NullaryExpression(Expression):
    __slots__ = (
        "_type",
        "_data",
    )

    def __init__(self, source_location: SourceLocation, *, type_: NullaryExpressionType
                 , data: NullaryExpressionData) -> None:
        super().__init__(source_location)
        self._type = type_
        self._data = data

    @property
    def type(self) -> NullaryExpressionType:
        return self._type

    @property
    def data(self) -> NullaryExpressionData:
        return self._data

    @data.setter
    def data(self, value: NullaryExpressionData) -> None:
        self._data = value

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_nullary_expression(self)


class UnaryExpressionType(enum.IntEnum):
    CONVERSION = enum.auto()
    PREFIX = enum.auto()
    POSTFIX = enum.auto()


class UnaryExpression(Expression):
    __slots__ = (
        "_type",
        "_operator",
        "_operand",
    )

    def __init__(self, source_location: SourceLocation, *, type_: UnaryExpressionType
                 , operator: TokenType, operand: Expression) -> None:
        super().__init__(source_location)
        self._type = type_
        self._operator = operator
        self._operand = operand

    @property
    def type(self) -> UnaryExpressionType:
        return self._type

    @property
    def operator(self) -> TokenType:
        return self._operator

    @property
    def operand(self) -> Expression:
        return self._operand

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_unary_expression(self)


class BinaryExpression(Expression):
    __slots__ = (
        "_operator",
        "_operand1",
        "_operand2",
    )

    def __init__(self, source_location: SourceLocation, *, operator: TokenType
                 , operand1: Expression, operand2: Expression) -> None:
        super().__init__(source_location)
        self._operator = operator
        self._operand1 = operand1
        self._operand2 = operand2

    @property
    def operator(self) -> TokenType:
        return self._operator

    @property
    def operand1(self) -> Expression:
        return self._operand1

    @property
    def operand2(self) -> Expression:
        return self._operand2

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_binary_expression(self)


class TernaryExpression(Expression):
    __slots__ = (
        "_operator1",
        "_operator2",
        "_operand1",
        "_operand2",
        "_operand3",
    )

    def __init__(self, source_location: SourceLocation, *, operator1: TokenType
                 , operator2: TokenType, operand1: Expression, operand2: Expression
                 , operand3: Expression) -> None:
        super().__init__(source_location)
        self._operator1 = operator1
        self._operator2 = operator2
        self._operand1 = operand1
        self._operand2 = operand2
        self._operand3 = operand3

    @property
    def operator1(self) -> TokenType:
        return self._operator1

    @property
    def operator2(self) -> TokenType:
        return self._operator2

    @property
    def operand1(self) -> Expression:
        return self._operand1

    @property
    def operand2(self) -> Expression:
        return self._operand2

    @property
    def operand3(self) -> Expression:
        return self._operand3

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_ternary_expression(self)


class VariaryExpression(Expression):
    __slots__ = (
        "_operands",
    )

    def __init__(self, source_location: SourceLocation, *
                 , operands: typing.List[Expression]) -> None:
        super().__init__(source_location)
        self.operands = operands

    def accept_visit(self, visitor: ASTVisitor) -> None:
        visitor.visit_variary_expression(self)


from . import statement
