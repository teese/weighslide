#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 Weighslide is a program for sliding window analysis of a list of numerical values,
 using flexible windows determined by the user.

Copyright (C) 2016  Mark George Teese

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
from setuptools import setup, find_packages
import path

# grab the long_description from the readme file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

classifiers = """\
Development Status :: 3 - Alpha
Intended Audience :: Science/Research
License :: OSI Approved :: GNU Lesser General Public License v3 or later (LGPLv3+)
Programming Language :: Python :: 3.6
Topic :: Scientific/Engineering :: Bio-Informatics
"""

setup(name='weighslide',
    packages=find_packages(),
    version='0.1.5',
    description="Flexible sliding window analysis",
    author='Mark Teese',
    long_description=long_description,
    url = "https://github.com/teese/weighslide",
    download_url = 'https://github.com/teese/weighslide/archive/0.1.tar.gz',
    license='LGPLv3',
    classifiers=classifiers.splitlines(),
    install_requires=["pandas", "numpy", "matplotlib"],
    keywords=["sliding", "data", "normalisation", "normalization","array"]
    )