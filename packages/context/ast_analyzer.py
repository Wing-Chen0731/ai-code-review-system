"""Python AST symbol, import and call-graph extraction."""

import ast
from dataclasses import dataclass, field


@dataclass
class Symbol:
    name: str
    type: str
    start_line: int
    end_line: int
    parent: str | None = None
    dependencies: list[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return self.type

    @property
    def qualified_name(self) -> str:
        return f"{self.parent}.{self.name}" if self.parent else self.name


@dataclass
class SymbolTable:
    symbols: dict[str, Symbol]
    call_graph: dict[str, list[str]]
    reverse_call_graph: dict[str, list[str]]
    imports: dict[str, str] = field(default_factory=dict)

    def find_callers(self, function_name: str) -> list[str]:
        return self.reverse_call_graph.get(function_name, [])

    def find_callees(self, function_name: str) -> list[str]:
        return self.call_graph.get(function_name, [])


class ASTAnalyzer(ast.NodeVisitor):
    def __init__(self, content: str | None = None, file_path: str | None = None):
        self.symbols: list[Symbol] = []
        self.imports: dict[str, str] = {}
        self.calls: list[dict[str, str | int]] = []
        self.current_class: str | None = None
        self._function_stack: list[str] = []
        self.file_path = file_path
        if content is not None:
            self.visit(ast.parse(content, filename=file_path or "<string>"))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name.split(".")[0]
            self.imports[name] = alias.name
            self.symbols.append(Symbol(name, "import", node.lineno, node.end_lineno or node.lineno, dependencies=[alias.name]))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}".strip(".")
            name = alias.asname or alias.name
            self.imports[name] = full_name
            self.symbols.append(Symbol(name, "import", node.lineno, node.end_lineno or node.lineno, dependencies=[full_name]))

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        bases = [base.id for base in node.bases if isinstance(base, ast.Name)]
        self.symbols.append(Symbol(node.name, "class", node.lineno, node.end_lineno or node.lineno, dependencies=bases))
        previous = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = previous

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node)

    def _handle_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualified = f"{self.current_class}.{node.name}" if self.current_class else node.name
        dependencies = [arg.arg for arg in [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs]]
        self.symbols.append(Symbol(node.name, "function", node.lineno, node.end_lineno or node.lineno, self.current_class, dependencies))
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                callee = self._call_name(child.func)
                if callee:
                    self.calls.append({"caller": qualified, "callee": callee, "line": child.lineno})
        previous = self._function_stack[-1] if self._function_stack else None
        self._function_stack.append(qualified)
        self.generic_visit(node)
        self._function_stack.pop()
        if previous is not None and self._function_stack and self._function_stack[-1] != previous:
            self._function_stack[-1] = previous

    @staticmethod
    def _call_name(node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts: list[str] = []
            current: ast.AST | None = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None

    def symbol_table(self) -> SymbolTable:
        symbols = {symbol.name: symbol for symbol in self.symbols if symbol.type in {"function", "class"}}
        call_graph: dict[str, list[str]] = {}
        reverse: dict[str, list[str]] = {}
        for call in self.calls:
            caller, callee = str(call["caller"]), str(call["callee"])
            call_graph.setdefault(caller, []).append(callee)
            reverse.setdefault(callee, []).append(caller)
        return SymbolTable(symbols, call_graph, reverse, dict(self.imports))


def analyze_file(content: str, file_path: str | None = None) -> ASTAnalyzer:
    return ASTAnalyzer(content, file_path)
