import py7zr
import pytest
from pathlib import Path
from source.extract import _verify_xml, extract


def _make_archive(tmp_path: Path, xml_bytes: bytes, xml_name: str = "test.xml") -> Path:
    xml_path = tmp_path / xml_name
    xml_path.write_bytes(xml_bytes)
    archive = tmp_path / "test.7z"
    with py7zr.SevenZipFile(archive, "w") as z:
        z.write(xml_path, arcname=xml_name)
    xml_path.unlink()  # remove source so we can prove extraction recreated it
    return archive


def test_extract_decompresses_xml(tmp_path: Path) -> None:
    content = b'<?xml version="1.0"?><posts><row Id="1" PostTypeId="1"/></posts>'
    archive = _make_archive(tmp_path, content)
    out_dir = tmp_path / "out"

    result = extract(archive, out_dir=out_dir)

    assert result.is_file()
    assert result.read_bytes() == content


def test_extract_skips_when_xml_already_exists(tmp_path: Path) -> None:
    content = b'<?xml version="1.0"?><posts><row Id="1"/></posts>'
    archive = _make_archive(tmp_path, content)
    out_dir = tmp_path / "out"

    first = extract(archive, out_dir=out_dir)
    mtime_first = first.stat().st_mtime

    second = extract(archive, out_dir=out_dir)
    assert second == first
    assert second.stat().st_mtime == mtime_first  # not re-extracted


def test_verify_xml_rejects_empty_file(tmp_path: Path) -> None:
    empty = tmp_path / "empty.xml"
    empty.write_text("")
    with pytest.raises(RuntimeError, match="empty"):
        _verify_xml(empty)


def test_verify_xml_rejects_missing_row(tmp_path: Path) -> None:
    bad = tmp_path / "norow.xml"
    bad.write_bytes(b'<?xml version="1.0"?><posts></posts>')
    with pytest.raises(RuntimeError, match="No <row>"):
        _verify_xml(bad)


def test_extract_with_targets_filters(tmp_path: Path) -> None:
    posts = b'<?xml version="1.0"?><posts><row Id="1" /></posts>'
    users = b'<?xml version="1.0"?><users><row Id="1" /></users>'
    posts_path = tmp_path / "Posts.xml"
    users_path = tmp_path / "Users.xml"
    posts_path.write_bytes(posts)
    users_path.write_bytes(users)
    archive = tmp_path / "multi.7z"
    with py7zr.SevenZipFile(archive, "w") as z:
        z.write(posts_path, arcname="Posts.xml")
        z.write(users_path, arcname="Users.xml")
    posts_path.unlink()
    users_path.unlink()

    out = tmp_path / "out"
    result = extract(archive, out_dir=out, targets=["Posts.xml"])

    assert result.name == "Posts.xml"
    assert (out / "Posts.xml").is_file()
    assert not (out / "Users.xml").is_file()


def test_extract_with_unknown_target_raises(tmp_path: Path) -> None:
    xml = b'<?xml version="1.0"?><posts><row Id="1" /></posts>'
    archive = _make_archive(tmp_path, xml, xml_name="Posts.xml")
    with pytest.raises(RuntimeError, match="Not Found"):
        extract(archive, out_dir=tmp_path / "out", targets=["DoesNotExist.xml"])
