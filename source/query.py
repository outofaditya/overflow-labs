from __future__ import annotations

import pandas as pd
from source import constants
from typing import Any, Mapping
from google.cloud import bigquery
from source.logger import get_logger

# instantiate logger
log = get_logger(__name__)
_client: bigquery.Client | None = None


# generate a singleton client
def get_client() -> bigquery.Client:
    global _client
    if _client is None:
        if not constants.PROJECT:
            raise RuntimeError("GCP_PROJECT Not Set")
        _client = bigquery.Client(project=constants.PROJECT)
        log.info("BigQuery Client Ready")
    return _client


# the translator function (no f-strings)
def _to_query_parameters(
    params: Mapping[str, Any] | None,
) -> list[bigquery.ScalarQueryParameter]:
    if not params:
        return []
    out: list[bigquery.ScalarQueryParameter] = []

    # loop and translate the parameters
    for name, value in params.items():
        if isinstance(value, bool):
            bq_type = "BOOL"
        elif isinstance(value, int):
            bq_type = "INT64"
        elif isinstance(value, float):
            bq_type = "FLOAT64"
        else:
            bq_type = "STRING"
            value = str(value)
        out.append(bigquery.ScalarQueryParameter(name, bq_type, value))
    return out


# the price checker function
def estimate_bytes(sql: str, params: Mapping[str, Any] | None = None) -> int:
    client = get_client()
    job_config = bigquery.QueryJobConfig(
        dry_run=True,
        use_query_cache=False,
        query_parameters=_to_query_parameters(params),
    )
    job = client.query(sql, job_config=job_config)
    return job.total_bytes_processed or 0


# main query function
def run_query(
    sql: str,
    params: Mapping[str, Any] | None = None,
    max_bytes: int = constants.BILLING,
) -> pd.DataFrame:
    # estimate the bytes
    bytes_estimated = estimate_bytes(sql, params)
    gib_estimated = bytes_estimated / (1024**3)
    log.info(f"Query Cost: {gib_estimated:.2f} GiB")

    # exit if expensive
    if bytes_estimated > max_bytes:
        raise RuntimeError(
            f"Query Cost Exceeded Limit: {gib_estimated:.2f} GiB > {max_bytes / (1024**3):.2f} GiB"
        )

    # run the query
    client = get_client()
    job_config = bigquery.QueryJobConfig(query_parameters=_to_query_parameters(params))
    job = client.query(sql, job_config=job_config)

    # use the storage client for faster reads
    df = job.result().to_dataframe(create_bqstorage_client=True)
    log.info(f"Rows: {len(df)} + Columns: {df.shape[1]}")
    return df
