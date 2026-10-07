from packages.context.ast_analyzer import ASTAnalyzer


def test_ast_symbols_imports_and_call_graph():
    source = "import os\n\ndef helper():\n    return os.getcwd()\n\ndef main():\n    return helper()\n"
    table = ASTAnalyzer(source, "app.py").symbol_table()
    assert "os" in table.imports
    assert {symbol.name for symbol in table.symbols.values()} >= {"helper", "main"}
    assert "helper" in table.call_graph["main"]
    assert "main" in table.reverse_call_graph["helper"]
