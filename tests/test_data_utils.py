from __future__ import annotations

import numpy as np
import xarray as xr

from core.data_pipeline.utils import (
    as_float,
    as_float_or_nan,
    as_str,
    broadcast_to_scenario,
    normalize_weights,
    read_json_or_raise,
    read_yaml_or_raise,
)


class LocalValidationError(RuntimeError):
    pass


def test_normalize_weights_default_and_normalized() -> None:
    assert normalize_weights([], 2) == [0.5, 0.5]
    got = normalize_weights([2, 1], 2)
    assert np.isclose(sum(got), 1.0)
    assert np.allclose(got, [2 / 3, 1 / 3])


def test_as_float_and_str_coercion() -> None:
    assert as_float("1.5", name="x", error_cls=LocalValidationError) == 1.5
    assert np.isnan(as_float_or_nan(None, name="x", error_cls=LocalValidationError))
    assert as_str(12, name="x", error_cls=LocalValidationError) == "12"


def test_broadcast_to_scenario_scalar() -> None:
    scenario = xr.DataArray(["s1", "s2"], dims=("scenario",), coords={"scenario": ["s1", "s2"]})
    v = xr.DataArray(3.0, name="k")
    out = broadcast_to_scenario(v, scenario)
    assert out.dims == ("scenario",)
    assert out.name == "k"
    assert np.allclose(out.values, [3.0, 3.0])


def test_json_yaml_readers(tmp_path) -> None:
    j = tmp_path / "a.json"
    y = tmp_path / "a.yaml"
    j.write_text('{"a": 1}', encoding="utf-8")
    y.write_text("a: 1\n", encoding="utf-8")

    assert read_json_or_raise(j, error_cls=LocalValidationError)["a"] == 1
    assert read_yaml_or_raise(y, error_cls=LocalValidationError)["a"] == 1

