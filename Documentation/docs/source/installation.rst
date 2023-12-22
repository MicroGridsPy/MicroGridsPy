#######################################
Download and Installation
#######################################

Requirements
------------

MicroGridsPy has been tested on Linux, macOS, and Windows. Running MicroGridsPy requires:

* The Python programming language, version 3.9.18 
* A number of Python add-on modules (see below for further info).
* A solver: MicroGridsPy has been tested mainly with Gurobi but any other solver that is compatible with Pyomo should also work (GLPK and HiGHS)
* The MicroGrids software folder freely accessible from the environment.

Recommended installation method
-------------------------------

The easiest way to get a working MicroGridsPy installation is to use the free conda package manager, which can install all of the four things described above in a single step. To get conda, download and install the `Anaconda <https://repo.anaconda.com/archive/>`_ distribution for your operating system (using the version for Python 3). Anaconda is a free and open-source distribution of the Python and R programming languages for data science and machine learning-related applications that aims to simplify package management and deployment. With Anaconda installed, it is possible to create a new environment (e.g. "mgp"). To create a modelling environment that already contains everything needed to run MicrogridsPy, it's suggested to download the environment from `here <https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/tree/Environments>`_. After placing the mgp_win.yml file in "C:\Users\youruser", you can create and activate the new mgp environment by running the following command in the Anaconda Prompt terminal:

.. code-block:: python

   conda env create -f mgp_win.yml
   conda activate mgp

To ensure a smooth and efficient operation of MicroGridsPy, it is crucial to properly set up the development environment. This involves creating an isolated space that contains all the necessary Python packages and their specific versions as defined in the MicroGridsPy base.yml file. Key packages include Pyomo (minimum version 6.4.3 for the HiGHS solver), Pandas, NumPy, and Matplotlib.
For code development and debugging, consider using an Integrated Development Environment (IDE) like Spyder, which is included in the created environment.

Solvers
=======

At least one of the solvers supported by Pyomo is required. HiGHS (open-source) or Gurobi (commercial) are recommended for large problems and have been confirmed to work with MicroGridsPy. Refer to the documentation of your solver on how to install it.

Gurobi
------

Gurobi is commercial but significantly faster than CBC and GLPK, which is relevant for larger problems. It needs a license to work, which can be obtained for free for academic use by creating an account on gurobi.com. Gurobi can be installed via conda by means of the following command:

.. code-block:: python

   conda install -c gurobi gurobi

It's recommended to download and install the installer from the Gurobi website, as the conda package has repeatedly shown various issues. After installing, log on to the Gurobi website and obtain a (free academic or paid commercial) license, then activate it on your system via the instructions given online (using the grbgetkey command).

More info at `Gurobi documentation <https://www.gurobi.com/documentation/>`_

HiGHS
-----

.. warning::
   The HiGHS solver integration is currently under active development and will be available soon. This feature is being tested and optimized to ensure seamless performance with MicroGridsPy.

HiGHS is high-performance serial and parallel software for solving large-scale sparse linear programming (LP), mixed-integer programming (MIP) and quadratic programming (QP) models, developed in C++11, with interfaces to C, C#, FORTRAN, Julia and Python.

HiGHS is freely available under the MIT licence and is downloaded from Github. Installing HiGHS from source code requires CMake minimum version 3.15, but no other third-party utilities. HiGHS can be used as a stand-alone executable on Windows, Linux and MacOS. There is a C++11 library which can be used within a C++ project or, via one of the interfaces, to a project written in other languages.

More info at `HiGHS documentation <https://ergo-code.github.io/HiGHS/dev/>`_

Setting the environment
=======================

Refer to ..../base.yml in the MicroGridsPy repository for a full and up-to-date listing of required third-party packages.

Some of the key packages MicroGridsPy relies on are:

**Python Version**

*  Python 3.9.18: The base language version for the environment.

**Data Analysis and Scientific Computing**

*  NumPy (1.26.1): Essential for numerical computing.
*  Pandas (2.1.1): Provides high-performance data structures and analysis tools.
*  SciPy Libraries: Used for advanced computing tasks.

**Optimization**

*  Pyomo (6.6.2): A Python-based open-source optimization modeling language.

**Plotting and Visualization**

*  Matplotlib (3.8.0): For creating a range of static, interactive, and animated visualizations.
*  Seaborn: Enhances matplotlib for statistical data visualization (commonly used alongside pandas and matplotlib).

**Development Tools**

*  Spyder (5.4.3): An IDE for scientific programming in Python.

**Data File Management**

*  Openpyxl (3.1.2): Reads and writes Excel 2010 xlsx/xlsm/xltx/xltm files.

**Web and Internet Handling**

*  Requests: Essential for making HTTP requests, often used in web scraping and API interactions.

**Miscellaneous**

Various libraries for specific functionalities, including cryptography, JSON handling, and file I/O operations.

**Final considerations**

- *Python Version*: Ensure compatibility of all packages with Python 3.9.18. Upgrading Python may require updating packages.
- *Operating System*: This setup is tailored for Windows. Adjustments may be needed for Linux or macOS.
- *Package Versions*: Specified versions are crucial for compatibility and stable operation. Upgrading may cause issues.
- *Additional Dependencies*: Some packages have dependencies not listed in the base.yml file. Ensure all required libraries are installed.
- *Customization and Extensibility*: Install additional packages or modify configurations as needed for specific project requirements.





