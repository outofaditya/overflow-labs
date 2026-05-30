import pytest
from source.data.loaders import load_sql


# test loading the questions.sql file
def test_load_sql_reads_questions_file() -> None:
    sql = load_sql("questions.sql")
    assert isinstance(sql, str)
    assert len(sql) > 0
    assert "PostTypeId = 1" in sql
    assert "$start_date" in sql


# test loading the answers.sql file
def test_load_sql_reads_answers_file() -> None:
    sql = load_sql("answers.sql")
    assert isinstance(sql, str)
    assert "PostTypeId = 2" in sql
    assert "$start_date" in sql


# test that a missing file raises a FileNotFoundError
def test_load_sql_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_sql("does_not_exist.sql")
