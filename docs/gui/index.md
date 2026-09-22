# Graphical Interface (GUI)

MicroGridsPy can be used two ways: **as a Python library** (`import microgridspy`) or **as a
guided app** — a **Streamlit** application that walks you through defining a project, auditing
its data, solving, and exploring results, without writing any code. Both front-ends drive the
same Linopy optimization and the same project-folder workflow, so a study created in the app
can be solved from a script and vice versa.

![The MicroGridsPy Planning home screen — "Welcome to MicroGridsPy!" with the planning-tool card and an Open Project Setup button](../assets/gui/intro_interface.png)

*The MicroGridsPy Planning home screen. The app is the techno-economic optimization layer of
the broader MicroGridsPy ecosystem.*

## Launching the app

The GUI ships with the optional `gui` extra. Install it and start the app with the console
command:

```bash
pip install "microgridspy[gui,highs]"
microgridspy-gui
```

`microgridspy-gui` launches the Streamlit server and opens the app in your browser. See
[Installation](../getting-started/installation.md) for the full set of extras and solvers.

## The guided workflow

Every project follows the same sequence, whichever planning mode you choose:

```text
1. Launch the app and open Project Setup
2. Create a project folder under projects/<project_name>/
3. Select the planning formulation (typical-year or multi-year)
4. Configure the high-level settings that determine which templates are generated
5. Click "Initialize project and generate templates"
6. Edit the generated input files under projects/<project_name>/inputs/
7. Open Data Audit & Visualization to confirm the dataset loads and dimensions match
8. Open Optimization and solve the model
9. Open Results to inspect sizing, operation, costs, emissions, and exports
```

Steps 1–5 happen in the app; step 6 is where you fill in your case-study data (the generated
files are **templates** — see [Input Data](../user-guide/input-data.md#validation) and the
[Data Reference](../data-reference/overview.md)); steps 7–9 return to the app.

## The application pages

The app is a Streamlit multi-page project. The sidebar exposes four working pages plus the
landing page.

### Home

The landing page (**Welcome to MicroGridsPy!**) introduces the two planning formulations and
the surrounding ecosystem tools, and links onward to the working pages. It does not configure
the model directly — the primary action is **Open Project Setup**.

### Project Setup

Creates or loads projects, via two tabs.

**Create tab** — the single place where a new study is defined. It controls:

- project name and description;
- **formulation** selection (typical-year vs. multi-year);
- **grid and export** settings (off-grid / on-grid, export on/off);
- renewable-resource **count and labels**;
- **uncertainty** settings (single vs. multi-scenario, scenario labels and weights);
- **battery and generator** advanced-model options (convex battery loss, endogenous
  degradation, generator efficiency curve);
- **optimization constraints** (renewable penetration, lost-load, land, emission cost,
  enforcement mode);
- **template generation** — the *Initialize project and generate templates* action.

Clicking initialize writes `formulation.json` and the input templates into
`projects/<project_name>/inputs/`.

**Load tab** — marks an existing project as **active** without regenerating its inputs.

!!! warning "Regenerating overwrites inputs"
    Creating a project with a name that already exists **overwrites** the files in `inputs/`
    using the current Project Setup selections. Back up or review any user-edited inputs before
    regenerating.

Which files Project Setup generates depends on your choices; the mapping is summarized in
[UI → project settings](#ui-project-settings) below, and the files themselves are documented in
the [Data Reference](../data-reference/overview.md).

### Data Audit & Visualization

Reads `inputs/formulation.json`, initializes the formulation-specific sets, loads the canonical
project dataset, and gives you a pre-solve audit of the study:

- required and optional **input-file status**;
- **dataset-loading** status and **coordinate** summaries (`period`, `scenario`, `year`,
  `resource`, `inv_step`);
- **parameter** and **optimization-constraint** summaries;
- **advanced-curve diagnostics** (battery loss / calendar-fade / generator efficiency curves);
- **grid-availability** controls for on-grid projects;
- **time-series plots** of the loaded inputs, with multi-year and scenario comparisons.

For on-grid projects, `grid_availability.csv` is a **derived artifact** and can be regenerated
here from `grid.yaml`. The coordinates and variables shown on this page correspond one-to-one
to the canonical dataset described in the [Internal Data Contract](../data-reference/data-contract.md).

### Optimization

Builds and solves the model for the active project. It:

- requires an active project and reads `inputs/formulation.json`;
- builds the formulation-specific optimization model;
- lets you select the **solver** (`highs`, open source, or `gurobi`, licensed);
- optionally writes a **problem file** (LP/MPS) for inspection;
- stores a **solver log** under `projects/<project_name>/logs/`;
- solves the single-objective planning problem.

### Results

Dispatches to the formulation-specific results renderer and presents:

- **sizing summary** — installed capacity by technology (and by investment step in multi-year);
- **performance KPIs** — LCOE, renewable share, reliability, emissions;
- **least-cost energy mix** and operational summaries;
- **cost summary & cash-flow** — investment, O&M, fuel, discounted cash flows;
- **scenario-specific** operational costs and emissions;
- **export** — write the result tables to CSV/Excel in the project's `results/` folder.

These outputs mirror the structured results objects available from the library
(`TypicalYearResults` / `MultiYearResults`); see the User Guide [Results](../user-guide/results.md)
page for how to interpret them and the [Methodology](../methodology/overview.md) for what each
quantity means.

## Where the GUI meets the data model

The app is a front-end over the same project folder the library uses. Understanding two things
makes the interface predictable:

- **Project Setup generates templates, not a runnable case.** The generated CSVs are empty and
  the economic YAML values default to zero — you must fill in demand, resource availability, and
  costs before solving. See [Input Data](../user-guide/input-data.md) and the per-file
  [Data Reference](../data-reference/overview.md).
- **The pages read and write the canonical dataset.** What Data Audit displays and what
  Optimization consumes is the single `xarray` dataset defined by the
  [Internal Data Contract](../data-reference/data-contract.md) — the same interface the library
  builds.

### UI → project settings

Each Project Setup choice maps to a flag in `formulation.json` and, in turn, to which input
files are generated:

| UI choice | Effect |
|---|---|
| **Formulation: Multi-Year** | writes `core_formulation = "dynamic"` |
| **Formulation: Typical-Year** | writes `core_formulation = "steady_state"` |
| **Start year & horizon** | set the multi-year `year` coordinate and CSV year headers |
| **Capacity expansion enabled** | generates multiple `investment.by_step` blocks (multi-year) |
| **On-grid mode** | generates `grid.yaml` and `grid_import_price.csv` |
| **Export enabled** | also generates `grid_export_price.csv` |
| **Multi-scenario mode** | replicates scenario labels across CSV headers and scenario-keyed YAML |
| **Battery loss = convex** | generates the battery efficiency-curve template, activates curve loader |
| **Battery calendar fade enabled** | generates the calendar-fade curve template and fields |
| **Generator efficiency = curve** | generates the generator efficiency-curve template |

The generated files, their formats, units, and when each is required are documented in full in
the [Data Reference](../data-reference/overview.md); the mathematical meaning of the options is
in the [Methodology](../methodology/planning-modes.md).

## Command-line alternative

The same create → validate → solve workflow is also available headless through the
`microgridspy` console command (installed with the package), which wraps the public API — useful
for scripting and reproducible runs:

```bash
microgridspy list
microgridspy create my_site --resources solar wind
microgridspy validate my_site
microgridspy solve my_site --solver highs --export
```
