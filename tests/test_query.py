from source.query import _to_query_parameters


# test all scalar types
def test_param_translation_handles_all_scalar_types() -> None:
    params = {"name": "python", "n": 10, "ratio": 0.5, "active": True}
    bq_params = _to_query_parameters(params)
    by_name = {p.name: p for p in bq_params}
    assert by_name["name"].type_ == "STRING"
    assert by_name["n"].type_ == "INT64"
    assert by_name["ratio"].type_ == "FLOAT64"
    assert by_name["active"].type_ == "BOOL"


# test empty parameters
def test_param_translation_empty_input() -> None:
    assert _to_query_parameters(None) == []
    assert _to_query_parameters({}) == []


# test boolean branch matches first
def test_param_translation_isinstance_order() -> None:
    bq_params = _to_query_parameters({"flag": True})
    assert bq_params[0].type_ == "BOOL"
