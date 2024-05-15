#######################################
Download and Installation
#######################################

Running MicroGridsPy requires:

1. Install and use Anaconda (or Miniconda)
2. Install and set up the environment for MicroGridsPy
3. Install a Solver among the supported ones (Gurobi - license required, GLPK - free to access)
4. Download and Launch MicroGridsPy with Graphical User Interface (GUI)

.. warning::
   
      The installation steps following refer to Windows. The environment for macOS (version 2.1) of MicroGridsPy is currently under development and not available. 
      We advise macOS or Linux users to rely on MicroGridsPy version 2.0 until the new environment is fully developed and released.


1 - Install Anaconda (or Miniconda)
======================================

Anaconda's package manager, known as conda, is a powerful tool for managing packages, dependencies, and environments in the Anaconda ecosystem. It is designed to handle various types of packages, including Python and R, and works across multiple platforms (Windows, macOS, and Linux). Here are key features and functions of conda:

* **Package Management**: conda allows users to install, update, and remove packages. It hosts a large repository of scientific packages and ensures that the installed packages are compatible with each other.
* **Environment Management**: One of the most significant features of conda is its ability to create isolated environments. These environments can have different versions of Python and packages, making it easier to manage dependencies for different projects without conflicts.
* **Cross-Platform Compatibility**: conda works on various operating systems, providing a consistent experience across platforms.
* **Large Repository**: Anaconda comes with a vast repository of pre-built packages specifically tailored for scientific computing, data science, and machine learning applications. This saves time and effort in compiling and configuring these complex packages.
* **Open Source and Community-Driven**: conda is open-source and benefits from community contributions, which means a wide range of packages and continuous updates.
* **Ease of Use**: While it offers a command-line interface, conda is designed to be user-friendly, making package and environment management accessible to users regardless of their expertise in command-line tools.

**To install Conda:**

1. Download and install the `Anaconda distribution <https://www.anaconda.com/download>`_ that includes support for Python 3, ensuring compatibility with MicroGridsPy.
   You can find also a complete list of installation files and old versions `here <https://repo.anaconda.com/archive/>`_ .

2. Follow the installation instructions provided for your specific operating system.

.. note::

   Review the system requirements before installing Anaconda Distribution. If you want a more lightweight installation, you can opt for `Miniconda <https://docs.conda.io/en/latest/miniconda.html>`_, which includes only conda and Python, allowing you to install additional packages as needed.
   For the scope of using and running MicroGridsPy **Miniconda** is sufficient and recommended if you have limited disk space or want more control over the packages installed on your system.

Getting started with conda using the Anaconda Prompt
------------------------------------------------------

Conda is a powerful package manager and environment manager that you use with command line commands at the Anaconda Prompt for Windows, or in a terminal window for macOS or Linux.

**Windows:**

