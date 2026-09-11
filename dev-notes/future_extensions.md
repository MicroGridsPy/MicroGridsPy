# Future Extensions — internal notes

Backlog of generator/battery modelling ideas discussed during the partial-load /
degradation work. **Internal only** — this file lives outside `docs/`, so it is not
part of the published site.

Context / status: the generator partial-load model was moved from the (buggy) convex
fuel-majorant to an **affine Willans fuel line + clustered unit commitment**
(Palmintier & Webster), with modes `off | integer` and an optional `min_load_fraction`.
(An intermediate `relaxed` LP mode was implemented and then removed — its optimum was
identical to constant efficiency, so it added no realism.) These are **done**; the items
below are not.

---

## Generator

- **Start-up cost + minimum up/down time (Stage 3, `integer` mode only).**
  Add `startup(t)`, `shutdown(t)` helper variables tied to the online count by the
  state equation `n(t) = n(t-1) + startup(t) - shutdown(t)`; charge `Σ c_su·startup(t)`
  in the objective; add rolling-window min up/down constraints. Needs only one integer
  per timestep (Palmintier §III). Moderately invasive: it introduces *temporal
  coupling* into the generator block for the first time (and year-boundary handling in
  multi-year, mirroring the battery SOC year-links). **Split it:** start-up cost alone
  is the cheap, high-value part; min up/down time is a heavier, separate sub-step and
  matters more for operational scheduling than for sizing. Best in typical-year or with
  representative periods.

- **Multi-segment Willans line (2–3 pieces).** Fit the on-range fuel curve with a few
  convex secants instead of one affine line, to capture efficiency curvature across the
  operating band. No new integers (the commitment variable already handles the
  origin/on-off).

- **Perspective cuts** (Frangioni & Gentile) to tighten the LP relaxation of the integer
  commitment inside branch-and-cut, so the MILP solves faster at large multi-year scale.

## Battery — realism upgrades

- **Temperature-dependent performance.** Highest value / lowest risk. Because capacity,
  loss-curve coefficients and the flat calendar-fade rate are exogenous inputs,
  period-indexed temperature multipliers can scale them with **zero loss of
  linearity**. Matches the existing `battery.md` "future extensions" note and the
  SSA-relevant high-ambient case.

- **DOD / cycle-depth-aware cycle fade.** The current cycle fade is `γ·throughput`,
  which is depth-blind (one deep cycle ≈ several shallow ones). Upgrade path:
  cheap **weighted-throughput (wAh)** SOC/DOD weighting (stays linear) → state-of-art
  **piecewise-linear DOD-dependent cycle-aging cost** (Xu et al. 2018, IEEE TPWRS) or
  the **convex rainflow reformulation** (Shi et al. 2018, ACC).

- **Efficiency ageing.** Today degradation reduces *capacity* only; round-trip
  efficiency is static. Optional: scale the loss-curve slopes with accumulated
  throughput/age via exogenous yearly multipliers (stays linear).

- **Endogenous SoH state + degradation-triggered replacement.** Replacement timing is
  currently exogenous (lifetime/cohort masks). Link an explicit SoH state to a
  replacement decision at an end-of-life threshold (cf. Petrelli et al. 2021); usually
  needs iteration.

- **Battery salvage / residual value** at the horizon (flagged WIP in the code).

## Battery — consistency fixes (not new features)

- **[SUPERSEDED — removed] SOC-dependent calendar-fade curve.** The average-SOC calendar-fade
  surrogate (`battery_average_soc`/`battery_calendar_fade` vars, the `battery_calendar_fade_curve.csv`
  input, and `calendar_time_increment_per_year`) was removed to simplify the degradation surface.
  Its effect on the *sizing* decision is third-order, and the shipped default curve was calibrated
  ~20-50x too low to matter. Calendar ageing is now a single **flat %/yr** rate
  (`capacity_degradation_rate_per_year`, 0 = off), applied as the exogenous annual degradation
  factor and coexisting with cycle fade. This also retired the earlier scenario-convention fix
  below (there is no longer a calendar-fade variable to unify).
- **[PENDING — Stage 3] Power vs energy derating:** the code bounds charge/discharge **power by
  the inverter** only. `battery.md` was corrected to say so; the optional SoH-coupled power
  derating (bound DC power by `c_rate * eff_cap`, default off) is not yet implemented.
- **[DONE — Stage 1/2] `eff_cap` reporting truthfulness:** the effective-capacity year-link is an
  inequality nudged tight only by a `1e-9` regularizer, and it *can* stay slack-low in degenerate
  corners (confirmed by tests). Reporting now reconstructs the physical effective capacity from
  the initial SoH and the reliable cycle-fade solution, so the reported SoH no longer
  depends on the raw LP state.
- **[DONE — Stage 1] Doc/code drift:** `battery.md` now describes the loss reference power as the
  explicit inverter design variable + C-rate (was `C_bat/t_ch`).
- **[DONE — Stage 1] `/SoH0` factor** in the cycle-fade coefficient: documented (fade measured
  against beginning-of-life usable capacity; only matters when `initial_soh < 1`).

- **Last-period terminal free-discharge (model gap, surfaced by the 2-period degradation toy):**
  the multi-year battery has no cyclic/terminal SOC closure, so in the **final period of the last
  modeled year** it can discharge without SOC backing — the SOC-balance recursion links period
  `t` to `t+1`, and there is no `t+1` after the horizon end. Harmless at realistic 8760-h
  horizons (the effect is a single trailing hour out of thousands, and the battery is normally
  cycled continuously), but it lets a tiny toy extract "free" terminal energy and can leave the
  last-year effective-capacity state slack (which is why the reporting recomputation above
  matters). Fix, if ever needed: add an optional terminal-SOC condition (e.g. `SOC_end >=
  SOC_0 * C_eff`, or a soft penalty on net end-of-horizon depletion) so the last period cannot
  draw down un-backed energy.

## Cross-cutting

- **Representative-period / typical-day clustering** to keep integer commitment (and any
  future cycle-counting battery degradation) tractable in the multi-year formulation.

---

*References mentioned:* Palmintier & Webster 2012 (clustered UC); Xu et al. 2018 and
Shi et al. 2018 (battery cycle aging); Frangioni & Gentile 2006 (perspective cuts);
Petrelli et al. 2021 (SoH-triggered replacement).
