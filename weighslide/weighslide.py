# Defers evaluation of the annotations below, so that `Path | str` (PEP 604 syntax,
# which is only valid at runtime on python 3.10+) does not raise on older versions.
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

STATISTICS = ("mean", "std", "sum")


def run_weighslide(infile: Path | str, window: list | str, statistic: str, **kwargs):
    """Runs the weighslide algorithm using data from an input file, and saves the output files and figures

    Weighslide takes as an input a 1D array (list) of numerical data, and applies a user-defined weighting and
    algorithm in a sliding-window fashion across the data.

    For example:
    window = [ 2  5  2 ]
    statistic = "mean"
    dataset = [ 0  0  0  1  1  2  3  5  8  13  21]
    The window length is 3. The array will therefore be sliced as follows:
              [ NaN  0  0 ]
                 [ 0  0  1 ]
                    [ 0  1  1 ]
                      [ 1  1  2 ] and so on until the final slice [ 13  21  NaN ]
    Each array slice will be "weighted" by multiplication with the window, array-style, resulting in:
              [ NaN  0  0 ]
                 [ 0  0  2 ]
                    [ 0  5  2 ]
                       [ 2  5  4 ] and so on.
    If the "statistic" variable is given as "mean", a mean will be calculated for each array slice.
              [    0    ]
                 [   0.66  ]
                    [   2.33  ]
                       [  3.66  ] and so on.
    The "statistic" can be mean, std, or sum.
    The value (in this case the mean) will replace the central position in the output 1D array.
    output = [ 0.00  0.00  0.66  2.33  3.66  6.00  9.66  15.6  25.3  41.0  65.5  ]
    The first and last array slices always contain "not a number" (Nan) values, which are ignored in all calculations.
    The first and last output values therefore do not represent results from true, full-length windows.

    Parameters
    ----------
    infile : Path or string
        Path to csv or excel file containing the data to be analysed.
    window : list or string
        The user-defined window that determines the size of the slices in the array, and the weight of each value in
        the slice. Can be a list of integers or floats (e.g. [2,5,2]). Can also be a string of numbers that will be
        converted to a list, for example "494" will be converted to [0.5,1.0,0.5], where 0 gives the lowest weighting
        (0.1) and 9 giving the heighest weighting (1.0). In all cases, data to be ignored in the window should be
        annoted with "x", for example [2,"x",2], or "4x4" will be converted to [2,np.nan,2] and [0.5,np.nan,0.5]
        respectively.
    statistic : string
        Statistical algorithm to be applied to the weighted slice. The options are "mean", "std", or "sum".

    Keyword arguments (optional):
    ----------
    name :  string
        Short name used to describe sample or experiment. If given, will be included in output filename.
    column : string
        In excel or csv input files with headers, this is the column name containing the data to analyse.
        The default is the first column of the dataset.
    overwrite : boolean
        If True, output files with the same name will be overwritten. If False, any existing outputfiles will result
        in an error.
    showfig : boolean
        If True, the output figure will be shown as a popup window, or in IPython/Jupyter.
        For Ipython/Jupyter it is recommended to precede weighslide with the magic command %matplotlib inline.
    excel_kwargs : dictionary
        Keyword arguments necessary for pandas to read the input excel file.
        E.g. {"sheet_name" : "datasheet", "header" : 0, "skiprows : 3}
    csv_kwargs : dictionary
        Keyword arguments necessary for pandas to read the input csv file.
        E.g. {"delimiter" : ",", "skiprows : 3}

    Saved Files and Figures
    -------
    All output files are saved in a subfolder based on the input xlsx or csv file:
    D:/Path/To/Your/Input/File/weighslide_output/

    out_csv_statistic : csv
        Output file after applying weighslide to the input list of numerical values.
        Consists of a list of values, of the same length as the original input list.
        Filename will reflect that statistical method used (e.g. YourExperimentName_mean.csv for statistic = "mean")
    out_csv_slice : csv
        Shows all slices from the original 1D array/list. Filesize is ~1200 kb for an input list of size 1000.
    out_csv_mult : csv
        Shows the values in all slices after multiplication against the window.
        Filesize is ~1200 kb for an input list of size 1000.
    out_excelfile : excel (.xlsx)
        The three output datasets (out_csv_statistic, out_csv_slice, and out_csv_mult) are saved on separate sheets.
        Due to compression, filesize is efficient, with ~150 kb for an input list of size 1000.
    out_png : png image
        Very simple and unannotated figure showing a line graph of the original data, in combination with the output
        after the sliding window analysis.

    Note
    -------
    Weighslide is not currently optimised for performance. Input arrays must have <10 000 datapoints.
    """
    print("Starting weighslide analysis.")

    # accept either a string or a Path, so that the command line and the python API behave the same
    infile = Path(infile)
    filetype = infile.suffix.lstrip(".").lower()

    # if the infile ends in .xls or .xlsx, open with excel_kwargs, if available
    if filetype in ("xlsx", "xls"):
        excel_kwargs = kwargs.get("excel_kwargs") or {}
        df = pd.read_excel(infile, **excel_kwargs)
    # if the infile ends in .csv, open with csv_kwargs, if available
    elif filetype == "csv":
        csv_kwargs = kwargs.get("csv_kwargs") or {}
        df = pd.read_csv(infile, **csv_kwargs)
    else:
        raise ValueError("Filetype must be excel or csv, and have an .xlsx, .xls, or .csv extension.")

    # if the dataframe only has a single column, use it as the input data
    if df.shape[1] == 1:
        data_series = df.iloc[:, 0]
    # if the dataframe has multiple columns, search in the kwargs for the appropriate column name for input data
    elif df.shape[1] > 1:
        if kwargs.get("column") is not None:
            column = kwargs["column"]
            if column not in df.columns:
                raise ValueError(
                    f'Column "{column}" is not in the input file "{infile}". '
                    f"The available columns are {list(df.columns)}."
                )
            # select data column
            data_series = df[column]
        else:
            raise ValueError(
                f'No column name provided. The input file "{infile}" appears to have multiple columns, and '
                f"therefore the column name with data needs to be input as a column variable."
            )
    else:
        raise ValueError(f"Input data not found. Imported {filetype} file '{infile}' has {df.shape[1]} columns")

    # get the path of the input file
    inpath = infile.parent

    # get the sample/experiment name from input variables, otherwise use the first 20 characters of filename
    if "name" in kwargs:
        out_name = kwargs["name"][:20]
    else:
        out_name = infile.name[:20]

    # if the window is a string, use first 20 characters in output filenames
    if isinstance(window, str):
        window_str = window[:20]
    else:
        # the list of weightings is probably not suitable to include in a filename. Use an empty string.
        window_str = ""

    # create a base name for the output files. Create directory. Create output paths for excel, csv and png files.
    outpath = inpath / "weighslide_output"
    outpath.mkdir(parents=True, exist_ok=True)
    out_basename = outpath / (out_name + window_str)
    out_excelfile = out_basename.with_name(out_basename.name + ".xlsx")
    out_csv_slice = out_basename.with_name(out_basename.name + "_sliced.csv")
    out_csv_mult = out_basename.with_name(out_basename.name + "_mult.csv")
    out_csv_statistic = out_basename.with_name(f"{out_basename.name}_{statistic}.csv")
    out_png = out_basename.with_name(out_basename.name + ".png")

    # determine the user variable "overwrite"
    overwrite = kwargs.get("overwrite", False)

    # check if output files exist. Raise error if they exist, and "overwrite" is not True
    list_check_if_existing = [out_excelfile, out_csv_slice, out_csv_mult, out_csv_statistic, out_png]
    if not overwrite:
        for filepath in list_check_if_existing:
            if filepath.exists():
                raise FileExistsError(
                    "\nOutput files already exist. To overwrite files, please change the"
                    ' "overwrite" variable to True.'
                )

    # run the algorithm to calculate the weighted windows
    window_array, df_orig_sliced, df_multiplied, output_series = calculate_weighted_windows(
        data_series, window, statistic
    )

    # save output files to csv
    df_orig_sliced.to_csv(out_csv_slice)
    df_multiplied.to_csv(out_csv_mult)
    output_series.to_csv(out_csv_statistic)

    # print dot showing progress
    sys.stdout.write(".")
    sys.stdout.flush()

    # save output files to excel
    with pd.ExcelWriter(out_excelfile) as writer:
        df_orig_sliced.to_excel(writer, sheet_name="orig_data_sliced")
        df_multiplied.to_excel(writer, sheet_name="data_multipled")
        output_series.to_frame(name=f"window_{statistic}").to_excel(writer, sheet_name=f"window_{statistic}")

    # print dot showing progress
    sys.stdout.write(".")
    sys.stdout.flush()

    ############################################################
    #                                                          #
    #         Plot the output data vs the original             #
    #                                                          #
    ############################################################

    fig, ax = plt.subplots()
    # the labels are what ax.legend() below picks up; without them the legend is empty
    ax.plot(data_series.index, data_series.to_numpy(), label="original data")
    ax.plot(output_series.index, output_series.to_numpy(), label=str(output_series.name))
    ax.set_xlabel("position")
    ax.set_ylabel("value")
    window_string = str(window)
    dots = "..." if len(window_string) > 20 else ""
    ax.set_title(f"weighslide output for window {window_string[:20]}{dots}")
    max_value = max(data_series.max(), output_series.max())
    min_value = min(data_series.min(), output_series.min())
    ax.set_ylim(min_value * 0.8, max_value * 1.2)
    ax.legend()
    plt.tight_layout()
    fig.savefig(out_png, format="png", dpi=200)
    if kwargs.get("showfig"):
        plt.show()
    # close explicitly, otherwise repeated calls accumulate open figures until matplotlib warns
    plt.close(fig)

    print("\nWeighslide analysis is finished.")
    print(f"\nLocation of output files:\n\t{outpath}")


