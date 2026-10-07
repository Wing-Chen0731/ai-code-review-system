from packages.context.chunker import CodeChunker


def test_chunker_prefers_functions_and_has_line_metadata():
    chunks = CodeChunker().chunk("app.py", "def first():\n    return 1\n\ndef second():\n    return 2\n")
    assert chunks
    assert any(chunk.symbol_name == "first" for chunk in chunks)
    assert all(chunk.start_line <= chunk.end_line for chunk in chunks)
