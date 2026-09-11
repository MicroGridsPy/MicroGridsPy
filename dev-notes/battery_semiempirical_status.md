# Semi-empirical battery cycle-fade — implementation status & equations

**Internal note.** Records the state after the P1 transplant: the temperature- and
DoD-aware semi-empirical cycle coefficient `β(T)` (and calendar `α(T)`) is now the
degradation coefficient source in both formulations. Companion to
`dev-notes/battery_semiempirical_assessment.md`. Model provenance/credits live in the
published documentation; the package code is kept generic.

## 0. Coefficient source (shared)

`data_pipeline/battery_degradation_coefficients.py` is the single source. Given
`chemistry ∈ {LFP, NMC, lead_acid}`, `depth_of_discharge`, an ambient-temperature
series, and the rated cycle life, it evaluates per-timestep

```
α_hour = c1·y³ + c2·y² + c3·y + c4            (calendar, per-hour fraction of nameplate)
β_hour = ( d1·y³ + d2·y² + d3·y + d4 ) · (N_ref / N_user)     (cycle, per kWh exchanged)
y = T_env[°C] / 10           (lead-acid β uses z = DoD·10 − 2, temperature-flat)
```

The cubics are a fixed *shape* per chemistry and stress band (SoC band for α from the
DoD; DoD band for β); the user scales β through the rated cycle life `N_user`
(`battery.technical.cycle_lifetime_to_eol_cycles`). All exogenous ⇒ the optimisation
stays linear. Input `ambient_temperature.csv` mirrors `load_demand.csv` (scenario/year
header, °C, default 25 °C).

## 1. Typical-year (steady_state) — binding-life CAPEX amortisation, no state ✅

No capacity state, no convex-loss requirement. `β(T)` is loaded per `(period, scenario)`,
and the battery **energy** CAPEX is amortised over the binding (calendar vs cycle) life via
a per-scenario max-of-annuities epigraph — the same treatment as multi-year, so the two are
economically consistent and there is no double count with the calendar annuity:

```
Z_s ≥ CRF(wacc, L_cal) · CAPEX · C_bat                          [calendar annuity]
Z_s ≥ c_repl · φ · Σ_t β_{t,s} · (P^ch_{t,s} + P^dis_{t,s})      [cycle annuity]
c_repl = CAPEX/(SoH₀−SoH_eol),   φ = CRF(wacc, L_cal)·L_cal
minimise  annualized_investment(without battery energy CAPEX) + Σ_s w_s Z_s + …
```

- At the optimum `Z_s = max(·,·) = CAPEX / min(calendar, cycle-limited) life`. Gently cycled →
  calendar binds → flat; hard cycled → cycle binds → cost rises. `P^ch,P^dis` are AC-side.
- The battery **inverter** CAPEX stays calendar-amortised. The `cycle_fade_mode` setting is
  `"binding_life_annuity"`.
- Wiring: `typical_year_parsing._load_ambient_temperature_csv` + degradation keys;
  `typical_year_loader` attaches `battery_beta_cycle`; `typical_year_model.variables` adds the
  `battery_replacement_cost` epigraph var; `typical_year_model.objective` moves the battery
  energy annuity into the epigraph. (Replaces the earlier standalone throughput wear cost,
  which double-counted the calendar annuity.)

## 2. Multi-year (dynamic) — endogenous capacity-fade recursion ✅

The flat `γ` cycle term is replaced by `β(T)`; the calendar channel is driven by `α(T)`.
Requires `loss_model = convex_loss_epigraph` (throughput on internal DC powers).

**Cycle fade** — `β(T)` is the single source (the flat `γ` was removed). To avoid one
fade variable per hour, `F^cyc` is aggregated to an **annual** variable per cohort (P2
"inline"): one defining constraint per year instead of per hour (kills the 8760×Y×S×K
per-period fade constraints):

```
F^cyc_{y,s,k} = Σ_t β_{t,y,s} · ( P^ch,dc_{t,y,s,k} + P^dis,dc_{t,y,s,k} )
```

(`β` multiplies the full summed throughput — both directions — matching its calibration
of `2·DoD` exchanged per full cycle.)

**Calendar fade (P1-cal)** — `α(T)` supplies a **year-varying** exogenous rate (static
within the solve, faithful to the decomposition), replacing the flat user `%/yr`:

```
r_cal,y = α_hour(T̄_y) · 8760            [T̄_y = annual mean ambient temperature, over hours+scenarios]
g_{y,k} = Π_{j=commission}^{y-1} (1 − r_cal,j)     [availability factor; = (1−r_cal)^(age−1) for constant T]
C̄^bat_{y,k} = C_nom_k · g_{y,k}
```

