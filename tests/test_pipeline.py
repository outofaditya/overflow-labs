import py7zr
import pytest
from pathlib import Path
from source import constants
import pyarrow.parquet as pq
from source.pipeline import ingest_table


# create a small archive in the test raw dir
def _make_archive(raw_dir: Path, table: str, xml_bytes: bytes) -> Path:
    xml_path = raw_dir / f"{table}.xml"
    xml_path.write_bytes(xml_bytes)
    archive_path = raw_dir / f"stackoverflow.com-{table}.7z"
    with py7zr.SevenZipFile(archive_path, "w") as z:
        z.write(xml_path, arcname=f"{table}.xml")
    xml_path.unlink()
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


# verify successful table ingest writes parquet and cleans up files
def test_ingest_table_writes_parquet_and_cleans_up(fake_ssd: Path) -> None:
    xml = (
        b'<?xml version="1.0"?>'
        b"<tags>"
        b'<row Id="1" TagName="python" Count="100" />'
        b'<row Id="2" TagName="javascript" Count="50" />'
        b"</tags>"
    )
    archive = _make_archive(constants.RAW, "Tags", xml)
    ingest_table("Tags")
    out_dir = constants.PROCESSED / "tags"
    parquet = out_dir / "year_month=all" / "data.parquet"
    assert parquet.is_file()
    assert pq.read_table(parquet).num_rows == 2
    assert (out_dir / "_SUCCESS").is_file()
    assert not archive.is_file()


# ensure idempotency when success marker is present
def test_ingest_table_is_idempotent(fake_ssd: Path) -> None:
    xml = b'<?xml version="1.0"?><tags><row Id="1" TagName="x" Count="1" /></tags>'
    _make_archive(constants.RAW, "Tags", xml)
    ingest_table("Tags")
    ingest_table("Tags")


# ensure keep_archives leaves .7z and .xml in place
def test_ingest_table_keep_archives_preserves_files(fake_ssd: Path) -> None:
    xml = b'<?xml version="1.0"?><tags><row Id="1" TagName="x" Count="1" /></tags>'
    archive = _make_archive(constants.RAW, "Tags", xml)
    ingest_table("Tags", keep_archives=True)
    assert archive.is_file()
    assert (constants.RAW / "Tags.xml").is_file()


# refuse to continue if partial output is present without success marker
def test_ingest_table_refuses_partial_output(fake_ssd: Path) -> None:
    xml = b'<?xml version="1.0"?><tags><row Id="1" TagName="x" Count="1" /></tags>'
    _make_archive(constants.RAW, "Tags", xml)
    out_dir = constants.PROCESSED / "tags"
    (out_dir / "year_month=all").mkdir(parents=True)
    (out_dir / "year_month=all" / "data.parquet").write_bytes(b"partial")
    with pytest.raises(RuntimeError, match=r"(?i)_success marker"):
        ingest_table("Tags")
