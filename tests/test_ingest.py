import pytest
from source.ingest import load_sql


# test loading a known file
def test_load_sql_reads_known_file() -> None:
    sql = load_sql("questions.sql")
    assert isinstance(sql, str)
    assert len(sql) > 0
    assert "FROM" in sql.upper()
    assert "@start_date" in sql


# test loading a missing file
def test_load_sql_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_sql("does_not_exist.sql")