`repeating_degradation_factor` now accepts a year-indexed rate and forms the cumulative
product over the years a cohort has lived (resets at each replacement).

**Effective-capacity state** (yearly, per scenario and cohort):

```
C^eff_{y,s,k} ≤ C̄^bat_{y,k}
C^eff_{y₀,s,k} = SoH₀ · C̄^bat_{y₀,k}
C^eff_{y,s,k}  {≤ or ==}  C^eff_{y−1,s,k} − F^cyc_{y−1,s,k}   [+ reset to SoH₀·C̄^bat at commission]
(1 − DoD)·C^eff_{y,s,k} ≤ SOC ≤ C^eff_{y,s,k}
```

- **P2 equality link**: when the availability ceiling does not decline (`r_cal == 0`), the
  year-link is an exact **equality** (state fully determined, no degeneracy). When
  `r_cal > 0` it stays `≤` (min of continuation and the declining ceiling).
- **P2 economics — CAPEX amortized over the binding (endogenous) life.** Rather than a
  separate wear charge (which double-counted the calendar annuity — see §6), the battery
  *energy* CAPEX is recovered through a max-of-annuities **epigraph** that stays inside the
  existing annuity / pay-as-you-go / no-salvage convention:
  ```
  Z_{y,s,k} ≥ calendar annuity  = units_k·nom·CAPEX_k·CRF(wacc_k, calendar_life_k)   [availability-masked]
  Z_{y,s,k} ≥ cycle annuity     = c_repl_k · φ_k · F^cyc_{y,s,k}
  c_repl_k = CAPEX_k /(SoH₀−SoH_eol) ,   φ_k = CRF(wacc_k, calendar_life_k)·calendar_life_k
  minimize Σ_y disc_y · Σ_s w_s · Σ_k Z_{y,s,k}
  ```
  At the optimum `Z = CAPEX / min(calendar, cycle-limited life)` — i.e. amortization over
  the effective (economic = technical) lifetime. `φ` is the financing gross-up chosen so
  the two bounds coincide exactly at the crossover (cycle life = calendar life), making the
  switch continuous; `φ=1` when `wacc=0`. The battery *inverter* CAPEX stays calendar-only.
  The `1e-9` credit is kept purely as a reporting tie-break for the `C_eff` LP state.
- `β`/`α` are exogenous coefficient fields ⇒ the block stays linear. Investments are
  first-stage; `C^eff`, `F^cyc`, SOC are per-scenario recourse; cohort/annuity untouched.
- Verified end-to-end: `Σ F^cyc == Σ β·(ch+dis)` at the optimum (β is consumed, not γ).

## 3. Status matrix

| Piece | Typical-year | Multi-year |
|---|---|---|
| ambient_temperature.csv input | ✅ (period×scenario) | ✅ (period×year×scenario) |
| chemistry / DoD-band / cycle-life scaling | ✅ | ✅ |
| cycle term `β(T)` | ✅ binding-life annuity | ✅ recursion + binding-life annuity |
| calendar term `α(T)` | ⛔ (time-based; a single-year cost overlaps CAPEX — left out) | ✅ drives exogenous rate |
| SoH capacity state / feedback | ⛔ by design | ✅ (SOC window) |
| power derating with SoH | ⛔ | ⛔ (still inverter-bound) |
| endogenous SoH-triggered replacement | ⛔ | ⛔ (calendar-lifetime cohorts) |
| convex-loss required | no | yes |

## 4. Dead-code cleanup (done)
- **Legacy `γ` cycle-fade path fully removed** (single source is now `β(T)`):
  `derive_cycle_fade_coefficient_from_cycle_life`, the `data.py` derivation block,
  `cycle_fade_input_mode`/`direct_coefficient`, the `battery_cycle_fade_coefficient_per_kwh_throughput`
  param (multi- and typical-year) and its typical-parsing override, and
  `require_cycle_fade_coefficient`. The constraint now **requires** `battery_beta_cycle`.
- Removed the unused `curve_point` Params field (multi-year).
- The removed SOC-calendar-fade curve / average-SoC / calendar-time-increment feature
  left no residue (confirmed by grep).
- The 3 unit tests of the deleted `derive_*` helper were removed; in-memory degradation
  tests now inject `battery_beta_cycle` instead of `γ`.

## 5. Residual items / future work
- The wear-cost/annuity **double-count is resolved** by the max-of-annuities epigraph (§2,
  §6) — CAPEX is amortized over the binding (endogenous) life, staying inside the
  annuity/no-salvage convention. No separate wear charge.
- The per-year `max` is a first-order proxy for "replace when cumulative SoH hits EOL";
  discrete SoH-triggered replacement (P4) is the exact version but would reintroduce lumpy
  CAPEX + a salvage term + integers, so it is deliberately *not* pursued here.
