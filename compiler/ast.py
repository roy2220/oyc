__all__ = (
    "ASTVisitor",
    "ASTNode",
)


from .source_location import SourceLocation


class ASTVisitor:
    def visit_nullary_expression(self, expression: "expression.NullaryExpression") -> None:
        raise NotImplementedError()

    def visit_unary_expression(self, expression: "expression.UnaryExpression") -> None:
        raise NotImplementedError()

    def visit_binary_expression(self, expression: "expression.BinaryExpression") -> None:
        raise NotImplementedError()

    def visit_ternary_expression(self, expression: "expression.TernaryExpression") -> None:
        raise NotImplementedError()

    def visit_variary_expression(self, expression: "expression.VariaryExpression") -> None:
        raise NotImplementedError()

    def visit_null_statement(self, statement: "statement.NullStatement") -> None:
        raise NotImplementedError()

    def visit_block_statement(self, statement: "statement.BlockStatement") -> None:
        raise NotImplementedError()

    def visit_auto_statement(self, statement: "statement.AutoStatement") -> None:
        raise NotImplementedError()

    def visit_return_statement(self, statement: "statement.ReturnStatement") -> None:
        raise NotImplementedError()

    def visit_delete_statement(self, statement: "statement.DeleteStatement") -> None:
        raise NotImplementedError()

    def visit_break_statement(self, statement: "statement.BreakStatement") -> None:
        raise NotImplementedError()

    def visit_continue_statement(self, statement: "statement.ContinueStatement") -> None:
        raise NotImplementedError()

    def visit_if_statement(self, statement: "statement.IfStatement") -> None:
        raise NotImplementedError()

    def visit_switch_statement(self, statement: "statement.SwitchStatement") -> None:
        raise NotImplementedError()

    def visit_switch_clause(self, switch_clause: "statement.SwitchClause") -> None:
        raise NotImplementedError()

    def visit_while_statement(self, statement: "statement.WhileStatement") -> None:
        raise NotImplementedError()

    def visit_do_while_statement(self, statement: "statement.DoWhileStatement") -> None:
        raise NotImplementedError()

    def visit_for_statement(self, statement: "statement.ForStatement") -> None:
        raise NotImplementedError()

    def visit_foreach_statement(self, statement: "statement.ForeachStatement") -> None:
        raise NotImplementedError()

    def visit_expression_statement(self, statement: "statement.ExpressionStatement") -> None:
        raise NotImplementedError()


class ASTNode:
    __slots__ = (
        "_source_location",
    )

    def __init__(self, source_location: SourceLocation) -> None:
        self._source_location = source_location

    @property
    def source_location(self) -> SourceLocation:
        return self._source_location

    def accept_visit(self, visitor: ASTVisitor) -> None:
        raise NotImplementedError()


from . import expression
from . import statement
