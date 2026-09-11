# Battery Degradation in MicroGridsPy — Implementation Report

**Scope.** This report documents, precisely and against the current source, how the battery
capacity-degradation effect is represented in the MicroGridsPy **multi-year (`dynamic`)**
optimization, including the offline coefficient layer, the decision variables, and the main
constraints. It covers both cycle-fade representations available today:

- `single_beta` — a flat-in-depth, temperature/DoD-aware throughput coefficient `β(T)` (the
  existing default), and
- `marginal_bands` — a depth-resolved, convex per-SOC-band marginal cost `cₖ(T)` (new;
  emergent depth-of-discharge, binary-free).

A short note on the typical-year (`steady_state`) treatment is given in §8. The report ends
(§9) with a controlled comparison run of the two modes.

Source files: `data_pipeline/battery_degradation_coefficients.py`,
`data_pipeline/battery_degradation_model.py`, `data_pipeline/battery_loss_model.py`,
`multi_year_model/{data,variables,constraints,objective,lifecycle}.py`.

---

## 1. Architecture

All nonlinearity/temperature physics lives **offline** and is distilled to exogenous
coefficient arrays; the **online** MILP is then linear (LP unless integer sizing/commitment is
enabled elsewhere).

```
OFFLINE (per chemistry, from ambient temperature)     ONLINE (multi-year MILP)
  α(T, SoC-band)  calendar rate                 ─────►  effective-capacity state Cᵉᶠᶠ(y)
  β(T, DoD-band)  single cycle coefficient       ─────►  annual cycle fade F_cyc(y)
  cₖ(T)           per-SOC-band cycle marginals   ─────►  binding-life replacement cost Z(y)
  convex loss curve (charge/discharge epigraph)  ─────►  DC/AC power split
```

The economic cost of degradation is **not** a separate wear charge; it is carried by a
max-of-annuities *epigraph* that amortizes the battery-energy CapEx over the **binding**
(calendar vs cycle-limited) life (§7), keeping degradation inside the annuity / no-salvage
cash-flow convention.

---

## 2. Inputs and parameters

| Input | Location | Meaning |
|---|---|---|
| `core_formulation: dynamic` | `formulation.json` | selects the multi-year model |
| `battery_model.loss_model` | `formulation.json` | `constant_efficiency` or `convex_loss_epigraph`; degradation **requires** `convex_loss_epigraph` |
| `battery_model.degradation_model.cycle_fade_enabled` | `formulation.json` | master switch for the endogenous cycle-fade state |
| `battery_model.degradation_model.cycle_fade_mode` | `formulation.json` | `single_beta` (default) or `marginal_bands` |
| `battery_model.degradation_model.n_soc_bands` | `formulation.json` | K depth bands (default 5), `marginal_bands` only |
| `battery_model.degradation_model.initial_soh` (`SoH₀`) | `formulation.json` / `battery.yaml` | beginning-of-life state of health ∈ (0, 1] |
| `battery_model.degradation_model.end_of_life_soh` (`SoH_eol`) | " | end-of-life threshold ∈ (0, SoH₀] |
| `battery.technical.chemistry` | `battery.yaml` | `LFP` \| `NMC` \| `lead_acid` (selects coefficient set) |
| `battery.technical.depth_of_discharge` (`DoD`) | `battery.yaml` | usable SOC window fraction; selects the β DoD-band and the α SoC-band |
| `battery.technical.cycle_lifetime_to_eol_cycles` (`N_user`) | `battery.yaml` | rated cycle life; scales β and cₖ by `N_ref / N_user` |
| `battery.technical.battery_calendar_lifetime_years` (`L_cal`) | `battery.yaml` | calendar life; sets the cohort replacement period and the calendar annuity |
| `battery.technical.max_(charge/discharge)_c_rate` | `battery.yaml` | C-rate power limits |
| `ambient_temperature.csv` | project inputs | hourly ambient temperature `T(period, year, scenario)` [°C]; **required** when cycle fade is on |
| `battery_efficiency_curve.csv` | project inputs | efficiency curve → convex loss epigraph breakpoints |

Resolution/validation happens in `get_battery_degradation_settings(...)`
(`battery_degradation_model.py`): it enforces `loss_model = convex_loss_epigraph`, the SoH
span, a positive rated cycle life, and the `cycle_fade_mode` / `n_soc_bands` values.

---

## 3. Offline coefficient layer

Coefficients are evaluated in the data loader (`multi_year_model/data.py`) from
`ambient_temperature.csv` and the battery chemistry, and attached to the model dataset.

### 3.1 Calendar coefficient `α(T, SoC-band)` → year rate `r_cal,y`
Cubic in `y = T[°C]/10`, per chemistry and SoC band (the SoC band is mapped from the fixed
`DoD`: Li-ion `DoD ≥ 0.75 → 20 %` band, else `40 %`; lead-acid single band):