- The `φ` financing gross-up on the cycle term uses the calendar-life CRF (exact at the
  crossover, approximate away from it) — a documented second-order simplification.
- Calendar life is a fixed input; temperature accelerates cycle fade (`β`) and in-life
  capacity droop (`α`) but does not (yet) shorten the calendar amortization life itself.
- Power-fade (`R_int`) and SoH-power derating remain future work.
- Solve performance: the full-chronology convex-loss + degradation LP is degenerate;
  use the **barrier** solver (§6). Representative-day clustering is the structural fix.

## 6. Multi-year assessment — how results change, and why

Sweep on a synthetic off-grid mini-grid (3 modelled years, evening-peak load, midday PV,
PV + battery only, no lost load; battery CAPEX 350/kWh over a 10-yr calendar life; HiGHS
barrier `ipm`). "old" = the earlier standalone wear cost; **"new" = the max-of-annuities
epigraph** (CAPEX amortized over the binding life):

| config | binding limit | NPC old | **NPC new** | Δ vs no-degr (25 222) | battery kWh | PV kW |
|---|---|---|---|---|---|---|
| no degradation | — | 25 222 | **25 222** | — | 153.5 | 24.9 |
| LFP 25 °C, N6000 | calendar | 35 006 | **25 481** | **+1.0 %** | 155.0 | 25.2 |
| LFP 40 °C, N6000 | calendar | 38 818 | **25 481** | **+1.0 %** | 155.0 | 25.2 |
| LFP 40 °C, N3000 | cycle | 51 919 | **42 120** | **+67 %** | 284.0 | 26.6 |
| NMC 40 °C, N3000 | cycle | 35 062 (46 815) | **35 062** | **+39 %** | 229.1 | 26.2 |

**The behaviour is now economically consistent:**
- **Gently cycled (N6000 → cycle life ≈16 yr > 10-yr calendar, calendar binds).** NPC is
  **flat at +1.0 %** (was +39–54 %); the residual is just the convex-loss efficiency
  difference vs the constant-efficiency baseline, not a phantom replacement charge. The
  battery sits at the baseline size (155 vs 153.5 kWh) — the earlier PV over-sizing
  (≈30 kW) the wear cost induced is gone. Temperature barely matters here over 3 yr,
  because calendar fade is tiny (`r_cal`≈0.05–0.09 %/yr) and cycle life does not bind — as
  it should be.
- **Cycle-stressed (N3000 → cycle life ≈9 yr ≈ the 10-yr calendar crossover, cycle binds).**
  NPC rises (**+67 % LFP, +39 % NMC**), and the model responds the way a real operator
  would: it **oversizes the battery** (155 → 284 kWh LFP, 229 kWh NMC) so each unit is
  cycled less deeply/often, pushing the cycle-limited life back up toward the calendar
  limit. That is the epigraph working as intended — it makes cycling that actually
  shortens the battery's life expensive, and lets the optimiser trade "buy more battery" vs
  "replace it sooner."
- **Chemistry**: NMC (lower fitted `β`/`α` here) needs less oversizing than LFP at the same
  harsh setting → cheaper (+39 % vs +67 %).

So NPC **stays flat when cycling doesn't shorten life, and rises only when it does** —
exactly the requested criterion, with no double count.

*Caveat on the table:* `battery.py` reports the **physical** SoH via a separate
reconstruction; the raw LP effective-capacity state is only weakly pinned (1e-9 tie-break)
and is not a reliable SoH readout, so per-config end SoH is omitted here.

**Remaining item — solve performance.** The full-chronology convex-loss + degradation LP is
highly degenerate: default HiGHS **simplex** crawled (>550 s and climbing at 8760×3); the
**barrier** solver (`ipm`, crossover off) returns the optimum in ~350–560 s. Recommend
defaulting large multi-year degradation runs to barrier (Gurobi already auto-selects it),
and representative-day clustering as the structural fix for 8760×Y scaling.

## 7. Tests
- `tests/test_battery_degradation_coefficients.py` — coefficient shapes, EOL calibration,
  ambient loader, end-to-end multi-year load, and the **multi-year β transplant solve**
  (`Σ F^cyc == Σ β·(ch+dis)`).
- `tests/test_typical_year_degradation.py` — the epigraph identity `Z = max(calendar, cycle)`
  annuity (flat when the calendar binds), and monotonicity (a shorter rated cycle life is never cheaper).
- `tests/test_battery_degradation.py` — the effective-capacity recursion mechanics
  (scenario-wise fade, replacement reset, reporting truthfulness), now on `β`.
