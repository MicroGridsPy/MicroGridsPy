# MicroGridsPy

**MicroGridsPy** is an open-source Python package for the techno-economic planning of
mini-grid energy systems in remote and underserved areas. It builds and solves
linear / mixed-integer optimization models — via [Linopy](https://linopy.readthedocs.io) —
that size renewable generation, battery storage, and backup generation at least cost.

!!! note "Proof-of-concept documentation"
    This site is a minimal proof of concept demonstrating the documentation toolchain:
    **Zensical** generates the site, **mkdocstrings** builds the
    [API Reference](api.md) automatically from the package source, and **Read the Docs**
    builds and hosts it. Explanatory pages like this one sit alongside the
    auto-generated reference.

## Installation

```bash
pip install "microgridspy[highs]"
```

## Quickstart

```python
import microgridspy as mgp

# scaffold a project and its input templates
mgp.create_project("my_site", formulation="steady_state", resources=["solar", "wind"])

# ...fill in the load demand, resource availability, and techno-economic inputs...

mgp.validate_project("my_site")
results = mgp.solve("my_site", solver="highs").results()
print(results.kpis)
```

## The optimization problem

At its core, the planning model minimizes the discounted total system cost over the
planning horizon — the sum of annualized investment and expected operating costs:

$$
\min \; \sum_{y=1}^{Y} \frac{C^{\text{inv}}_{y} + \mathbb{E}\left[C^{\text{op}}_{y}\right]}{(1 + r)^{\,y}}
$$

subject to an hourly energy balance in every scenario $s$ and time step $t$:

$$
\sum_{g} P_{g,s,t} + P^{\text{dis}}_{s,t} + P^{\text{grid}}_{s,t} = D_{s,t} + P^{\text{ch}}_{s,t} + P^{\text{curt}}_{s,t}
$$

where $P_{g,s,t}$ is generation from technology $g$, $P^{\text{ch}}$/$P^{\text{dis}}$ are
battery charge/discharge, and $D_{s,t}$ is the served demand.

## Planning modes

- **Typical-year** — a single representative year; compact and fast, for screening.
- **Multi-year** — an explicit horizon with capacity expansion, degradation, and
  discounted cash flows.

See the [API Reference](api.md) for the full programmatic interface.
