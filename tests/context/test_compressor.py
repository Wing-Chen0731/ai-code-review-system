from packages.context.compressor import ContextCompressor, estimate_tokens


def test_compressor_prioritizes_changed_context_and_obeys_budget():
    chunks = [
        {"reference_type": "retrieved", "content": "z" * 100},
        {"reference_type": "changed", "content": "important"},
    ]
    result = ContextCompressor().compress(chunks, max_tokens=3)
    assert result[0]["reference_type"] == "changed"
    assert sum(estimate_tokens(item["content"]) for item in result) <= 3
