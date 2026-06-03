from __future__ import annotations

import sys
import numpy as np
import pandas as pd
from source import constants
from source.logger import get_logger
from source.analysis.metrics import write_csv

log = get_logger(__name__)

# metric csvs to run structural-break tests on, with the column to test
SERIES_SPECS = [
    ("monthly_volume.csv", "question_count", "Question Volume"),
    ("monthly_volume.csv", "answer_count", "Answer Volume"),
    ("active_askers.csv", "distinct_askers", "Active Askers"),
    ("accepted_rate.csv", "accepted_rate", "Accepted Rate"),
    ("answer_coverage.csv", "coverage_rate", "Answer Coverage"),
    ("time_to_first_answer.csv", "median_seconds", "Time to First Answer (med)"),
    ("time_to_acceptance.csv", "median_seconds", "Time to Acceptance (med)"),
    ("engagement.csv", "mean_score", "Mean Score"),
    ("engagement.csv", "mean_comments", "Mean Comments"),
]


def _load_series(filename: str, column: str) -> pd.Series:
    df = pd.read_csv(constants.TABLES / filename)
    df["year_month"] = pd.to_datetime(df["year_month"] + "-01")
    return df.set_index("year_month")[column].dropna()


def _breakpoint_index(series: pd.Series) -> int:
    cutoff = pd.Timestamp(constants.RELEASE)
    idx = series.index.searchsorted(cutoff)
    return max(1, min(idx, len(series) - 2))


def chow_test(series: pd.Series) -> dict:
    y = series.values.astype(float)
    n = len(y)
    bp = _breakpoint_index(series)

    # trend variable
    t = np.arange(n, dtype=float)

    # full model: y = a + b*t + c*D + d*D*t where D = post-break indicator
    D = np.zeros(n)
    D[bp:] = 1.0
    X_full = np.column_stack([np.ones(n), t, D, D * t])
    beta_full = np.linalg.lstsq(X_full, y, rcond=None)[0]
    rss_full = float(np.sum((y - X_full @ beta_full) ** 2))

    # restricted model: y = a + b*t (no break)
    X_restricted = np.column_stack([np.ones(n), t])
    beta_restricted = np.linalg.lstsq(X_restricted, y, rcond=None)[0]
    rss_restricted = float(np.sum((y - X_restricted @ beta_restricted) ** 2))

    # f-statistic
    k_full = X_full.shape[1]
    k_restricted = X_restricted.shape[1]
    df_num = k_full - k_restricted
    df_den = n - k_full
    if rss_full < 1e-15:
        f_stat = float("inf")
    else:
        f_stat = ((rss_restricted - rss_full) / df_num) / (rss_full / df_den)

    # p-value from f-distribution
    from scipy import stats

    p_value = 1.0 - stats.f.cdf(f_stat, df_num, df_den)

    return {
        "f_statistic": round(f_stat, 4),
        "p_value": round(p_value, 6),
        "df_numerator": df_num,
        "df_denominator": df_den,
        "breakpoint_month": str(series.index[bp].strftime("%Y-%m")),
    }


def cusum_test(series: pd.Series) -> dict:
    y = series.values.astype(float)
    n = len(y)

    # ols residuals under h0 (linear trend)
    t = np.arange(n, dtype=float)
    X = np.column_stack([np.ones(n), t])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    residuals = y - X @ beta
    sigma = float(np.std(residuals, ddof=2))

    # cusum statistic
    if sigma < 1e-15:
        return {
            "cusum_max": 0.0,
            "cusum_max_month": str(series.index[0].strftime("%Y-%m")),
            "significant_5pct": False,
        }

    cumsum = np.cumsum(residuals) / sigma
    abs_cusum = np.abs(cumsum)
    max_idx = int(np.argmax(abs_cusum))
    cusum_max = float(abs_cusum[max_idx])

    # approximate 5% critical value for cusum (brownian bridge bound)
    # using the boundary a + b * sqrt(n) where a ~ 0.948, from Harvey (1990)
    critical_5 = 0.948 * np.sqrt(n)

    return {
        "cusum_max": round(cusum_max, 4),
        "cusum_max_month": str(series.index[max_idx].strftime("%Y-%m")),
        "critical_5pct": round(critical_5, 4),
        "significant_5pct": bool(cusum_max > critical_5),
    }


def interrupted_ts_regression(series: pd.Series) -> dict:
    from scipy import stats

    y = series.values.astype(float)
    n = len(y)
    bp = _breakpoint_index(series)

    t = np.arange(n, dtype=float)
    D = np.zeros(n)
    D[bp:] = 1.0
    T_post = np.zeros(n)
    T_post[bp:] = np.arange(n - bp, dtype=float)

    # y = intercept + trend*t + level_change*D + slope_change*T_post
    X = np.column_stack([np.ones(n), t, D, T_post])
    beta, residuals_sum, _, _ = np.linalg.lstsq(X, y, rcond=None)
    y_hat = X @ beta
    residuals = y - y_hat
    sse = float(np.sum(residuals**2))
    mse = sse / (n - X.shape[1])

    # standard errors
    try:
        cov = mse * np.linalg.inv(X.T @ X)
        se = np.sqrt(np.diag(cov))
    except np.linalg.LinAlgError:
        se = np.full(X.shape[1], float("nan"))

    t_stats = beta / se
    p_values = [2 * (1 - stats.t.cdf(abs(ts), n - X.shape[1])) for ts in t_stats]

    names = ["intercept", "trend", "level_change", "slope_change"]
    result = {}
    for i, name in enumerate(names):
        result[f"{name}_coef"] = round(float(beta[i]), 6)
        result[f"{name}_se"] = round(float(se[i]), 6)
        result[f"{name}_t"] = round(float(t_stats[i]), 4)
        result[f"{name}_p"] = round(float(p_values[i]), 6)

    # r-squared
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r_squared = 1.0 - sse / ss_tot if ss_tot > 1e-15 else 0.0
    result["r_squared"] = round(r_squared, 6)
    result["n_obs"] = n
    result["breakpoint_month"] = str(series.index[bp].strftime("%Y-%m"))

    return result


def run_all_tests() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    chow_rows = []
    cusum_rows = []
    its_rows = []

    for filename, column, label in SERIES_SPECS:
        path = constants.TABLES / filename
        if not path.exists():
            log.warning("Skipping %s: %s not found", label, filename)
            continue

        series = _load_series(filename, column)
        log.info("Testing %s (%d observations)", label, len(series))

        chow = chow_test(series)
        chow["metric"] = label
        chow_rows.append(chow)

        cusum = cusum_test(series)
        cusum["metric"] = label
        cusum_rows.append(cusum)

        its = interrupted_ts_regression(series)
        its["metric"] = label
        its_rows.append(its)

    return (
        pd.DataFrame(chow_rows),
        pd.DataFrame(cusum_rows),
        pd.DataFrame(its_rows),
    )


def write_all() -> None:
    chow_df, cusum_df, its_df = run_all_tests()
    write_csv(chow_df, "chow_test.csv")
    write_csv(cusum_df, "cusum_test.csv")
    write_csv(its_df, "its_regression.csv")


def main() -> int:
    write_all()
    return 0


if __name__ == "__main__":
    sys.exit(main())
