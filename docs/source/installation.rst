#######################################
Download and Installation
#######################################

Running MicroGridsPy requires:

* The Python programming language, version 3.9.18 
* A number of Python add-on modules (see below for further info).
* A solver: MicroGridsPy has been tested mainly with Gurobi but it is also available the open source GLPK and, in a development stage, any solvers compatible with Pyomo may also work.
* The MicroGridsPy software folder freely accessible from the environment.

.. warning::
   
      The installation steps following refer to Windows. The environment for macOS (version 2.1) of MicroGridsPy is currently under development and not available. 
      We advise macOS or Linux users to rely on MicroGridsPy version 2.0 until the new environment is fully developed and released.


Recommended Installation Method
===================================

Conda Package Manager
---------------------

The recommended way to install MicroGridsPy is through the Conda package manager. Conda is an open-source package management system and environment management system that simplifies package management and deployment for Python and R languages, especially in data science and machine learning applications.

**To install Conda:**

1. Download and install the `Anaconda distribution <https://repo.anaconda.com/archive/>`_ that includes support for Python 3, ensuring compatibility with MicroGridsPy.

2. Follow the installation instructions provided for your specific operating system.

Creating the mgpy environment
-----------------------------

With Anaconda installed, setting up a specific environment for MicroGridsPy ensures that all dependencies are handled appropriately.

**Steps to set up the mgpy environment:**

1. Download the environment YML file from the `MicroGridsPy SESAM GitHub - Environments <https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/tree/Environments>`_. Save the ``mgpy_win.yml`` file in a directory on your machine, for example, ``C:/Users/youruser`` or another location of your choice.

2. Open the Anaconda Prompt. If you saved the ``mgpy_win.yml`` file in the default directory, such as ``C:/Users/youruser``, you are already in the correct directory. If you saved it in a different location, navigate to that directory using the `cd` command. For example: *cd path/to/your/directory*.

3. Run the following commands to create the mgpy environment from the YML file:

   .. code-block:: bash

      conda env create -f mgpy_win.yml

The mgpy environment is now set up and ready to use. 

Operating MicroGridsPy
----------------------

1. The first step is to activate the mgpy environment with the following command:

   .. code-block:: bash

      conda activate mgpy

2. Then, to use Spyder (already installed within the mgpy environment), run the following command:

   .. code-block:: bash

      spyder

To start working with MicroGridsPy, navigate to the *Code/User Interface* folder, open the ``app_main.py`` file in Spyder (or your preferred IDE), and execute the file to launch the MicroGridsPy user interface.

.. figure:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Mgpy%20installation.png?raw=true
   :width: 800
   :align: center

   Installation steps for MicroGridsPy using Anaconda and Spyder as IDE.

.. note::

      If you prefer to use another IDE, such as **Visual Studio Code**, ensure it is installed on your system. You can start Visual Studio Code by opening the application normally and ensuring the correct Python interpreter from the mgpy environment is selected. 
      Make sure to configure Visual Studio Code to use the Python interpreter from the activated `mgpy` environment by selecting it from the interpreter options in the bottom bar or via the command palette.


Solvers
========

At least one of the solvers supported by Pyomo is required. HiGHS (open-source) or Gurobi (commercial) are recommended for large problems. 
Gurobi and GLPK have been confirmed to work with MicroGridsPy. Refer to the documentation of your solver on how to install it.

.. note::

   Gurobi and GLPK solvers are build-in options within MicroGridsPy environment. 
   GLPK is ready to use and open-source while Gurobi requires the activation of a license online since it's a commercial software (more info below).


GLPK (GNU Linear Programming Kit)
---------------------------------

GLPK is an open-source solver for Linear Programming (LP) and Mixed Integer Programming (MIP). It's a suitable option for smaller to medium-sized problems and offers a free alternative to commercial solvers.

If you are using Anaconda, GLPK can be installed easily using the Conda package manager. To install GLPK, open your Anaconda Prompt or terminal and enter the following command:

.. code-block:: python

    conda install -c conda-forge glpk

This command installs GLPK and ensures that it is added to your environment's path, allowing Pyomo to automatically detect and use it.

.. warning::

   While GLPK is a capable solver for many optimization problems, it may have longer operational times compared to commercial solvers like Gurobi, especially for large or complex problems. 
   The difference can often be substantial, potentially ranging from several times to orders of magnitude faster, depending on the specifics of the problem even if 
   it's important to note that these are general observations, and actual performance will vary with each unique problem. It is advisable to consider this factor when choosing a solver for time-sensitive or large-scale applications.

Refer to (:doc:`example`) for more details about the specific performances of the two solvers compared for a test model simulation.

Gurobi
------

Gurobi is commercial but significantly faster than GLPK, which is relevant for larger problems. It needs a license to work, which can be obtained for free for academic use by creating an account on gurobi.com. Gurobi can be installed via conda by means of the following command:

.. code-block:: python

   conda install -c gurobi gurobi

It's recommended to download and install the installer from the Gurobi website, as the conda package has repeatedly shown various issues. After installing, log on to the Gurobi website and obtain a (free academic or paid commercial) license, then activate it on your system via the instructions given online (using the grbgetkey command).

.. warning::

   Gurobi is not open-source and free for non-academic use. Commercial licenses for Gurobi can be costly, and it's important to consider this when planning for larger-scale or commercial projects. 
   For precise pricing details and licensing options, refer to `Gurobi website <https://www.gurobi.com>`_.
   
More info at `Gurobi documentation <https://www.gurobi.com/documentation/>`_



HiGHS
-----

HiGHS is high-performance serial and parallel software for solving large-scale sparse linear programming (LP), mixed-integer programming (MIP) and quadratic programming (QP) models, developed in C++11, with interfaces to C, C#, FORTRAN, Julia and Python.

HiGHS is freely available under the MIT licence and is downloaded from Github. Installing HiGHS from source code requires CMake minimum version 3.15, but no other third-party utilities. HiGHS can be used as a stand-alone executable on Windows, Linux and MacOS. There is a C++11 library which can be used within a C++ project or, via one of the interfaces, to a project written in other languages.


.. warning::
   The HiGHS solver integration is currently under active development and will be available soon. This feature is being tested and optimized to ensure seamless performance with MicroGridsPy.

More info at `HiGHS documentation <https://ergo-code.github.io/HiGHS/dev/>`_

Environment Overview
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

*  Pyomo (6.7): A Python-based open-source optimization modeling language.

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





