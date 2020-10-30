from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
import argparse
import ast
import sys


def run_weighslide(infile: Union[Path, str], window: Union[list, str], statistic: str, **kwargs):
    """ Runs the weighslide algorithm using data from an input file, and saves the output files and figures

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
    infile : string
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
    D:\Path\To\Your\Input\File\weighslide_output\

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

    # if the infile ends in .xls or .xlsx, open with excel_kwargs, if available
    filetype = str(infile.name).split(".")[-1]
    if filetype == "xlsx" or filetype == "xls":
        if "excel_kwargs" in kwargs.keys():
            df = pd.read_excel(infile, **kwargs["excel_kwargs"])
        else:
            df = pd.read_excel(infile)
    # if the infile ends in .csv, open with csv_kwargs, if available
    elif filetype == "csv":
        if "csv_kwargs" in kwargs:
            if kwargs["csv_kwargs"] is not None:
                df = pd.read_csv(infile, **kwargs["csv_kwargs"])
            else:
                df = pd.read_csv(infile)
        else:
            df = pd.read_csv(infile)
    else:
        raise ValueError("Filetype must be excel or csv, and have an .xlsx, .xls, or .csv extension.")

    # if the dataframe only has a single column, use it as the input data
    if df.shape[1] == 1:
        data_series = df.iloc[:, 0]
    # if the dataframe has multiple columns, search in the kwargs for the appropriate column name for input data
    elif df.shape[1] > 1:
        if "column" in kwargs.keys() and kwargs["column"] is not None:
            column = kwargs["column"]
            # select data column
            data_series = df[column]
        else:
            raise ValueError(r'No column name provided. The input file "{}" appears to have multiple columns, and '
                             r'therefore the column name with data needs to be input as a column '
                             r'variable.'.format(infile))
    else:
        raise ValueError(f"Input data not found. Imported {filetype} file '{infile}' has {df.shape[1]} columns")

    # get the path of the input file
    split_input_filepath = os.path.split(infile)
    inpath = split_input_filepath[0]

    # get the sample/experiment name from input variables, otherwise use the first 20 characters of filename
    if "name" in kwargs.keys():
        out_name = kwargs["name"][:20]
    else:
        out_name = split_input_filepath[1][:20]

    # if the window is a string, use first 20 characters in output filenames
    if type(window) == str:
        window_str = window[:20]
    else:
        # the list of weightings is probably not suitable to include in a filename. Use an empty string.
        window_str = ""

    # create a base name for the output files. Greate directory. Create output paths for excel, csv and png files.
    outpath = os.path.join(inpath, "weighslide_output")
    if not os.path.isdir(outpath):
        os.mkdir(outpath)
    out_basename = os.path.join(outpath, out_name + window_str)
    out_excelfile = out_basename + ".xlsx"
    out_csv_slice = out_basename + "_sliced" + ".csv"
    out_csv_mult = out_basename + "_mult" + ".csv"
    out_csv_statistic = out_basename + "_{}".format(statistic) + ".csv"
    out_png = out_basename + ".png"

    # determine the user variable "overwrite"
    if "overwrite" in kwargs.keys():
        overwrite = kwargs["overwrite"]
    else:
        overwrite = False

    # check if output files exist. Raise error if they exist, and "overwrite" is not True
    list_check_if_existing = [out_excelfile, out_csv_slice, out_csv_mult, out_csv_statistic, out_png]
    for filepath in list_check_if_existing:
        if os.path.exists(filepath):
            if not overwrite:
                raise FileExistsError('\nOutput files already exist. To overwrite files, please change the'
                                      ' "overwrite" variable to True.')

    # run the algorithm to calculate the weighted windows
    window_array, df_orig_sliced, df_multiplied, output_series = calculate_weighted_windows(data_series,
                                                                                            window, statistic)

    # save output files to csv
    df_orig_sliced.to_csv(out_csv_slice)
    df_multiplied.to_csv(out_csv_mult)
    output_series.to_csv(out_csv_statistic)

    # print dot showing progress
    sys.stdout.write(".")
    sys.stdout.flush()

    # save output files to excel
    writer = pd.ExcelWriter(out_excelfile)
    df_orig_sliced.to_excel(writer, sheet_name="orig_data_sliced")
    df_multiplied.to_excel(writer, sheet_name="data_multipled")
    output_series.to_frame(name="window_{}".format(statistic)).to_excel(writer, sheet_name="window_{}".format(statistic))
    writer.save()
    writer.close()

    # print dot showing progress
    sys.stdout.write(".")
    sys.stdout.flush()

    ############################################################
    #                                                          #
    #         Plot the output data vs the original             #
    #                                                          #
    ############################################################

    fig, ax = plt.subplots()
    ax.plot(data_series)
    ax.plot(output_series)
    ax.set_xlabel("position")
    ax.set_ylabel("value")
    window_string = str(window)
    dots = "..." if len(window_string) > 20 else ""
    ax.set_title("weighslide output for window {}{}".format(window_string[:20], dots))
    max_value = max(data_series.max(), output_series.max())
    min_value = min(data_series.min(), output_series.min())
    ax.set_ylim(min_value * 0.8, max_value * 1.2)
    lgd = ax.legend()
    plt.tight_layout()
    fig.savefig(out_png, format='png', dpi=200)
    if "showfig" in kwargs.keys():
        if kwargs["showfig"] == True:
            plt.show()

    print("\nWeighslide analysis is finished.")
    if len(inpath) > 1:
        print("\nLocation of output files:\n\t{}".format(outpath))


def calculate_weighted_windows(data_series, window, statistic, full_output=True):
    """ Apply the weighslide algorithm to an input series.

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

    data_series.name = "original data"

    if type(window) == str:
        # determine length of the window from the user input window
        window_length = len(window)
        # split into a list, convert to float, divide by 10 to yield a proportion
        window_series: pd.Series = pd.Series(list(window))
        # replace x with np.nan
        window_series.replace("x", np.nan, inplace=True)
        # change dtype to float
        window_series: pd.Series = window_series.astype(float)
        # convert 0-9 scale to 1-10, divide by 10 to give a relative weighting
        window_series = (window_series + 1) / 10
        # convert the series to a numpy array
        window_array = np.array(window_series).astype(float)

    elif type(window) == list:
        window_length = len(window)
        # convert the list or series to a numpy array
        window_series = pd.Series(window)
        # replace x with np.nan
        window_series.replace("x", np.nan, inplace=True)
        # convert the series to a numpy array
        window_array = np.array(window_series).astype(float)

    else:
        raise TypeError("The input variable 'window' is neither a string nor a list.")

    if window_length == 0:
        raise ValueError("Window length is 0. Please check the 'window' input variable.")

    elif window_length % 2 == 0:
        raise ValueError("Window length ({}) is even. Please check the window input variable. Only odd-length windows "
                         "are accepted, so that the result of the sliding "
                         "window analysis centres around a single non-ambiguous original position.".format(
            window_length))

    elif window_length > 100:
        raise ValueError("Window length ({}) is too long. Weighslide has not been optimised for large windows "
                         "or datasets. To run code anyway, convert this elif statement to a comment.".format(window_length))

    # count the number of positions on either side of the central position
    extension_each_side = int((window_length - 1) / 2)
    # extend the original series with zeroes on either side
    # define positive and negative ranges
    neg_range = list(range(-extension_each_side, 0))
    pos_range = list(np.arange(1, 6) + len(data_series) - 1)
    # create the index (e.g. -5,-4,-3,-2,-1,0,ORIG DATA, end+1, end+2...end+5)
    s_index = neg_range + list(data_series.index) + pos_range
    # reindex the series so that it is padded with np.nan on either side, as in the s_index
    extend_series = data_series.reindex(s_index)

    # create output series for the final window-averaged data
    output_series = pd.Series(index=data_series.index)
    # create output dataframes for saving all the slices etc.
    df_orig_sliced = pd.DataFrame()
    df_multiplied = pd.DataFrame()

    # get length of data series
    data_series_len = len(data_series)

    # show a warning if the data series is quite long
    if data_series_len > 1000:
        print("Warning. Input data length is {}. Weighslide performance may be slow.".format(data_series_len))
        if data_series_len > 10000:
            # abort if data series is very long.
            raise ValueError("Program aborted due to long input sequence. "
                             "Weighslide performance has not been optimised for large datasets. "
                             "To run code anyway, convert this 'if statement' to a comment".format(data_series_len))

    # for i in extend_series.index[:len(extend_series)-extension_each_side-1]:
    for i in range(data_series_len):
        if data_series_len > 100:
            if i % 100 == 0:
                sys.stdout.write(".")
                sys.stdout.flush()
        start = extend_series.index[i]
        end = start + window_length
        data_range = list(range(start, end))
        # slice out the original data from the window (e.g. 11 residues)
        # orig_sliced = extend_series.loc[i:i+window_length-1]
        # orig_sliced = extend_series[extend_series.index.isin(data_range)]
        orig_sliced = extend_series.reindex(data_range)
        orig_sliced.name = "window {}".format(i)
        orig_sliced_for_excel = orig_sliced.fillna("nodata")
        df_orig_sliced = pd.concat([df_orig_sliced, orig_sliced_for_excel], axis=1, names=[start])
        # double-check that the sliced window, and the values have the same length
        assert (len(orig_sliced) == len(window_array))
        # multiply by the window value multiplier for each position
        win_multiplied = orig_sliced * window_array
        win_multiplied_for_excel = win_multiplied.fillna("")
        df_multiplied = pd.concat([df_multiplied, win_multiplied_for_excel], axis=1, names=start)
        if statistic == "mean":
            # calculate the mean of the values, representing the relative value of that window
            win_mult_statistic = win_multiplied.mean()
        elif statistic == "std":
            # calculate the standard deviation of the values, representing the relative value of that window
            win_mult_statistic = win_multiplied.std()
        elif statistic == "sum":
            # calculate the standard deviation of the values, representing the relative value of that window
            win_mult_statistic = win_multiplied.sum()
        else:
            raise ValueError("The 'statistic' variable is not recognised. \nPlease check that the variable "
                             "is either 'mean', 'std', or 'sum'.")
        # add to output series
        output_series[i] = win_mult_statistic

    output_series.index.name = "position"
    output_series.name = "{} over window".format(statistic)

    if full_output == True:
        return window_array, df_orig_sliced, df_multiplied, output_series
    else:
        return output_series


