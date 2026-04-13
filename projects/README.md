# Example Projects

This folder contains a curated set of **reference example projects** designed to demonstrate the capabilities of the MicroGridsPy planning framework.

Each project represents a **self-contained configuration** illustrating a specific modeling feature, workflow, or level of system complexity. Together, these examples form a **progressive path**, starting from simple steady-state systems and moving toward dynamic, multi-year planning with advanced technical realism.

These examples can be used to:

- Understand how to structure input data  
- Test new features or model extensions  
- Benchmark solver performance  
- Validate installation and configuration  
- Learn the differences between planning modes  

---

# Overview of Example Projects

The examples are ordered from **simplest to most advanced**, following the conceptual evolution of the modeling framework.

| Project | Description |
|--------|-------------|
| **example_1** | Typical year, off-grid, no degradation |
| **example_2** | Multi-year (10 years), constant demand, off-grid, no degradation |
| **example_3** | Multi-year (10 years), increasing demand (+5%), off-grid, no degradation |
| **example_4** | Multi-year (10 years), increasing demand (+5%), capacity expansion (2 steps), off-grid, no degradation |
| **example_5** | Multi-year (10 years), multi-scenario demand (+2.5%, +5%, +7.5%), off-grid, no degradation |
| **example_6** | Multi-year (10 years), constant demand, off-grid, generator partial-load model |
| **example_7** | Multi-year (10 years), constant demand, off-grid, battery loss model |
| **example_8** | Multi-year (10 years), constant demand, off-grid, battery loss model + cycle fade |
| **example_9** | Multi-year (10 years), increasing demand (+5%), capacity expansion (2 steps), on-grid |
| **example_10** | Multi-year (10 years), increasing demand (+5%), capacity expansion (2 steps), on-grid with emissions |

---

# Conceptual Progression Across Examples

The example projects are intentionally designed to **introduce model features incrementally**, allowing users to isolate the impact of each modelling assumption.

The progression follows this structure:

1. Planning mode complexity  
2. System dynamics  
3. Operational realism  
4. Battery performance  
5. Grid interaction  
6. Environmental accounting  

