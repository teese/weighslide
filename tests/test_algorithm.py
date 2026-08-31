"""Unit tests for the weighslide algorithm itself (calculate_weighted_windows)."""

import numpy as np
import pandas as pd
import pytest

from weighslide.weighslide import _window_to_array, calculate_weighted_windows

# the worked example from the README and the run_weighslide docstring
DOCSTRING_DATA = [0, 0, 0, 1, 1, 2, 3, 5, 8, 13, 21]
DOCSTRING_EXPECTED = [0.0, 0.0, 0.666667, 2.333333, 3.666667, 6.0, 9.666667, 15.666667, 25.333333, 41.0, 65.5]


def test_matches_the_worked_example_in_the_docs():
    """The [2,5,2] mean example is quoted in the README, the docstring and the paper citation."""
    result = calculate_weighted_windows(pd.Series(DOCSTRING_DATA, dtype=float), [2, 5, 2], "mean", full_output=False)
    np.testing.assert_allclose(result.to_numpy(), DOCSTRING_EXPECTED, rtol=1e-5)


def test_ignored_positions_are_excluded_from_the_statistic():
    """An "x" position must not contribute to the window, not even as a zero."""
    data = pd.Series([0, 0, 0, 1, 1, 2, 3, 5, 8, 13, 21], dtype=float)
    result = calculate_weighted_windows(data, [1, 1, "x", 1, 1], "mean", full_output=False)
    # position 5 averages the four neighbours (1, 2 upstream; 5, 8 downstream) -> 1+2+5+8 = 16/4
    assert result.iloc[6] == pytest.approx(4.0)
    # a window of all-ones with an ignored centre is the mean of the 4 surrounding values
    expected = [0.0, 0.333333, 0.5, 0.75, 1.5, 2.5, 4.0, 6.5, 10.5, 11.333333, 10.5]
    np.testing.assert_allclose(result.to_numpy(), expected, rtol=1e-5)


def test_flanking_windows_are_padded_with_nan_not_zero():
    """The first and last windows are short; the missing positions must be NaN, which is skipped."""
    data = pd.Series([4.0, 4.0, 4.0])
    result = calculate_weighted_windows(data, [1, 1, 1], "mean", full_output=False)
    # every window averages only the real values, so a flat input stays flat
    np.testing.assert_allclose(result.to_numpy(), [4.0, 4.0, 4.0])


@pytest.mark.parametrize(
    ("statistic", "expected"),
    [
        ("mean", 2.0),
        ("sum", 6.0),
        ("std", 0.0),
    ],
)
def test_each_statistic_reduces_the_window(statistic, expected):
    data = pd.Series([2.0] * 5)
    result = calculate_weighted_windows(data, [1, 1, 1], statistic, full_output=False)
    # the centre position has a full-length window of three identical values
    assert result.iloc[2] == pytest.approx(expected)


def test_full_output_shapes():
    data = pd.Series(np.arange(10), dtype=float)
    window_array, df_sliced, df_multiplied, result = calculate_weighted_windows(data, [2, 5, 2], "mean")
    np.testing.assert_allclose(window_array, [2.0, 5.0, 2.0])
    # one column per input position, in both the sliced and the multiplied frames
    assert df_sliced.shape[1] == len(data)
    assert df_multiplied.shape[1] == len(data)
    assert list(df_sliced.columns) == [f"window {i}" for i in range(len(data))]
    assert len(result) == len(data)
    assert result.name == "mean over window"
    assert result.index.name == "position"


def test_output_keeps_the_index_of_the_input():
    """The window is positional, but the result must line up with the caller's own index."""
    data = pd.Series([0, 0, 0, 1, 1, 2, 3, 5, 8, 13, 21], dtype=float, index=range(100, 111))
    result = calculate_weighted_windows(data, [2, 5, 2], "mean", full_output=False)
    assert list(result.index) == list(range(100, 111))
    # a shifted index must not shift the values
    np.testing.assert_allclose(result.to_numpy(), DOCSTRING_EXPECTED, rtol=1e-5)


def test_input_series_is_not_mutated():
    data = pd.Series(DOCSTRING_DATA, dtype=float)
    data.name = "my measurements"
    before = data.copy()
    calculate_weighted_windows(data, [2, 5, 2], "mean", full_output=False)
    pd.testing.assert_series_equal(data, before)


class TestWindowParsing:
    def test_string_window_maps_0_to_9_onto_0pt1_to_1pt0(self):
        np.testing.assert_allclose(_window_to_array("094"), [0.1, 1.0, 0.5])

    def test_x_becomes_nan_in_a_string_window(self):
        np.testing.assert_allclose(_window_to_array("4x4"), [0.5, np.nan, 0.5], equal_nan=True)

    def test_x_becomes_nan_in_a_list_window(self):
        np.testing.assert_allclose(_window_to_array([2, "x", 2]), [2.0, np.nan, 2.0], equal_nan=True)

    def test_list_weights_are_taken_literally(self):
        np.testing.assert_allclose(_window_to_array([0.5, 1, 0.5]), [0.5, 1.0, 0.5])

    def test_a_window_that_is_neither_string_nor_list_is_rejected(self):
        with pytest.raises(TypeError, match="neither a string nor a list"):
            _window_to_array(np.array([1, 1, 1]))


class TestInputValidation:
    @pytest.fixture
    def data(self):
        return pd.Series(np.arange(10), dtype=float)

    def test_even_window_is_rejected(self, data):
        with pytest.raises(ValueError, match="is even"):
            calculate_weighted_windows(data, [1, 1], "mean")

    def test_empty_window_is_rejected(self, data):
        with pytest.raises(ValueError, match="Window length is 0"):
            calculate_weighted_windows(data, [], "mean")

    def test_over_long_window_is_rejected(self, data):
        with pytest.raises(ValueError, match="too long"):
            calculate_weighted_windows(data, [1] * 101, "mean")

    def test_unknown_statistic_is_rejected(self, data):
        with pytest.raises(ValueError, match="not recognised"):
            calculate_weighted_windows(data, [1, 1, 1], "median")

    def test_unknown_statistic_is_rejected_before_any_work_is_done(self):
        """The check used to sit inside the loop, so it only fired after slicing the whole array."""
        with pytest.raises(ValueError, match="not recognised"):
            calculate_weighted_windows(pd.Series([], dtype=float), [1, 1, 1], "median")

    def test_over_long_dataset_is_rejected(self):
        with pytest.raises(ValueError, match="long input sequence"):
            calculate_weighted_windows(pd.Series(np.zeros(10001)), [1, 1, 1], "mean")