```
α_hour(T) = c₁ y³ + c₂ y² + c₃ y + c₄          (clipped ≥ 0)
r_cal,y   = α_hour(T̄_y) · 8760                 T̄_y = annual mean ambient (over period, scenario)
```

`r_cal,y` is a **year-varying, exogenous** calendar rate (static within a solve). Data var:
`battery_calendar_rate_per_year (year)`.

### 3.2 Single cycle coefficient `β(T, DoD-band)` (`single_beta`)
Cubic in `y = T/10` (Li-ion; lead-acid uses a DoD-argument cubic), selected by the fixed DoD
band and scaled by the cycle-life ratio:

```
β_hour(T) = ( d₁ y³ + d₂ y² + d₃ y + d₄ ) · (N_ref / N_user)      (clipped ≥ 0)
```

Data var: `battery_beta_cycle (period, year, scenario)`. Interpretation: fraction of nameplate
energy lost per unit of DC energy exchanged.

### 3.3 Depth-resolved marginals `cₖ(T)` (`marginal_bands`)
Produced by `evaluate_band_marginals(...)` from the shipped Layer-I physical-model coefficients
(`data_pipeline/layer1_liion_coefficients.json`, generated by
`notebooks/battery_layer1_liion_physical_model.ipynb`): the depth curve `Ψ(D,T)` is
reconstructed on a fine grid and re-binned into `K` **usable** bands over `[0, DoD]`, then
scaled by `N_ref / N_user`:

```
cₖ(T) = [ Ψ(dₖ, T) − Ψ(d_{k−1}, T) ] / (dₖ − d_{k−1}) · (N_ref / N_user)
```

`cₖ` is the marginal capacity loss per unit of discharge depth-fraction; the shape is convex
(`c₁ ≤ … ≤ c_K`), enforced offline by a pool-adjacent-violators guard. Data var:
`battery_ck_bands (soc_band, period, year, scenario)`. Li-ion only. Band `0` is the shallowest
(top-of-SOC) slice.

---

## 4. Decision variables (multi-year)

Battery variables are indexed over `(period, year, scenario, inv_step)` unless noted;
`inv_step` is the investment cohort dimension.

| Variable | Dims | Role |
|---|---|---|
| `battery_units` | `(inv_step)` | installed energy capacity [kWh], first-stage |
| `battery_inverter_power` | `(inv_step)` | installed converter power [kW], first-stage |
| `battery_charge`, `battery_discharge` | `(period,year,scenario,inv_step)` | AC-side charge/discharge [kWh] |
| `battery_soc` | " | state of charge (energy) [kWh] |
| `battery_charge_dc`, `battery_discharge_dc` | " | DC-side charge/discharge (loss model) [kWh] |
| `battery_charge_loss`, `battery_discharge_loss` | " | converter losses [kWh] |
| `battery_cycle_fade` | `(year,scenario,inv_step)` | **annual** cycle capacity fade [kWh] |
| `battery_effective_energy_capacity` (`Cᵉᶠᶠ`) | `(year,scenario,inv_step)` | degraded usable capacity state [kWh] |
| `battery_replacement_cost` (`Z`) | `(year,scenario,inv_step)` | binding-life energy-CapEx annuity epigraph |
| **`marginal_bands` only:** | | |
| `battery_soc_band` | `(soc_band,period,year,scenario,inv_step)` | usable stored energy in band k [kWh] |
| `battery_discharge_band` | " | DC discharge routed through band k [kWh] |
| `battery_charge_band` | " | DC charge routed into band k [kWh] |

Investments (`battery_units`, `battery_inverter_power`) are first-stage; `Cᵉᶠᶠ`,
`battery_cycle_fade`, SOC and the band variables are per-scenario recourse.

---

## 5. Main constraints (multi-year, degradation active)

Let `Δt = 1 h`, `T` = number of periods per year, `bat_cap_available` = nominal installed
energy after the exogenous availability/calendar factor (§5.5).

### 5.1 Converter loss (convex epigraph) and AC/DC coupling
For each loss segment `j` with slope `sⱼ` and intercept `ιⱼ`, and reference power
`P_ref = bat_inv_active` (the active installed inverter power):

```
battery_charge_loss    ≥ s_j · charge_dc    + ι_j · P_ref        (battery_charge_loss_epigraph)
battery_discharge_loss ≥ s_j · discharge_dc + ι_j · P_ref        (battery_discharge_loss_epigraph)
charge    = charge_dc    + charge_loss                            (battery_charge_ac_dc_coupling)
discharge = discharge_dc − discharge_loss                         (battery_discharge_ac_dc_coupling)
charge_dc ≤ P_ref ,  discharge_dc ≤ P_ref                         (battery_(charge/discharge)_dc_limit)
```