# create a parser object to read user inputs from the command line
parser = argparse.ArgumentParser()

# add command-line options
parser.add_argument("w",  # "--window",
                    help="Sliding weighted window. Can be either a python list "
                         "(e.g. [0.3,1.0,0.3,0,0.3,1.0,0.3,0,0.3,1.0,0.3]), or a list of numbers that will be "
                         "converted to a python list (e.g. 393x393x393), where x represents positions that are ignored"
                         "and 9 represents positions that are most highly weighted.")
parser.add_argument("s",  # "--statistic",
                    default="mean",
                    type=str, choices=["mean", "std", "sum"],
                    help="The choices are mean, std or sum. Desired method to reduce the weighted values in the to a "
                         "single value at the central position.")
parser.add_argument("-r",  # "--rawdata",
                    default=None,
                    help='Raw data input in the command line. Should be a python list of integers (e.g. "[1,3,5,7,2,4]")'
                         ' or floats (e.g. "[1.1,3.4,5.2,7.8,2.7,4.5]")')
parser.add_argument("-i",  # "-infile",
                    default=None,
                    help=r'Full path of file containing original data in csv or excel format.'
                         r'E.g. "C:\Path\to\your\file.xlsx"')
parser.add_argument("-n",  # "--name",
                    default="",
                    help="Name of dataset. Should not be longer than 20 characters. Used in output filenames.")
