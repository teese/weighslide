"""Tests for run_weighslide, which reads an input file and writes the output files and figure."""

import warnings

import numpy as np
import pandas as pd
import pytest

from weighslide import run_weighslide

WINDOW = "9xxxxx9xxxxx9xxxxx9xxxxx9xxxxx9xxxxx9"
# run_weighslide truncates both the name and a string window to 20 characters
OUT_STEM = "wavetest" + WINDOW[:20]


@pytest.fixture
def noisy_wave_csv(tmp_path):
    """A wave repeating every 6th position, buried in noise. The example from the README."""
    rng = np.random.default_rng(seed=0)
    df = pd.DataFrame()
    df["wave"] = [1, 1, 1, 3, 3, 3] * 8
    df["random"] = rng.random(df.shape[0])
    df["noisy wave"] = df.wave + df.random * 5
    csv = tmp_path / "wave.csv"
    df.to_csv(csv)
    return csv


def test_writes_all_four_output_files(noisy_wave_csv):
    run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="noisy wave")

    outdir = noisy_wave_csv.parent / "weighslide_output"
    assert (outdir / f"{OUT_STEM}.png").is_file()
    assert (outdir / f"{OUT_STEM}.xlsx").is_file()
    assert (outdir / f"{OUT_STEM}_mean.csv").is_file()
    assert (outdir / f"{OUT_STEM}_sliced.csv").is_file()
    assert (outdir / f"{OUT_STEM}_mult.csv").is_file()


def test_accepts_a_string_path_as_documented_in_the_readme(noisy_wave_csv):
    """The README passes a plain string. This used to raise AttributeError: 'str' has no attribute 'name'."""
    run_weighslide(str(noisy_wave_csv), WINDOW, "mean", name="wavetest", column="noisy wave")
    assert (noisy_wave_csv.parent / "weighslide_output" / f"{OUT_STEM}_mean.csv").is_file()


def test_smooths_the_repeating_wave(noisy_wave_csv):
    """The point of the package: a window matching the period should recover the underlying wave."""
    run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="noisy wave")

    outdir = noisy_wave_csv.parent / "weighslide_output"
    result = pd.read_csv(outdir / f"{OUT_STEM}_mean.csv", index_col=0).iloc[:, 0]
    original = pd.read_csv(noisy_wave_csv)["noisy wave"]
    assert len(result) == len(original)
    # only the central positions have full-length windows; the flanks are averaged over fewer points
    centre = slice(18, 30)
    underlying = pd.Series([1, 1, 1, 3, 3, 3] * 8, dtype=float)
    # the smoothed signal must track the underlying wave more closely than the noisy input does
    assert (result[centre] - underlying[centre]).abs().mean() < (original[centre] - underlying[centre]).abs().mean()


def test_excel_output_has_the_three_expected_sheets(noisy_wave_csv):
    run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="noisy wave")
    xlsx = noisy_wave_csv.parent / "weighslide_output" / f"{OUT_STEM}.xlsx"
    sheets = pd.ExcelFile(xlsx).sheet_names
    assert sheets == ["orig_data_sliced", "data_multipled", "window_mean"]


def test_reads_an_excel_input_file(tmp_path):
    xlsx = tmp_path / "in.xlsx"
    pd.DataFrame({"values": [0, 0, 0, 1, 1, 2, 3, 5, 8, 13, 21]}).to_excel(xlsx, index=False, sheet_name="data")
    run_weighslide(xlsx, [2, 5, 2], "mean", name="xl", excel_kwargs={"sheet_name": "data"})

    result = pd.read_csv(tmp_path / "weighslide_output" / "xl_mean.csv", index_col=0).iloc[:, 0]
    expected = [0.0, 0.0, 0.666667, 2.333333, 3.666667, 6.0, 9.666667, 15.666667, 25.333333, 41.0, 65.5]
    np.testing.assert_allclose(result.to_numpy(), expected, rtol=1e-5)


def test_single_column_input_needs_no_column_name(tmp_path):
    csv = tmp_path / "single.csv"
    pd.DataFrame({"values": [1.0, 2, 3, 4, 5]}).to_csv(csv, index=False)
    run_weighslide(csv, [1, 1, 1], "mean", name="single")
    assert (tmp_path / "weighslide_output" / "single_mean.csv").is_file()


def test_existing_output_is_not_overwritten_by_default(noisy_wave_csv):
    run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="noisy wave")
    with pytest.raises(FileExistsError, match="already exist"):
        run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="noisy wave")


def test_overwrite_true_replaces_existing_output(noisy_wave_csv):
    run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="noisy wave")
    run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="noisy wave", overwrite=True)


def test_multi_column_input_without_a_column_name_is_rejected(noisy_wave_csv):
    with pytest.raises(ValueError, match="No column name provided"):
        run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest")


def test_a_column_name_that_is_not_in_the_file_is_rejected(noisy_wave_csv):
    with pytest.raises(ValueError, match="not in the input file"):
        run_weighslide(noisy_wave_csv, WINDOW, "mean", name="wavetest", column="no such column")


def test_unsupported_filetype_is_rejected(tmp_path):
    txt = tmp_path / "data.txt"
    txt.write_text("1\n2\n3\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Filetype must be excel or csv"):
        run_weighslide(txt, [1, 1, 1], "mean")


def test_csv_kwargs_are_passed_to_pandas(tmp_path):
    csv = tmp_path / "skipme.csv"
    csv.write_text("# a comment line\nvalues\n1\n2\n3\n4\n5\n", encoding="utf-8")
    run_weighslide(csv, [1, 1, 1], "mean", name="skip", csv_kwargs={"skiprows": 1})
    assert (tmp_path / "weighslide_output" / "skip_mean.csv").is_file()


@pytest.mark.parametrize("window", [WINDOW, [1, 1, "x", 1, 1], [2, 5, 2]], ids=["string", "list_with_x", "list"])
def test_no_deprecation_or_future_warnings_are_raised(noisy_wave_csv, window):
    """This package sat untouched for years; pandas and numpy deprecations must not pile up again.

    Parametrised over both window forms: the string and list branches take different code
    paths, and a deprecation on one of them is invisible when only the other is exercised.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        warnings.simplefilter("error", DeprecationWarning)
        warnings.simplefilter("error", UserWarning)
        run_weighslide(noisy_wave_csv, window, "mean", name="wavetest", column="noisy wave")
