"""Tests for the weighslide command-line interface."""

import numpy as np
import pandas as pd
import pytest

from weighslide.weighslide import main


def test_raw_data_is_printed_to_stdout(capsys):
    main(["[2,5,2]", "mean", "-r", "[0,0,0,1,1,2,3,5,8,13,21]"])
    printed = capsys.readouterr().out
    values = [float(line) for line in printed.splitlines() if line.strip() and not line.startswith("Weighslide")]
    expected = [0.0, 0.0, 0.666667, 2.333333, 3.666667, 6.0, 9.666667, 15.666667, 25.333333, 41.0, 65.5]
    np.testing.assert_allclose(values, expected, rtol=1e-4)


def test_string_window_from_the_command_line(capsys):
    main(["4x4", "mean", "-r", "[1,1,2,3,5,8,13,21,34]"])
    assert "Weighslide output:" in capsys.readouterr().out


def test_infile_is_analysed(tmp_path):
    """`weighslide ... -i file.csv` used to fail with AttributeError before reading any data."""
    csv = tmp_path / "in.csv"
    pd.DataFrame({"values": [0, 0, 0, 1, 1, 2, 3, 5, 8, 13, 21]}).to_csv(csv, index=False)

    main(["[2,5,2]", "mean", "-i", str(csv), "-n", "cli"])

    result = pd.read_csv(tmp_path / "weighslide_output" / "cli_mean.csv", index_col=0).iloc[:, 0]
    expected = [0.0, 0.0, 0.666667, 2.333333, 3.666667, 6.0, 9.666667, 15.666667, 25.333333, 41.0, 65.5]
    np.testing.assert_allclose(result.to_numpy(), expected, rtol=1e-5)


def test_infile_with_a_named_column(tmp_path):
    csv = tmp_path / "in.csv"
    pd.DataFrame({"other": range(11), "values": [0, 0, 0, 1, 1, 2, 3, 5, 8, 13, 21]}).to_csv(csv, index=False)
    main(["[2,5,2]", "mean", "-i", str(csv), "-n", "cli", "-c", "values"])
    assert (tmp_path / "weighslide_output" / "cli_mean.csv").is_file()


def test_overwrite_flag_is_honoured(tmp_path):
    """The -o flag was parsed but never passed on, so a rerun always raised FileExistsError."""
    csv = tmp_path / "in.csv"
    pd.DataFrame({"values": [1.0, 2, 3, 4, 5]}).to_csv(csv, index=False)
    argv = ["[1,1,1]", "mean", "-i", str(csv), "-n", "cli"]

    main(argv)
    with pytest.raises(FileExistsError):
        main(argv)
    main([*argv, "-o", "True"])


def test_giving_both_an_infile_and_raw_data_is_rejected(tmp_path):
    csv = tmp_path / "in.csv"
    pd.DataFrame({"values": [1.0, 2, 3]}).to_csv(csv, index=False)
    with pytest.raises(ValueError, match="only one data format"):
        main(["[1,1,1]", "mean", "-i", str(csv), "-r", "[1,2,3]"])


def test_giving_neither_an_infile_nor_raw_data_is_rejected():
    with pytest.raises(SystemExit):
        main(["[1,1,1]", "mean"])


def test_unknown_statistic_is_rejected_by_the_parser():
    with pytest.raises(SystemExit):
        main(["[1,1,1]", "median", "-r", "[1,2,3]"])


def test_importing_the_module_does_not_parse_arguments():
    """The parser used to be built at import time, which ran on every `import weighslide`."""
    import weighslide.weighslide as module

    assert not hasattr(module, "args")
    assert callable(module.build_parser)


def test_help_is_available(capsys):
    with pytest.raises(SystemExit):
        main(["-h"])
    assert "weighslide" in capsys.readouterr().out