From the Start menu, search for and open "**Anaconda Prompt**”. The Anaconda Prompt is a command-line interface tool that comes with Anaconda. 
It is particularly tailored for managing Python environments and packages within the Anaconda ecosystem and it enables users to execute Python scripts, install new packages via conda (Anaconda's package manager), create isolated environments to avoid dependency conflicts, and update the Anaconda distribution itself. On Windows, all commands below are typed into the Anaconda Prompt window.

**MacOS:**

Open Launchpad, then click the terminal icon. On macOS, all commands below are typed into the terminal window.

**Linux:**

Open a terminal window. On Linux, all commands below are typed into the terminal window.

Manage conda
-----------------

Verify that conda is installed and running on your system by typing:

.. code-block:: bash

    conda --version

Conda displays the number of the version that you have installed. You do not need to navigate to the Anaconda directory.

.. note::

    If you get an error message, make sure you closed and re-opened the terminal window after installing, or do it now. Then verify that you are logged into the same user account that you used to install Anaconda or Miniconda.

Update conda to the current version. Type the following:

.. code-block:: bash

    conda update conda

Conda compares versions and then displays what is available to install. If a newer version of conda is available, type ``y`` to update.

.. note::

      We recommend that you always keep conda updated to the latest version.


Getting started with Anaconda Navigator
------------------------------------------

**Anaconda Navigator** starts by default when Anaconda (and not Miniconda) Distribution is first installed. Anaconda Navigator is a graphical user interface (GUI) tool included with the Anaconda distribution. 
It serves as an alternative to the Anaconda Prompt, offering a more user-friendly way to manage the various aspects of the Anaconda environment without needing to use command-line instructions.

**Windows:**

From the Start menu, search for “Anaconda Navigator” and click to open.

**MacOS:**

Open Launchpad, then click the Anaconda-Navigator icon.

**Linux:**
1. Open a terminal window.
2. Open Navigator by using the following command: *anaconda navigator*

Managing Navigator
---------------------

Through the Anaconda Navigator, users can easily manage their Python environments, install and update packages, and launch applications included in the Anaconda distribution, like Jupyter Notebooks, Spyder, RStudio, and others. It's particularly advantageous for those
who prefer a visual interface over command-line operations. The Navigator allows for easy access to different tools and simplifies the process of setting up and maintaining Python environments for various projects. This is especially beneficial for beginners or those who prefer a more intuitive, point-and-click experience in managing their Python development setup.
By default, all application tiles available to launch or install within Navigator are displayed on the Home page. Filter the application tiles with the applications dropdown menu.

2 - Install MicroGridsPy Environment
======================================

In conda, an *environment* is an isolated space that allows users to maintain different versions of Python and various packages without interference. Each environment can have its own specific set of packages and Python versions, independent of others. This is particularly useful in managing dependencies and avoiding conflicts when working on multiple projects with differing requirements. By using environments, developers and data scientists can ensure consistency and reproducibility of their work across various setups and collaborations.

Create the Environment from Anaconda Prompt
-------------------------------------------

When you begin using conda, you already have a default environment named `base`. To create a modelling environment that already contains everything needed to run MicrogridsPy, download the environment **YML file** named ``mgpy_win.yml`` from the following GitHub repository:

https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/Environments/mgpy_win.yml

Follow these steps to create the environment:

1. Place the YML file (`mgpy_win.yml`) in ``C:/Users/youruser``.

2. Open the Anaconda Prompt.

3. Type the following command in the Anaconda Prompt terminal:

   .. code-block:: bash

      conda env create -f mgpy_win.yml

4. Activate the environment by:

   .. code-block:: bash

      conda activate mgpy

.. note::

    `conda activate` only works on conda 4.6 and later versions.

Create the Environment from Anaconda Navigator
----------------------------------------------

1. **Launch Anaconda Navigator**: Open Anaconda Navigator on your computer.

2. **Navigate to Environments**: On the left-hand side of the Navigator window, click on the "Environments" tab.

3. **Import Environment**: Look for the "Import" button at the bottom of the environment list and click on "Import".

4. **Select the YML File**: In the import dialog, you will see a field to choose the YML file. Click on the folder icon next to the text box to browse your computer and select the `.yml` file you want to use.

5. **Name Your Environment**: Below the file selection, there's a field to name your new environment. Choose a meaningful name for the environment you're creating (e.g. `mgpy`).

6. **Create Environment**: After selecting the file and naming your environment, click the "Import" button. Anaconda Navigator will start creating the environment using the specifications in the YML file. This process may take some time, depending on the number of packages to be installed and your internet connection speed.

7. **Activation**: Once the environment is created, you can activate it by selecting it from the list in the "Environments" tab.

To use this environment, you can open tools like Jupyter Notebook, Spyder, or a terminal from within the Navigator while the environment is active.


3 - Install a Solver
=====================

**Gurobi:** 

Gurobi is a leading mathematical optimization solver renowned for its efficiency in solving linear, mixed-integer, and quadratic programming problems.
Gurobi stands out for its high-performance capabilities, user-friendly interfaces compatible with multiple programming languages, and continuous updates incorporating the latest algorithmic advancements. While it offers free academic licenses, its **commercial use** is governed by a comprehensive licensing model, making it an essential tool for researchers and professionals alike in optimizing complex decision-making processes.
More info at `Gurobi documentation <https://www.gurobi.com/documentation/>`_

**GLPK:**

GLPK is an open-source solver for Linear Programming (LP) and Mixed Integer Programming (MIP). It’s a suitable option for smaller to medium-sized problems and offers a free alternative to commercial solvers. 

.. warning::

   While GLPK is a capable solver for many optimization problems, it may have longer operational times compared to commercial solvers like Gurobi, especially for large or complex problems. 
   The difference can often be substantial, potentially ranging from several times to orders of magnitude faster, depending on the specifics of the problem even if 
   it's important to note that these are general observations, and actual performance will vary with each unique problem. It is advisable to consider this factor when choosing a solver for time-sensitive or large-scale applications.

Refer to (:doc:`example`) for more details about the specific performances of the two solvers compared for a test model simulation.

**HiGHS:**

HiGHS is high-performance serial and parallel software for solving large-scale sparse linear programming (LP), mixed-integer programming (MIP) and quadratic programming (QP) models, developed in C++11, with interfaces to C, C#, FORTRAN, Julia and Python.
HiGHS is freely available under the MIT licence and is downloaded from Github. Installing HiGHS from source code requires CMake minimum version 3.15, but no other third-party utilities. HiGHS can be used as a stand-alone executable on Windows, Linux and MacOS. There is a C++11 library which can be used within a C++ project or, via one of the interfaces, to a project written in other languages.

.. warning::

   The HiGHS solver integration is currently under active development and will be available soon. This feature is being tested and optimized to ensure seamless performance with MicroGridsPy.

More info at `HiGHS documentation <https://ergo-code.github.io/HiGHS/dev/>`_

Obtain a Gurobi License
-----------------------

Before installing Gurobi, you need to obtain a license. Gurobi offers different types of licenses, including academic licenses which are free for academic purposes. Visit the Gurobi website and register for a license, then follow their instructions to set up your license: `Gurobi website <https://www.gurobi.com>`_

Installing Gurobi using Anaconda Prompt
---------------------------------------

1. Open the Anaconda Prompt (or your terminal in Linux/Mac).

2. Activate the `mgpy` environment.

   .. code-block:: bash

      conda activate mgpy

3. Install the Gurobi package by running:

   .. code-block:: bash

      conda install -c gurobi gurobi

4. Once Gurobi is installed, you need to activate your license. This usually involves running a command provided by Gurobi in your Anaconda Prompt or terminal. If you're using an academic license, you typically run:

   .. code-block:: bash

      grbgetkey YOUR_LICENSE_KEY

   Refer to the Gurobi website for more information about license installation.

Installing Gurobi using Anaconda Navigator
------------------------------------------

1. Launch Anaconda Navigator on your computer.

2. In Anaconda Navigator, go to the "Environments" tab. Click on "Channels" and then on "Add". Type `gurobi` and click on the "Update channels" button. This step ensures that the Gurobi package can be found in the Anaconda repository.

3. Click on the "Home" tab, then select the MicroGridsPy environment you created from the drop-down menu.

4. In the search bar, type "Gurobi". When Gurobi appears in the list, select it and click on "Apply" to install.

5. Follow the instructions provided by Gurobi for activating your license. This typically involves running a command in your terminal or Anaconda Prompt.

Installing GLPK using Anaconda Prompt
---------------------------------------

If you are using Anaconda, GLPK can be installed easily using the Conda package manager. To install GLPK, open your Anaconda Prompt or terminal and enter the following command:

.. code-block:: python

    conda install -c conda-forge glpk

This command installs GLPK and ensures that it is added to your environment's path, allowing Pyomo to automatically detect and use it.

Installing GLPK using Anaconda Navigator
-------------------------------------------

1. Launch Anaconda Navigator on your computer.

2. In Anaconda Navigator, go to the "Environments" tab and select the MicroGridsPy environment from the list.

3. Click on the "Channels" button at the bottom of the window, then click on "Add". Type `conda-forge` and click "Update channels" to ensure that the GLPK package is available in the Anaconda repository.

4. Click on the "Home" tab and ensure the MicroGridsPy environment is selected from the drop-down menu.

5. In the search bar, type "GLPK". When GLPK appears in the list, select it and click "Apply" to install.

By following these steps, you can easily install and configure both Gurobi and GLPK solvers within your Anaconda environments, ensuring you have the appropriate tools for your optimization tasks.

4 - Download and Launch MicroGridsPy with GUI
===============================================

Download the MicroGridsPy Folder
--------------------------------

To actually use MicroGridsPy, first download the folder of the model from GitHub. Open your web browser and go to the SESAM GitHub repository at this link:

`SESAM-Polimi/MicroGridsPy-SESAM: MicroGridsPy - SESAM-PoliMi (github.com) <https://github.com/SESAM-Polimi/MicroGridsPy-SESAM>`_

Click the green "Code" button on the right side and select "Download ZIP" to download the entire folder as a ZIP file. Unzip and place the folder wherever it’s easily accessible in your system.

.. figure:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Mgpy_download.png?raw=true
   :width: 700
   :align: center

----------------------------------------------------------

Launch Spyder using Anaconda Prompt
-----------------------------------

Spyder is an open-source integrated development environment (IDE) primarily designed for scientific and data-driven computing in the Python programming language. It provides a user-friendly and interactive environment for tasks such as data analysis, scientific research, machine learning, and numerical computing. Spyder offers features like a code editor, IPython console integration, variable explorer, and a comprehensive set of tools for data visualization and exploration, making it a popular choice among data scientists and researchers for Python-based projects.

.. note::

      If you prefer to use another IDE, such as **Visual Studio Code**, ensure it is installed on your system. You can start Visual Studio Code by opening the application normally and ensuring the correct Python interpreter from the mgpy environment is selected. 
      Make sure to configure Visual Studio Code to use the Python interpreter from the activated `mgpy` environment by selecting it from the interpreter options in the bottom bar or via the command palette.

To launch Spyder using the Anaconda Prompt, follow these steps:

1. Open the Anaconda Prompt.
2. Activate the `mgpy` environment:

   .. code-block:: bash

      conda activate mgpy

3. Type the following command to open the Spyder interface:

   .. code-block:: bash

      spyder

Launch Spyder using Anaconda Navigator
--------------------------------------

1. **Launch Anaconda Navigator**: Start by opening Anaconda Navigator on your computer. You can typically find it in your list of installed applications or use the Anaconda Navigator shortcut if you have one.
2. **Activate the `mgpy` environment**: Activate the `mgpy` environment from the "Environments" tab in Anaconda Navigator.
3. **Open Spyder**: In Anaconda Navigator, navigate to the "Home" tab. You will see a list of available applications and tools. Look for "Spyder" in the list. Click on the "Launch" button next to Spyder to open the Spyder IDE.

Launch the GUI within Spyder
----------------------------------

After launching the Spyder IDE, you should see the following page:

.. figure:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Mgpy_spyder.png?raw=true
   :width: 700
   :align: center

If you have visualization problems, you can always set the default layout from the “View” button.

4. **Locate the MicroGridsPy Working Folder**: In Spyder, go to the "File" menu at the top left corner of the interface. Select "Open..." to open a file or folder.
5. **Navigate to the MicroGridsPy Folder**: Use the file browser to navigate to the location where you have the MicroGridsPy project folder stored on your computer.
6. **Open the MicroGridsPy Folder**: Double-click on the MicroGridsPy project folder to open it within the Spyder interface. You should now see the contents of the project folder displayed in the Spyder File Explorer.
7. **Locate `app_main.py`**: In the File Explorer panel on the left-hand side of the Spyder interface, navigate to the "Code/User Interface" folder within the MicroGridsPy project folder. Look for the `app_main.py` file within this folder.
8. **Open `app_main.py`**: Double-click on the `app_main.py` file to open it in the Spyder code editor.
9. **Run `app_main.py`**: With `app_main.py` open in the code editor, you can run it by pressing `F5` or using the "Run" button in Spyder's toolbar. Alternatively, you can right-click in the code editor and select "Run File" from the context menu.

.. figure:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Mgpy_run.png?raw=true
   :width: 700
   :align: center

After running `app_main.py`, the interface of MicroGridsPy should launch within Spyder.

.. figure:: https://github.com/SESAM-Polimi/MicroGridsPy-SESAM/blob/MicroGridsPy-2.1/docs/source/Images/Mgpy_gui.png?raw=true
   :width: 700
   :align: center

Well done: you can now interact with the application as needed for your specific use case!






