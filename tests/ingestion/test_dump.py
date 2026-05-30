import pytest
from pathlib import Path
import pyarrow.parquet as pq

from source.ingestion.dump import convert, _coerce_row, _partition_of

_TAGS_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<tags>
<row Id="1" TagName="python" Count="100" />
<row Id="2" TagName="javascript" Count="50" />
</tags>
"""

_POSTS_XML = b"""<?xml version="1.0" encoding="utf-8"?>
<posts>
<row Id="1" PostTypeId="1" CreationDate="2022-11-15T10:00:00.000" Score="5" Title="Q1" />
<row Id="2" PostTypeId="1" CreationDate="2022-11-20T11:00:00.000" Score="3" Title="Q2" />
<row Id="3" PostTypeId="1" CreationDate="2022-12-01T12:00:00.000" Score="7" Title="Q3" />
</posts>
"""


# tests that converting tags creates a single partition called 'all' with correct data
def test_convert_tags_writes_single_all_partition(tmp_path: Path) -> None:
    xml = tmp_path / "Tags.xml"
    xml.write_bytes(_TAGS_XML)
    out = tmp_path / "out"
    total = convert("Tags", xml, out, batch_size=1000)
    assert total == 2
    part = out / "year_month=all" / "data.parquet"
    assert part.is_file()
    table = pq.read_table(part)
    assert table.num_rows == 2
    assert "TagName" in table.column_names


# tests that post data is correctly split into partitions by creation month
def test_convert_posts_partitions_by_month(tmp_path: Path) -> None:
    xml = tmp_path / "Posts.xml"
    xml.write_bytes(_POSTS_XML)
    out = tmp_path / "out"
    total = convert("Posts", xml, out, batch_size=1000)
    assert total == 3
    nov = out / "year_month=2022-11" / "data.parquet"
    dec = out / "year_month=2022-12" / "data.parquet"
    assert nov.is_file() and dec.is_file()
    assert pq.read_table(nov).num_rows == 2
    assert pq.read_table(dec).num_rows == 1


# tests that coercion converts string types to expected python types
def test_coerce_row_types() -> None:
    row = {
        "Id": "42",
        "TagName": "python",
        "Count": "100",
        "ExcerptPostId": "",
        "WikiPostId": "999",
    }
    out = _coerce_row("Tags", row)
    assert out["Id"] == 42
    assert isinstance(out["Id"], int)
    assert out["TagName"] == "python"
    assert out["ExcerptPostId"] is None
    assert out["WikiPostId"] == 999


# tests that unpartitioned tables return 'all' as the partition
def test_partition_of_unpartitioned_table() -> None:
    assert _partition_of({"Id": 1}, None) == "all"


# tests that unknown table names raise a ValueError
def test_convert_rejects_unknown_table(tmp_path: Path) -> None:
    xml = tmp_path / "foo.xml"
    xml.write_bytes(b"<rows></rows>")
    with pytest.raises(ValueError, match="Unknown table"):
        convert("NotATable", xml, tmp_path / "out")
