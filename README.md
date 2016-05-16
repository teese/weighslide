#Weighslide
Weighslide is a python program to calculate sliding windows across of a list of numerical values.
The user sets the window size, and the exact weighting of each value in the window.

The sliding window (rolling window) analysis is used in diverse scientific and financial fields.
The current weighslide program is designed to be easy to use and allows highly customisable windows. Weighslide is not currently
optimised for large datasets.

**Citation:**<br /> For scientific texts, please cite as follows:<br />
"A sliding window analysis was performed using the weighslide module in python (Mark Teese, Technical University of Munich)."

#Installation
Weighslide depends on the following:
* python (tested for version 3.5)
* numpy
* pandas
* matplotlib

For Windows users, we recommend Anaconda python 3.x. The Anaconda package should contain all required python modules.

To install as a python module, open the command console and navigate to the weighslide folder
containing setup.py. Run the following:

`python setup.py install`

#Test
To test the module, open the command console and navigate to the folder
containing weighslide.py. Run the following:

`python weighslide.py [1,1,"x",1,1] mean -r [1,1,2,3,5,8,13,21,34]`

If successful, an output list will be printed on the screen.
#Usage
Here is an example of how to run weighslide within python, using an excel input file.
```
import weighslide
infile = r"D:\Path\To\Your\File\infile_name.xlsx"
# for excel files, you will need to input the sheet name containing the data
excel_kwargs = {"sheet_name":"orig_disruption"}
# if it's an excel file with multiple columns, define which column contains the data
column_with_data = "your data column header"
# define the window and statistic. The following parameters are used
# if you want to calculate mean of the four surrounding values in the sequence
window = [1,1,"x",1,1]
statistic = "mean"
name = "your short sample name"
weighslide.run_weighslide(infile, window, statistic, name, column_with_data, excel_kwargs=excel_kwargs)
```

Here is an example of how to run weighslide from the command line, using a csv input file.
```
python weighslide.py [1,1,"x",1,1] mean -i "D:\Path\To\Your\File\infile_name.xlsx" -c "your data column header"
```
In both cases the output files will be created in a subfolder within the same location as the input file.

For more help regarding the command-line options:
`python weighslide.py -h`

**Examples of windows:**<br/>
[1,1,1]<br/>&#8195; - if "statistic" is set to "mean", this window returns the average of the central position, and the two neighbouring positions<br>
&#8195; - the window size is 3<br>


[1,1,"x",1,1]<br/>&#8195; - the central position "x" has no weighting at all<br>
&#8195; - the window size is 5, it consists of the central position, two upstream, and two downstream positions<br>
&#8195; - the positions upstream (-1, -2) and downstream (1, 2) of the central position are all equally weighted.<br>
&#8195; - if the statistic is set to "mean", the result for each position will simply be the average of the surrounding 4 positions<br>

[0.5, 1, 0.5, 2, 0.5, 1, 0.5]<br/>&#8195; - the central position "2" is highly weighted (2*orig value)<br>
&#8195; - the window size is 7, it consists of the central position, three upstream, and three downstream positions<br>
&#8195; - the positions upstream (-1, -2, -3) and downstream (1, 2, 3) of the central position are unequally weighted.<br>
&#8195; - if the statistic is set to "mean", the result for each position will simply be the average of the surrounding 4 positions<br>



#License
Weighslide is free software distributed under the GNU General Public License version 3.