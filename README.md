# Welcome to MicroGridsPy!

> **Note:** This version of MicroGridsPy is under **active development** and has not been officially released yet. It is recommended to check regularly for updates and changes in the repository.

**MicroGridsPy** is an open-source optimization model for **energy scaling and dispatch optimization** in microgrids, specifically designed for remote locations. The model now runs using the [Linopy](https://linopy.readthedocs.io/) optimization framework, which provides fast, efficient, and scalable solutions for linear and mixed-integer programming. MicroGridsPy supports both open-source solvers like **HiGHS** and common commercial solvers, giving users a range of options for solving optimization problems.

The model features a **streamlined web interface** built using [Streamlit](https://streamlit.io/), offering a dynamic and user-friendly environment for inputting data, visualizing results, and running optimizations. **Pydantic** is used for robust data validation, ensuring data accuracy and consistency.

With **Streamlit**, users can:
- Interact with **real-time data visualizations** of the optimization process.
- Input parameters through a **responsive web interface**.
- Generate, monitor, and adjust simulation scenarios with ease.
- View **live results and graphical outputs** directly in the browser.
- Use Pydantic's validation to ensure data integrity and minimize input errors.

The goal of MicroGridsPy is to provide an open-source approach to **energy system optimization**, allowing users to design the optimal configuration for their microgrids using advanced modeling techniques.

---

## Features

MicroGridsPy is under continuous development and the latest version includes:

- **Modern Web Interface**: Built with Streamlit for interactive, real-time optimization and scenario exploration.
- **Pydantic-Based Data Validation**: Ensures accurate data entry and provides dynamic feedback to users.
- **Dynamic Data Visualization**: Real-time graphs and metrics during simulation, powered by Streamlit's rich visualization tools.
- **Linopy Optimization**: Leveraging Linopy for scalable and efficient linear/mixed-integer programming.
- **Open-Source Solver Support**: Native support for **HiGHS** as well as integration with commercial solvers.
- **Multi-Year Formulation**: Simulates long-term changes in energy demand.
- **Capacity Expansion**: Plans for future infrastructure investments.
- **Multi-Objective Optimization**: Balances between cost and environmental goals.
- **Mixed-Integer Linear Programming (MILP)**: Ensures optimal generation scheduling while accounting for complex system behavior.
- **Partial Load Generator Modeling**: Considers generator efficiency under varied loads.
- **Endogenous Load Curve Estimation**: Creates load curves based on local rural village data or estimate load demand profiles using excel inputs file with [RAMP](https://github.com/RAMP-project/RAMP), an open-source bottom-up stochastic model for generating multi-energy load profiles
- **Endogenous RES Production Time Series**: Utilizes PVGIS and NASA POWER API for solar and wind predictions.
- **Brownfield Feature**: Takes into account existing technologies in the field.
- **Main Grid Connectivity Simulation**: Models interactions with an existing main grid, including outages.

---

## Quick Start

To get started with **MicroGridsPy**, follow the detailed steps below. These instructions will guide you through setting up your Python environment, downloading the project files, and running the web-based interface for the model.

### 1. Clone or Download the GitHub Repository

Download the MicroGridsPy code by cloning the GitHub repository:

```bash
git clone https://github.com/MicroGridsPy/MicroGridsPy/tree/Development_Linopy.git
```

If you prefer not to use Git, you can directly download the zip folder from GitHub [here](https://github.com/MicroGridsPy/MicroGridsPy/tree/Development_Linopy). Once downloaded, extract the zip file to a location of your choice.

### 2. Install Anaconda or Miniconda (Recommended)

For the smoothest experience, it's recommended to install [Anaconda](https://www.anaconda.com/products/individual) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html). These tools allow you to manage Python environments, ensuring that you can install and manage the dependencies required for **MicroGridsPy** without interfering with your system Python or other projects.

- **Anaconda**: A full-featured environment manager and Python distribution with numerous scientific packages included by default.
- **Miniconda**: A lightweight version of Anaconda, containing just the essentials, letting you install only the packages you need.

After installation, you can create isolated Python environments and easily install any required libraries for **MicroGridsPy**.

#### Install Anaconda or Miniconda:
- **For Anaconda**: [Download and install Anaconda](https://www.anaconda.com/products/individual).
- **For Miniconda**: [Download and install Miniconda](https://docs.conda.io/en/latest/miniconda.html).

### 3. Create and Characterize a Python Environment

Once Anaconda or Miniconda is installed, the next step is to create a Python environment dedicated to running **MicroGridsPy**. This keeps the required libraries isolated from your main Python environment.

#### Step-by-step process:
1. Open the **Anaconda Prompt** or any terminal of your choice.
2. Use the following command to create a new Python environment. In this example, the environment is named `myenv`, but you can use any name you prefer.

```bash
# Create a new environment (replace 'myenv' with your preferred environment name)
conda create --name myenv python=3.9

# Activate the environment
conda activate myenv
```

Now that your environment is active, install the required packages using the requirements.txt file contained in the project repository. This file lists all the dependencies needed to run MicroGridsPy.

```bash
# Change Directory to MicroGridsPy downloaded project folder
# Replace with the actual path where you saved the MicroGridsPy project
cd path/to/MicroGridsPy

# Install required packages from the requirements.txt file
pip install -r requirements.txt
```

Alternatively, you can manually install the required packages using pip. An example is:

```bash
# Install Streamlit for the user interface
pip install streamlit

# Install the linopy optimization library
pip install linopy==0.3.14

# Install additional libraries for data handling, plotting, and other functionalities
pip install xarray==2024.3.0
pip install pydantic
pip install pyyaml
pip install folium
pip install streamlit-folium
pip install geopy
pip install openpyxl
pip install matplotlib
pip install seaborn
pip install rampdemand
pip install highspy
```

### 4. Navigate to the Project Directory

Everytime you want to launch the model, change directory to the folder where the MicroGridsPy files are located. If you cloned the repository, use the following command to move into the project directory:

```bash
# Replace with the actual path where you saved the MicroGridsPy project
cd path/to/MicroGridsPy
```

### 5. Launch the Streamlit user interface

To run the MicroGridsPy model, execute the following command from within the project directory. Make sure that your environment is still activated:

```bash
streamlit run main.py
```

This will launch a local instance of the Streamlit web app in your default web browser. A web page will open on localhost (typically at http://localhost:8501), where you can interact with the model through an intuitive user interface.

The web interface allows you to input parameters, run simulations, and visualize the results directly.

Happy modeling!

---

## Contributors

MicroGridsPy is mantained by the SESAM group in the Department of Energy Engineering at Politecnico di Milano. The research activity of SESAM focuses on the use of mathematical models for the study of systems, components, and processes in the energy field and industrial ecology.

The current version of **MicroGridsPy** in linopy has been developed by **Alessandro Onori**, based on the original model created in Pyomo with contributions from other developers and the previous version listed here below:

- **Nicolò Stevanato**, Politecnico di Milano
- **Riccardo Mereu**, Politecnico di Milano
- **Emanuela Colombo**, Politecnico di Milano
- **Gianluca Pellecchia**, Politecnico di Milano
- **Ivan Sangiorgio**, Politecnico di Milano
- **Francesco Lombardi**, TU Delft
- **Giulia Guidicini**, Politecnico di Milano
- **Lorenzo Rinaldi**, Politecnico di Milano

### Based on the original model by:
- **Sergio Balderrama**, Universidad Mayor de San Simón <s.balderrama@umss.edu>
- **Sylvain Quoilin**, Université de Liège <squoilin@uliege.be>

## License
This is a free software licensed under the “European Union Public Licence" EUPL v1.1. It can be redistributed and/or modified under the terms of this license.
