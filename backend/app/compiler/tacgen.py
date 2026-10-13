"""TAC generation: typed AST -> three-address code.

Requires an AST that passed semantic analysis (every expression is typed and
every name is resolved to a unique symbol).
"""

from __future__ import annotations

from . import ast_nodes as ast
from .tac import BinOp, Const, Copy, Goto, IfFalse, IfTrue, Instr, Label, Operand, Print, UnOp, Var
from .typesys import Type


class TacGenerator:
    def __init__(self) -> None:
        self.code: list[Instr] = []
        self._temps = 0
        self._labels = 0

    def new_temp(self, type_: Type) -> Var:
        self._temps += 1
        return Var(f"t{self._temps}", type_, temp=True)

    def new_label(self) -> str:
        self._labels += 1
        return f"L{self._labels}"

    def emit(self, instr: Instr) -> None:
        self.code.append(instr)

    # -- statements ------------------------------------------------------
    def program(self, program: ast.Program) -> list[Instr]:
        for stmt in program.statements:
            self.stmt(stmt)
        return self.code

    def stmt(self, stmt: ast.Stmt) -> None:
        if isinstance(stmt, (ast.LetStmt, ast.AssignStmt)):
            assert stmt.symbol and stmt.var_type, "statement was not analyzed"
            value = self.coerce(self.expr(stmt.value), stmt.var_type)
            self.emit(Copy(Var(stmt.symbol, stmt.var_type), value))
        elif isinstance(stmt, ast.PrintStmt):
            self.emit(Print(tuple(self.expr(arg) for arg in stmt.args)))
        elif isinstance(stmt, ast.Block):
            for inner in stmt.statements:
                self.stmt(inner)
        elif isinstance(stmt, ast.IfStmt):
            self.if_stmt(stmt)
        elif isinstance(stmt, ast.WhileStmt):
            self.while_stmt(stmt)
        else:  # pragma: no cover
            raise TypeError(f"unknown statement {type(stmt).__name__}")

    def if_stmt(self, stmt: ast.IfStmt) -> None:
        cond = self.expr(stmt.condition)
        else_label = self.new_label()
        self.emit(IfFalse(cond, else_label))
        self.stmt(stmt.then_block)
        if stmt.else_branch is None:
            self.emit(Label(else_label))
            return
        end_label = self.new_label()
        self.emit(Goto(end_label))
        self.emit(Label(else_label))
        self.stmt(stmt.else_branch)
        self.emit(Label(end_label))

    def while_stmt(self, stmt: ast.WhileStmt) -> None:
        start, end = self.new_label(), self.new_label()
        self.emit(Label(start))
        cond = self.expr(stmt.condition)
        self.emit(IfFalse(cond, end))
        self.stmt(stmt.body)
        self.emit(Goto(start))
        self.emit(Label(end))

    # -- expressions -----------------------------------------------------
    def coerce(self, operand: Operand, target: Type) -> Operand:
        """Insert an explicit int -> float conversion when needed."""
        if target is Type.FLOAT and operand.type is Type.INT:
            temp = self.new_temp(Type.FLOAT)
            self.emit(UnOp(temp, "itof", operand))
            return temp
        return operand

    def expr(self, expr: ast.Expr) -> Operand:
        assert expr.type is not None, "expression was not analyzed"
        if isinstance(expr, ast.IntLiteral):
            return Const(expr.value, Type.INT)
        if isinstance(expr, ast.FloatLiteral):
            return Const(expr.value, Type.FLOAT)
        if isinstance(expr, ast.StringLiteral):
            return Const(expr.value, Type.STRING)
        if isinstance(expr, ast.BoolLiteral):
            return Const(expr.value, Type.BOOL)
        if isinstance(expr, ast.Name):
            assert expr.symbol is not None
            return Var(expr.symbol, expr.type)
        if isinstance(expr, ast.Unary):
            operand = self.expr(expr.operand)
            temp = self.new_temp(expr.type)
            self.emit(UnOp(temp, expr.op, operand))
            return temp
        if isinstance(expr, ast.Binary):
            if expr.op in ("and", "or"):
                return self.short_circuit(expr)
            left = self.expr(expr.left)
            right = self.expr(expr.right)
            if left.type.is_numeric and right.type.is_numeric and left.type != right.type:
                left = self.coerce(left, Type.FLOAT)
                right = self.coerce(right, Type.FLOAT)
            temp = self.new_temp(expr.type)
            self.emit(BinOp(temp, expr.op, left, right))
            return temp
        raise TypeError(f"unknown expression {type(expr).__name__}")  # pragma: no cover

    def short_circuit(self, expr: ast.Binary) -> Operand:
        """``a and b`` / ``a or b`` only evaluate ``b`` when it can change the result."""
        result = self.new_temp(Type.BOOL)
        skip = self.new_label()
        self.expr_into(expr.left, result)
        self.emit((IfFalse if expr.op == "and" else IfTrue)(result, skip))
        self.expr_into(expr.right, result)
        self.emit(Label(skip))
        return result

    def expr_into(self, expr: ast.Expr, dest: Var) -> None:
        """Evaluate ``expr`` directly into ``dest`` instead of via an extra copy."""
        value = self.expr(expr)
        last = self.code[-1] if self.code else None
        if isinstance(value, Var) and value.temp and isinstance(last, (BinOp, UnOp)) \
                and last.dest == value:
            if isinstance(last, BinOp):
                self.code[-1] = BinOp(dest, last.op, last.left, last.right)
            else:
                self.code[-1] = UnOp(dest, last.op, last.operand)
            return
        self.emit(Copy(dest, value))


def generate_tac(program: ast.Program) -> list[Instr]:
    return TacGenerator().program(program)