The intercept `ιⱼ · P_ref` is the standby term that scales with installed inverter power
(the efficiency "hump"); no on/off binary is needed (grid-forming inverter always on).

### 5.2 SOC dynamics (DC-side) and window
```
soc[t] = soc[t−1] + charge_dc[t−1] − discharge_dc[t−1]           (soc_balance, within year)
soc[first year, period 0] = SoC₀ · Cᵉᶠᶠ[first year]              (soc_initial)
soc[year, period 0] = continued/reset SOC                        (soc_year_link_*)
(1 − DoD) · Cᵉᶠᶠ ≤ soc ≤ Cᵉᶠᶠ                                    (soc_lower / soc_upper)
```

### 5.3 Effective-capacity recursion (the degradation state)
```
Cᵉᶠᶠ ≤ bat_cap_available                                         (…_upper_available)
Cᵉᶠᶠ[first year] = SoH₀ · bat_cap_available[first year]          (…_initial)
Cᵉᶠᶠ[y] {≤ or ==} Cᵉᶠᶠ[y−1] − F_cyc[y−1]  (+ reset at commission)  (…_year_link_<y>)
```
The link is an **equality** when the exogenous calendar factor does not decline within the
cohort's life (state fully determined by the fade recursion), and a `≤` bound otherwise.
Commissioning years reset `Cᵉᶠᶠ` to `SoH₀ · bat_cap_available`.

### 5.4 Cycle-fade definition — the two modes  ⟵ *the degradation representation*

**`single_beta`** (constraint `battery_cycle_fade_definition`):
```
F_cyc[y,s,k] = Σ_period  β(T) · ( charge_dc + discharge_dc )
```
`β` multiplies the full summed DC throughput (both directions), matching its calibration of
`2·DoD` exchanged per full cycle. Flat in depth: every kWh of throughput is charged the same
wear regardless of how deep the cycle is.

**`marginal_bands`** — a stacked SOC-band reservoir, then a depth-weighted fade:
```
0 ≤ battery_soc_band ≤ (DoD / K) · Cᵉᶠᶠ                          (battery_band_soc_cap)
Σ_bands battery_discharge_band = discharge_dc                     (battery_band_discharge_balance)
Σ_bands battery_charge_band    = charge_dc                        (battery_band_charge_balance)
soc_band[t] = soc_band[t−1] + charge_band[t−1] − discharge_band[t−1]   (battery_band_soc_balance, within year)
Σ_bands soc_band[year, period 0] + (1−DoD)·Cᵉᶠᶠ = soc[year, period 0]  (battery_band_soc_link_<y>)
F_cyc[y,s,k] = Σ_period Σ_bands  cₖ(T) · discharge_band           (battery_cycle_fade_definition)
```
Because `cₖ` increases with depth (convex), the optimizer fills shallow (cheap) bands first,
so the **cycling depth is emergent** rather than assumed, and the block stays a pure LP (no
binaries). At full-depth cycling this reproduces the same per-cycle fade as `single_beta`.

### 5.5 Calendar availability factor
The year-rate `r_cal,y` (§3.1) enters the nominal capacity through the cohort availability
factor (`lifecycle.repeating_degradation_factor`):
```
bat_cap_available[y,k] = units_k · nominal · g[y,k] ,   g = Π_{j∈cohort life so far} (1 − r_cal,j)
```
(reduces to `(1 − r_cal)^(age−1)` for a constant rate). Calendar ageing is thus exogenous and
temperature-derived, feeding the ceiling on `Cᵉᶠᶠ` and the calendar annuity.

### 5.6 Power limits and nodal balance
```
charge_dc ≤ P_ref ,  discharge_dc ≤ P_ref                        (inverter power)
Σ_res gen + Σ_gen gen + (discharge − charge) + lost_load = load  (energy_balance)
```

---

## 6. Objective — where degradation is paid

NPC is discounted in-horizon annual cash-flows. Battery-energy CapEx is amortized over the
**binding life** via the epigraph `Z` (`battery_replacement_cost`):

```
Z ≥ bat_energy_annuity_cal                    (battery_replacement_cost_calendar)
Z ≥ (c_repl · φ) · F_cyc                       (battery_replacement_cost_cycle)
    c_repl = CapEx_kWh / (SoH₀ − SoH_eol)       [currency per kWh of fade]
    φ      = CRF(wacc, L_cal) · L_cal           [financing gross-up ≥ 1; = 1 when wacc = 0]
```
At the optimum `Z = CapEx amortized over min(calendar, cycle-limited) life`. `φ` is chosen so
the two bounds coincide exactly at the crossover (cycle life = calendar life), making the
switch continuous. `Z` is scenario-weighted into the cash-flow; the battery inverter CapEx
stays calendar-amortized. `Cᵉᶠᶠ` enters the objective only through a `−1e-9` reporting
tie-break (no explicit wear charge; no salvage term).