def _window_to_array(window: list | str) -> np.ndarray:
    """Convert a user-supplied window into a 1D float array, with "x" positions as np.nan.

    A string window uses a 0-9 shorthand for the weighting, which is shifted and scaled onto
    0.1-1.0. A list window is taken as literal weights.
    """
    if isinstance(window, str):
        # split into a list of single characters, e.g. "4x4" -> ["4", "x", "4"]
        window_series = pd.Series(list(window))
        # replace x with np.nan, then change dtype to float
        window_series = window_series.replace("x", np.nan).astype(float)
        # convert 0-9 scale to 1-10, divide by 10 to give a relative weighting
        window_series = (window_series + 1) / 10
    elif isinstance(window, list):
        # replace x with np.nan
        window_series = pd.Series(window, dtype=object).replace("x", np.nan).astype(float)
    else:
        raise TypeError("The input variable 'window' is neither a string nor a list.")

    return np.asarray(window_series, dtype=float)


def calculate_weighted_windows(data_series, window, statistic, full_output=True):
    """Apply the weighslide algorithm to an input series.

    Parameters
    ----------
    data_series : pd.Series
        1D array of input data to which the weighslide algorithm will be applied.
    window : list or string
        The user-defined window that determines the size of the slices in the array, and the weight of each value in
        the slice. Can be a list of integers or floats (e.g. [2,5,2]). Can also be a string of numbers that will be
        converted to a list, for example "494" will be converted to [0.5,1.0,0.5], where 0 gives the lowest weighting
        (0.1) and 9 giving the heighest weighting (1.0). In all cases, data to be ignored in the window should be
        annoted with "x", for example [2,"x",2], or "4x4" will be converted to [2,np.nan,2] and [0.5,np.nan,0.5]
        respectively.
    statistic : string
        Statistical algorithm to be applied to the weighted slice. The options are "mean", "std", or "sum".

    Returns
    -------
    window_array : np.ndarray
        The window in numpy array format, as it is applied to the input data slices.
    df_orig_sliced : pd.DataFrame
        Pandas Dataframe containing each slice of the original data, before applying to the window_array and calculation
        of mean, etc. Effectively a 2D array of slices, so that the user can double-check the slice algorithm.
    df_multiplied : pd.DataFrame
        Pandas Dataframe containing each slice of the original data, after applying to the window_array.
        Effectively a 2D array of slices, so that the user can double-check the slice+window algorithm.
    output_series : pd.Series
        Pandas Series containing the output data. This is the result after slicing, applying the window, and applying a
        statistic (mean, std or sum). The series indexb is the range of the original data. The dtype is float.
    """
    if statistic not in STATISTICS:
        raise ValueError(
            "The 'statistic' variable is not recognised. \nPlease check that the variable "
            "is either 'mean', 'std', or 'sum'."
        )

    data_series = pd.Series(data_series).rename("original data")

    window_array = _window_to_array(window)
    window_length = len(window_array)

    if window_length == 0:
        raise ValueError("Window length is 0. Please check the 'window' input variable.")

    elif window_length % 2 == 0:
        raise ValueError(
            f"Window length ({window_length}) is even. Please check the window input variable. Only odd-length "
            "windows are accepted, so that the result of the sliding window analysis centres around a single "
            "non-ambiguous original position."
        )

    elif window_length > 100:
        raise ValueError(
            f"Window length ({window_length}) is too long. Weighslide has not been optimised for large windows "
            "or datasets. To run code anyway, convert this elif statement to a comment."
        )

    # get length of data series
    data_series_len = len(data_series)

    # show a warning if the data series is quite long
    if data_series_len > 1000:
        print(f"Warning. Input data length is {data_series_len}. Weighslide performance may be slow.")
        if data_series_len > 10000:
            # abort if data series is very long.
            raise ValueError(
                f"Program aborted due to long input sequence (length {data_series_len}). "
                "Weighslide performance has not been optimised for large datasets. "
                "To run code anyway, convert this 'if statement' to a comment"
            )

    # the slicing below indexes the data by position, so an arbitrary input index (e.g. a
    # gene name, or a non-zero-based range) would silently produce the wrong slices.
    # Work on a 0..n-1 index throughout, and restore the caller's index on the output.
    orig_index = data_series.index
    data_series = data_series.reset_index(drop=True)

    # count the number of positions on either side of the central position
    extension_each_side = (window_length - 1) // 2
    # extend the original series with np.nan on either side, so that the windows centred on the
    # first and last positions still have a full-length slice to work with
    neg_range = list(range(-extension_each_side, 0))
    pos_range = list(range(data_series_len, data_series_len + extension_each_side))
    # create the index (e.g. -5,-4,-3,-2,-1,0,ORIG DATA, end+1, end+2...end+5)
    s_index = neg_range + list(data_series.index) + pos_range
    # reindex the series so that it is padded with np.nan on either side, as in the s_index
    extend_series = data_series.reindex(s_index)

    # collect the slices in lists and concatenate once. Concatenating inside the loop copies the
    # whole growing frame on every iteration, which is quadratic in the length of the input.
    orig_slices = []
    multiplied_slices = []
    statistic_values = np.empty(data_series_len, dtype=float)

    for i in range(data_series_len):
        if data_series_len > 100 and i % 100 == 0:
            sys.stdout.write(".")
            sys.stdout.flush()
        start = i - extension_each_side
        data_range = list(range(start, start + window_length))
        # slice out the original data from the window (e.g. 11 residues)
        orig_sliced = extend_series.reindex(data_range)
        orig_sliced.name = f"window {i}"
        orig_slices.append(orig_sliced.fillna("nodata"))
        # double-check that the sliced window, and the values have the same length
        assert len(orig_sliced) == len(window_array)
        # multiply by the window value multiplier for each position
        win_multiplied = orig_sliced * window_array
        multiplied_slices.append(win_multiplied.fillna(""))
        if statistic == "mean":
            # calculate the mean of the values, representing the relative value of that window
            statistic_values[i] = win_multiplied.mean()
        elif statistic == "std":
            # calculate the standard deviation of the values, representing the relative value of that window
            statistic_values[i] = win_multiplied.std()
        else:
            # calculate the sum of the values, representing the relative value of that window
            statistic_values[i] = win_multiplied.sum()

    df_orig_sliced = pd.concat(orig_slices, axis=1)
    df_multiplied = pd.concat(multiplied_slices, axis=1)

    output_series = pd.Series(statistic_values, index=orig_index, dtype=float)
    output_series.index.name = "position"
    output_series.name = f"{statistic} over window"

    if full_output:
        return window_array, df_orig_sliced, df_multiplied, output_series
    else:
        return output_series


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for the weighslide console script."""
    parser = argparse.ArgumentParser(
        prog="weighslide",
        description="Sliding window analysis of a list of numerical values, using flexible user-defined windows.",
    )

    # add command-line options
    parser.add_argument(
        "w",  # "--window",
        help="Sliding weighted window. Can be either a python list "
        "(e.g. [0.3,1.0,0.3,0,0.3,1.0,0.3,0,0.3,1.0,0.3]), or a list of numbers that will be "
        "converted to a python list (e.g. 393x393x393), where x represents positions that are ignored"
        "and 9 represents positions that are most highly weighted.",
    )
    parser.add_argument(
        "s",  # "--statistic",
        default="mean",
        type=str,
        choices=list(STATISTICS),
        help="The choices are mean, std or sum. Desired method to reduce the weighted values in the to a "
        "single value at the central position.",
    )
    parser.add_argument(
        "-r",  # "--rawdata",
        default=None,
        help='Raw data input in the command line. Should be a python list of integers (e.g. "[1,3,5,7,2,4]")'
        ' or floats (e.g. "[1.1,3.4,5.2,7.8,2.7,4.5]")',
    )
    parser.add_argument(
        "-i",  # "-infile",
        default=None,
        help=r"Full path of file containing original data in csv or excel format." r'E.g. "C:/Path/to/your/file.xlsx"',
    )
    parser.add_argument(
        "-n",  # "--name",
        default="",
        help="Name of dataset. Should not be longer than 20 characters. Used in output filenames.",
    )
    parser.add_argument(
        "-c",  # "--column",
        default=None,
        help='Column name in input file that should be used for analysis. E.g. "data values"',
    )
    parser.add_argument(
        "-o",  # "--overwrite",
        type=str,
        default="False",
        choices=["True", "true", "TRUE", "False", "false", "FALSE"],
        help="If True, existing files will be overwritten.",
    )
    parser.add_argument(
        "-e",  # "--excel_kwargs",
        default="None",
        help="Keyword arguments in python dictionary format to be used when opening "
        "an excel file using the python pandas module. (E.g. {'sheet_name':'orig_data'}",
    )
    parser.add_argument(
        "-k",  # "--csv_kwargs",
        default=None,
        help="Keyword arguments in python dictionary format to be used when opening "
        "your csv file using the python pandas module. (E.g. {'delimeter':',','header'='infer'}",
    )
    return parser


def main(argv=None):
    """Entry point for the ``weighslide`` console script."""
    parser = build_parser()
    # obtain command-line arguments
    args = parser.parse_args(argv)

    # extract the boolean "overwrite" variable from the input arguments
    overwrite = args.o in ("True", "true", "TRUE")

    # check that the user has not input both an infile and a raw data list
    if args.i and args.r:
        raise ValueError("Both an input file and a raw data string are entered. Please input only one data format.")
    if not args.i and not args.r:
        parser.error("No data given. Provide either an input file with -i, or a raw data list with -r.")

    # if the window looks like a python list (i.e., it starts with "["), convert it from stringlist to list
    if args.w.startswith("["):
        window = ast.literal_eval(args.w)
    else:
        window = args.w
    # extract the statistic method to be applied the weighted window (e.g. mean)
    statistic = args.s

    if args.i is not None:
        # extract the excel_kwargs from the command-line input
        excel_kwargs = ast.literal_eval(args.e)
        # extract the csv_kwargs from the command-line input
        csv_kwargs = ast.literal_eval(args.k) if args.k is not None else None
        # run weighslide
        run_weighslide(
            infile=Path(args.i),
            window=window,
            statistic=statistic,
            column=args.c,
            name=args.n,
            overwrite=overwrite,
            excel_kwargs=excel_kwargs,
            csv_kwargs=csv_kwargs,
        )
    else:
        # convert the stringlist to a python list, then to a pandas Series
        raw_data_series = pd.Series(ast.literal_eval(args.r))
        # run the calculate_weighted_windows function
        output_series = calculate_weighted_windows(raw_data_series, window, statistic, full_output=False)
        print("\nWeighslide output:")
        # print out the values from the output series
        print(output_series.to_string(index=False, header=False))


# if weighslide.py is run as the main python script, obtain the options from the command line.
if __name__ == "__main__":
    main()
