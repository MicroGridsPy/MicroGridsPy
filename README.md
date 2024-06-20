MicroGridsPy Environment
================================

This branch contains environment files for setting up MicroGridsPy across different versions and platforms. Use these files to configure your environment on Windows or macOS using [Conda](https://docs.conda.io/projects/conda/en/latest/index.html).

## Quick Start

* Install [Anaconda](https://www.anaconda.com/products/individual) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html) if you haven't already.

* Download the environment YAML file for your desired version and place it in “C:/Users/youruser”

* Create and activate the mgpy environment by running the following command in the Anaconda Prompt terminal:

   ```bash
   conda env create -f mgpy_win.yml
   conda activate mgpy

> :warning: **Warning**: The environment for macOS (version 2.1) of MicroGridsPy is currently under development and not available. We advise macOS users to rely on MicroGridsPy version 2.0 until the new environment is fully developed and released.
