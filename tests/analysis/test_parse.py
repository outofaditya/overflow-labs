from source.analysis.parse import parse_body


# test that a single code block is extracted
def test_one_code_block_is_extracted() -> None:
    prose, code = parse_body(
        "<p>Try this:</p><pre><code>x = 1</code></pre><p>Did it work?</p>"
    )
    assert code == ["x = 1"]
    assert "x = 1" not in prose
    assert "Try this:" in prose and "Did it work?" in prose


# test that multiple code blocks are extracted in order
def test_multiple_code_blocks_preserve_order() -> None:
    _, code = parse_body(
        "<p>First:</p><pre><code>a = 1</code></pre>"
        "<p>Then:</p><pre><code>b = 2</code></pre>"
    )
    assert code == ["a = 1", "b = 2"]


# test that inline code stays in the prose
def test_inline_code_stays_in_prose() -> None:
    prose, code = parse_body("<p>Use the <code>print()</code> function.</p>")
    assert code == []
    assert "print()" in prose


# test that no code blocks returns an empty list
def test_no_code_blocks_returns_empty_list() -> None:
    prose, code = parse_body("<p>Just a plain question with no code.</p>")
    assert code == []
    assert "plain question" in prose


# test that an empty body returns an empty tuple
def test_empty_body_returns_empty_tuple() -> None:
    assert parse_body("") == ("", [])
    assert parse_body(None) == ("", [])
