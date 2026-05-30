from pathlib import Path
from source.ingestion.manifest import sha256_of


def test_sha256_of_known_input(tmp_path: Path) -> None:
    p = tmp_path / "hello.bin"
    p.write_bytes(b"hello world")
    # sha256("hello world") is a well-known constant.
    expected = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert sha256_of(p) == expected
