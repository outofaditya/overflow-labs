import pytest
from pathlib import Path
from source import constants
from unittest.mock import MagicMock, patch
from source.cloud import _require_token, pull_from_hf, push_to_hf


# fail fast when token is missing
def test_require_token_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "HF_TOKEN", None)
    with pytest.raises(RuntimeError, match=r"(?i)hf_token"):
        _require_token()


# return token unchanged when present
def test_require_token_returns_token_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(constants, "HF_TOKEN", "hf_test_xyz")
    assert _require_token() == "hf_test_xyz"


# verify push calls upload_folder with the right arguments
def test_push_to_hf_calls_upload_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    processed = tmp_path / "processed"
    processed.mkdir()
    (processed / "tags").mkdir()
    (processed / "tags" / "data.parquet").write_bytes(b"stub")

    monkeypatch.setattr(constants, "HF_TOKEN", "hf_test_xyz")
    monkeypatch.setattr(constants, "HF_REPO_ID", "test/repo")
    monkeypatch.setattr(constants, "PROCESSED", processed)

    fake_api = MagicMock()
    with (
        patch("source.cloud.HfApi", return_value=fake_api),
        patch("source.cloud.create_repo") as mock_create,
    ):
        push_to_hf()

    mock_create.assert_called_once()
    fake_api.upload_folder.assert_called_once()
    kwargs = fake_api.upload_folder.call_args.kwargs
    assert kwargs["folder_path"] == str(processed)
    assert kwargs["repo_id"] == "test/repo"
    assert kwargs["repo_type"] == "dataset"
    assert ".DS_Store" in kwargs["ignore_patterns"]


# fail fast when processed dir does not exist
def test_push_to_hf_requires_processed_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(constants, "HF_TOKEN", "hf_test_xyz")
    monkeypatch.setattr(constants, "PROCESSED", tmp_path / "missing")
    with pytest.raises(RuntimeError, match=r"(?i)processed dir"):
        push_to_hf()


# verify pull calls snapshot_download with the right arguments
def test_pull_from_hf_calls_snapshot_download(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(constants, "HF_TOKEN", "hf_test_xyz")
    monkeypatch.setattr(constants, "HF_REPO_ID", "test/repo")

    with patch(
        "source.cloud.snapshot_download", return_value="/tmp/cache/dataset"
    ) as mock_dl:
        result = pull_from_hf()

    mock_dl.assert_called_once()
    kwargs = mock_dl.call_args.kwargs
    assert kwargs["repo_id"] == "test/repo"
    assert kwargs["repo_type"] == "dataset"
    assert kwargs["token"] == "hf_test_xyz"
    assert result == Path("/tmp/cache/dataset")
