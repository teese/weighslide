"""
 Weighslide is a program for sliding window analysis of a list of numerical values,
 using flexible windows determined by the user.
"""
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
# Get the long description from the README file
with open(path.join(here, 'README.md'), "r", encoding='utf-8') as f:
    long_description = f.read()

setup(name='weighslide',
      packages=find_packages(),
      version='0.2.5',
      description="Flexible sliding window analysis",
      author='Mark Teese',
      author_email='mark.teese@SeeImageBelow.de',
      long_description=long_description,
      long_description_content_type='text/markdown',
      url="https://github.com/teese/weighslide",
      download_url='https://github.com/teese/weighslide/archive/0.2.5.tar.gz',
      project_urls={'LangoschLab': 'http://cbp.wzw.tum.de/index.php?id=9', "TU_Muenchen": "https://www.tum.de"},
      license='MIT',
      classifiers=[
          "Intended Audience :: Science/Research",
          'License :: OSI Approved :: MIT License',
          "Programming Language :: Python :: 3.6",
          "Topic :: Scientific/Engineering :: Bio-Informatics"
      ],
      install_requires=["pandas", "numpy", "matplotlib", "pytest"],
      keywords="sliding data normalisation normalization array"
      )