**Mechanism.** Deeper / harder cycling raises `F_cyc` → the cycle annuity in `Z` rises →
NPC rises, *only when* the cycle-limited life is shorter than the calendar life (otherwise the
calendar bound binds and `Z` — hence NPC — is insensitive to `F_cyc`).

---

## 7. Reporting note on SOH

The raw `Cᵉᶠᶠ` LP state is only weakly pinned (the `1e-9` tie-break), and can stay slack-low in
degenerate corners. Reported physical SoH is reconstructed separately from `SoH₀` and the
reliable cycle-fade solution, so the reported trajectory does not depend on the raw LP state.

## 8. Typical-year (`steady_state`) note

The single representative year has no inter-year `Cᵉᶠᶠ` state. Degradation is represented as a
**binding-life CapEx amortization**: a per-scenario max-of-annuities epigraph
`Z_s ≥ CRF(wacc,L_cal)·CapEx·C_bat` and `Z_s ≥ c_repl · φ · Σ_t β · (P_ch + P_dis)`, i.e. the
same economics as multi-year, without a capacity-state recursion. (Depth bands are a
multi-year feature.)

---

## 9. Results — `marginal_bands` vs `single_beta`

Controlled comparison on a reduced, tractable dynamic project derived from
`mbench_M5_batt_cycle_fade`: **1 modelled year**, 8760 h, 1 scenario, PV + battery + diesel,
**LFP** chemistry, ambient **35 °C**, `DoD = 0.8`, `SoH₀ = 1.0`, `SoH_eol = 0.8`, calendar life
10 yr, `n_soc_bands = 5`. Solver: HiGHS barrier (`solver=ipm, run_crossover=off,
ipm_optimality_tolerance=1e-6`). The 1-year horizon is sufficient because the binding-life
annuity is per-year. Two regimes are run, differing only in the rated cycle life:

- **Calendar-binding:** `N_user = 6000` (cycle-limited life ≈ 16 yr > 10 yr calendar).
- **Cycle-binding:** `N_user = 2500` (cycle-limited life < 10 yr calendar).

| Regime | Metric | `single_beta` | `marginal_bands` | Δ |
|---|---|---:|---:|---:|
| **Calendar binds** (N=6000) | NPC [$] | 79 865 | 79 865 | **+0.0 %** |
| | Battery [kWh] | 769.0 | 769.0 | 0 |
| | PV [kW] | 276.8 | 276.8 | 0 |
| | Diesel [kW] | 26.1 | 26.1 | 0 |
| | Annual cycle fade [kWh] | 11.22 | 10.34 | **−7.8 %** |
| **Cycling binds** (N=2500) | NPC [$] | 98 484 | **94 934** | **−3.6 %** |
| | Battery [kWh] | 788.0 | 790.3 | +0.3 % |
| | PV [kW] | 230.4 | 237.2 | +3.0 % |
| | Diesel [kW] | 34.2 | 33.2 | −2.9 % |
| | Annual cycle fade [kWh] | 24.01 | 22.59 | **−5.9 %** |

### Interpretation
- **When the calendar life binds** (gently/moderately cycled), depth-resolution *refines the
  computed fade* (−7.8 %) but leaves NPC and the design unchanged — correct: cycling is not the
  life-limiting channel, so the cycle annuity in `Z` is dominated by the calendar bound.
- **When cycling binds**, the fixed-DoD `single_beta` *overcharges* cycle wear (it prices all
  throughput at the `DoD = 0.8` band cost), which makes the battery look more expensive to cycle
  and pushes the design toward diesel. `marginal_bands` prices the *actual, shallower* realized
  cycling → cycling the battery is cheaper → the design shifts toward **more PV + battery, less
  diesel, and a 3.6 % lower NPC**. The NPC gap (~3 550) is far above the solver tolerance
  (~1e-6 relative), so it is a genuine design change, not numerical noise.

**Take-away.** Depth-resolution removes the fixed-DoD bias of the single-β term and changes the
sizing / NPC decision exactly in the cycle-limited regime where it should, while correctly
leaving the calendar-limited regime unchanged.

### Caveats
- The full 8760 × multi-year degradation LP with convex loss is ill-conditioned; the run above
  uses a 1-year horizon and the barrier solver with crossover off for tractability. Full-horizon
  runs need representative-period clustering.
- `Cᵉᶠᶠ` does not decline within a single modelled year, so the economic signals (NPC, `F_cyc`,
  technology mix) — not an end-of-life SoH trajectory — are the meaningful comparison here.
- `marginal_bands` is Li-ion only; lead-acid depth banding requires the Schiffer model.

*Runs: projects `banddemo_{beta,bands}` (N=6000) and `banddemo_{beta,bands}_cyc` (N=2500).*
