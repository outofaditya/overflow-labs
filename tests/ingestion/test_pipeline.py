import py7zr
import pytest
from pathlib import Path
from source import constants
import pyarrow.parquet as pq
from source.ingestion.pipeline import ingest_all, ingest_table


# build a single multi-xml archive in the test raw dir
def _make_archive(raw_dir: Path, contents: dict[str, bytes]) -> Path:
    written = []
    for name, body in contents.items():
        p = raw_dir / name
        p.write_bytes(body)
        written.append((p, name))
    archive_path = raw_dir / "stackoverflow.com-test.7z"
    with py7zr.SevenZipFile(archive_path, "w") as z:
        for p, name in written:
            z.write(p, arcname=name)
    for p, _ in written:
        p.unlink()
    return archive_path


# use a fake disk root for raw and processed constants
@pytest.fixture
def fake_ssd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    raw = tmp_path / "raw"
    processed = tmp_path / "processed"
    raw.mkdir()
    processed.mkdir()
    monkeypatch.setattr(constants, "RAW", raw)
    monkeypatch.setattr(constants, "PROCESSED", processed)
    return tmp_path


# verify successful table ingest writes parquet, deletes the xml, keeps the .7z
def test_ingest_table_writes_parquet_and_cleans_up(fake_ssd: Path) -> None:
    xml = (
        b'<?xml version="1.0"?>'
        b"<tags>"
        b'<row Id="1" TagName="python" Count="100" />'
        b'<row Id="2" TagName="javascript" Count="50" />'
        b"</tags>"
    )
    archive = _make_archive(constants.RAW, {"Tags.xml": xml})
    ingest_table("Tags")
    out_dir = constants.PROCESSED / "tags"
    parquet = out_dir / "year_month=all" / "data.parquet"
    assert parquet.is_file()
    assert pq.read_table(parquet).num_rows == 2
    assert (out_dir / "_SUCCESS").is_file()
    assert not (constants.RAW / "Tags.xml").is_file()
    assert archive.is_file()


# ensure idempotency when success marker is present
def test_ingest_table_is_idempotent(fake_ssd: Path) -> None:
    xml = b'<?xml version="1.0"?><tags><row Id="1" TagName="x" Count="1" /></tags>'
    _make_archive(constants.RAW, {"Tags.xml": xml})
    ingest_table("Tags")
    ingest_table("Tags")


# ensure keep_archives leaves .7z and .xml in place
def test_ingest_table_keep_archives_preserves_files(fake_ssd: Path) -> None:
    xml = b'<?xml version="1.0"?><tags><row Id="1" TagName="x" Count="1" /></tags>'
    archive = _make_archive(constants.RAW, {"Tags.xml": xml})
    ingest_table("Tags", keep_archives=True)
    assert archive.is_file()
    assert (constants.RAW / "Tags.xml").is_file()


# refuse to continue if partial output is present without success marker
def test_ingest_table_refuses_partial_output(fake_ssd: Path) -> None:
    xml = b'<?xml version="1.0"?><tags><row Id="1" TagName="x" Count="1" /></tags>'
    _make_archive(constants.RAW, {"Tags.xml": xml})
    out_dir = constants.PROCESSED / "tags"
    (out_dir / "year_month=all").mkdir(parents=True)
    (out_dir / "year_month=all" / "data.parquet").write_bytes(b"partial")
    with pytest.raises(RuntimeError, match=r"(?i)_success marker"):
        ingest_table("Tags")


# verify ingest_all removes the official archive after every table succeeds
def test_ingest_all_deletes_archive_after_success(fake_ssd: Path) -> None:
    archive = _make_archive(
        constants.RAW,
        {
            "Tags.xml": b'<?xml version="1.0"?><tags><row Id="1" TagName="a" Count="1" /></tags>',
            "PostLinks.xml": b'<?xml version="1.0"?><postlinks><row Id="1" CreationDate="2022-01-01T00:00:00.000" PostId="1" RelatedPostId="2" LinkTypeId="1" /></postlinks>',
            "Users.xml": b'<?xml version="1.0"?><users><row Id="1" Reputation="1" CreationDate="2022-01-01T00:00:00.000" DisplayName="x" /></users>',
            "Comments.xml": b'<?xml version="1.0"?><comments><row Id="1" PostId="1" Score="0" Text="hi" CreationDate="2022-01-01T00:00:00.000" /></comments>',
            "Posts.xml": b'<?xml version="1.0"?><posts><row Id="1" PostTypeId="1" CreationDate="2022-01-01T00:00:00.000" Score="0" Title="Q" /></posts>',
        },
    )
    ingest_all()
    assert not archive.is_file()
    for table in ["tags", "postlinks", "users", "comments", "posts"]:
        assert (constants.PROCESSED / table / "_SUCCESS").is_file()
