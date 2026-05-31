import pytest
import pandas as pd

from source.analysis.features import (
    FEATURES,
    _features_for_row,
    monthly_distributions,
)


# six features extracted correctly across a few representative inputs
@pytest.mark.parametrize(
    "title, body, tags, expected",
    [
        # one code block, one tag, no links
        (
            "Q1",
            "<p>hello world</p><pre><code>x=1</code></pre>",
            "<python>",
            {
                "title_length": 2,
                "code_block_count": 1,
                "code_block_total_length": 3,
                "link_count": 0,
                "tag_count": 1,
            },
        ),
        # no code, one link, three tags, inline code stays in prose
        (
            "a longer one",
            '<p>see <a href="x">here</a> and <code>inline</code></p>',
            "<a><b><c>",
            {
                "title_length": 12,
                "code_block_count": 0,
                "code_block_total_length": 0,
                "link_count": 1,
                "tag_count": 3,
            },
        ),
        # multiple code blocks sum, no title, no tags
        (
            "",
            "<pre><code>aaa</code></pre><pre><code>bbbbb</code></pre>",
            "",
            {
                "title_length": 0,
                "code_block_count": 2,
                "code_block_total_length": 8,
                "link_count": 0,
                "tag_count": 0,
            },
        ),
        # all-null inputs return zeros
        (
            None,
            None,
            None,
            {
                "title_length": 0,
                "body_prose_length": 0,
                "code_block_count": 0,
                "code_block_total_length": 0,
                "link_count": 0,
                "tag_count": 0,
            },
        ),
    ],
)
def test_features_for_row(title, body, tags, expected):
    out = _features_for_row(title, body, tags)
    for key, val in expected.items():
        assert out[key] == val


# monthly aggregation produces median + p90 columns per feature
def test_monthly_distributions_median_and_p90() -> None:
    df = pd.DataFrame(
        {
            "year_month": ["2024-01"] * 3 + ["2024-02"] * 3,
            "title_length": [10, 20, 30, 40, 50, 60],
            "body_prose_length": [100, 200, 300, 400, 500, 600],
            "code_block_count": [0, 1, 2, 3, 4, 5],
            "code_block_total_length": [0, 10, 20, 30, 40, 50],
            "link_count": [0, 0, 1, 0, 0, 1],
            "tag_count": [1, 2, 3, 1, 2, 3],
        }
    )
    out = monthly_distributions(df)
    assert len(out) == 2
    assert {f"{f}_median" for f in FEATURES}.issubset(out.columns)
    assert {f"{f}_p90" for f in FEATURES}.issubset(out.columns)
    jan = out[out["year_month"] == "2024-01"].iloc[0]
    assert jan["title_length_median"] == 20
    assert jan["title_length_p90"] == pytest.approx(28.0)  # 90th of [10,20,30]
    assert jan["code_block_count_median"] == 1