parser.add_argument("-c",  # "--column",
                    default=None,
                    help='Column name in input file that should be used for analysis. E.g. "data values"')
parser.add_argument("-o",  # "--overwrite",
                    type=str, default="False",
                    help='If True, existing files will be overwritten.')
parser.add_argument("-e",  # "--excel_kwargs",
                    default="None",
                    help="Keyword arguments in python dictionary format to be used when opening "
                         "an excel file using the python pandas module. (E.g. {'sheet_name':'orig_data'}")
parser.add_argument("-k",  # "--csv_kwargs",
                    default=None,
                    help="Keyword arguments in python dictionary format to be used when opening "
                         "your csv file using the python pandas module. (E.g. {'delimeter':',','header'='infer'}")

# if weighslide.py is run as the main python script, obtain the options from the command line.
if __name__ == '__main__':

    print("\nTo view the help:\npython weighslide.py -h\n\nTo test the weighslide module:\n"
          "python weighslide.py [0.5,1.0,0.5] mean -r [1,3,5,7,2,4,3,5,7,2,4]\n\n")
    # obtain command-line arguments
    args = parser.parse_args()

    print(args)

    # extract the boolean "overwrite" variable from the input arguments
    if "o" in args:
        print(args.o)
        if args.o in ["True", "true", "TRUE"]:
            overwrite = True
        elif args.o in ["False", "false", "FALSE"]:
            overwrite = False
        else:
            raise ValueError('Overwrite variable "{}" is not recognised. '
                             'Accepted values are "True" or "False".'.format(args.o))
    else:
        overwrite = False

    # check that the user has not input both an infile and a raw data list
    if "r" in args:
        if all([args.i, args.r]):
            raise ValueError("Both an input file and a raw data string are entered. Please input only one data format.")

    # if the window looks like a python list (i.e., it starts with "["), convert it from stringlist to list
    if args.w[0] == "[":
        window = ast.literal_eval(args.w)
    else:
        window = args.w
    # extract the statistic method to be applied the weighted window (e.g. mean)
    statistic = args.s

    if args.i is not None:
        # normalise the path of the infile to suit the operating system
        infile = os.path.normpath(args.i)
        # extract the column name from the command-line input
        column = args.c
        # extract the sample/data name from the command-line input
        name = args.n
        # extract the excel_kwargs from the command-line input
        excel_kwargs = ast.literal_eval(args.e)
        # extract the csv_kwargs from the command-line input
        if args.k is not None:
            csv_kwargs = ast.literal_eval(args.k)
        else:
            csv_kwargs = None
        # run weighslide
        run_weighslide(infile=infile, window=window, statistic=statistic, column=column,
                       name=name, excel_kwargs=excel_kwargs, csv_kwargs=csv_kwargs)

    elif args.r is not None:
        # extract the csv_kwargs from the command-line input
        raw_data_user_input = args.r
        # convert the stringlist to a python list
        raw_data_list = ast.literal_eval(raw_data_user_input)
        # convert the python list to a pandas Series
        raw_data_series = pd.Series(raw_data_list)
        # run the calculate_weighted_windows function
        window_array, df_orig_sliced, df_multiplied, output_series = calculate_weighted_windows(raw_data_series,
                                                                                                window, statistic)
        print("\nWeighslide output:")
        # print out the values from the output series
        print(output_series.to_string(index=False, header=False))
