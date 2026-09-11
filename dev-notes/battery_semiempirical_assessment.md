# Battery semi-empirical degradation — assessment & intervention plan

**Internal note.** Benchmarks the *current* MicroGridsPy battery-degradation implementation against
(i) the Shamarova et al. review taxonomy, (ii) the **Andrade decomposition** ("Coefficients model",
MSc dissertation 2023), and (iii) the old partially-implemented `…-Development_Batteries` prototype.
Goal: a *working* semi-empirical battery model that follows Andrade as closely as practical, with the
changes differentiated for the **typical-year (steady_state)** and **multi-year (dynamic)** formulations,
and consistent with the current annuity / multi-investment-step / stochastic-recourse machinery.

> One-line verdict (from the review, confirmed against the code): **MicroGridsPy has the better skeleton
> and the weaker muscles.** It already has the harder half — a yearly effective-capacity state, cohorts,
> DC-side flows, degradation *inside* the optimisation — but its cycle term is a flat, temperature- and
> depth-blind `γ·throughput`, and its calendar term is a flat exogenous %/yr. The single highest-leverage
> fix is a **coefficient transplant**: put Andrade's `β(T, DoD-band)` into the existing endogenous cycle
> slot and drive the calendar rate from `α(T)`, both as exogenous inputs (LP-safe), then harden the solve.

---

## 1. Reference frame (Shamarova et al.)

Four lifetime-model families, ordered by physical detail: electrochemical (PDEs) → equivalent-circuit
(ECM) → **semi-empirical (SEM)** → data-driven, plus event-oriented (rainflow). For a sizing MILP only
**SEM (linearised)** is the pragmatic default. The two **dominant** stress factors are **DoD** and
**temperature**; SoC (calendar) and C-rate are secondary. The review's standing criticism: sizing tools
either assume zero degradation cost, collapse life to a linear DoD function, or freeze temperature.

The decisive property for an optimiser is **endogenous vs exogenous**: the solver can only trade operation
against ageing for a term that appears in a constraint/objective as a function of a *decision*
(throughput, SoC, DoD). An exogenous `%/yr` term is solver-invisible.

---

## 2. Andrade decomposition — the target formulation (equations retrieved)

Andrade builds a nonlinear **Battery Degradation model** (ECM + thermal + SEM, offline reference
generator) and collapses it into a linear **Coefficients model** usable inside the MILP.

### 2.1 Offline reference laws (Li-ion, used only to *generate* the coefficients)

Calendar (eq 3.20) and cycle (eq 3.21) capacity-loss (%) per step:

```
C_loss,cal(%) = a1·exp(a2·SOC) · a3·exp(a4/T_b) · (t/24)^a5
C_loss,cyc(%) = b1·exp( b2·(T_b−b3)/T_b + b4·DOD + C_rate·(b5+b6) ) · [1 + b7·mSOC·(1 − mSOC/(2·b8))]
C(t) = C(t−1) − C_loss(t)·C_max/100      SOH = C/C_max
```

| Fitting params | a1 | a2 | a3 | a4 | a5 |     | b1 | b2 | b3 | b4 | b5 | b6 | b7 | b8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **LFP** | 0.00157 | 1.317 | 142300 | −3492 | 0.48 | | 0.003414 | 5.8755 | 293 | −0.0046 | 0.296 | 0.1038 | 0.0513 | 0.42 |
| **NMC** | 0.03304 | 0.5036 | 385.3 | −2708 | 0.51 | | 0.001673 | 21.6745 | 293 | 0.022 | 0.2553 | 0.1571 | −0.0212 | 0.42 |

Lead-acid uses a charge-throughput *lifetime-estimation* model (no capacity update):
`AhT_lifetime = C_max·DOD·N_cycles·2`, EOL when cumulative Ah hits it. `R_int` grown a flat 10 %/yr
(power fade — **dropped** in the linear model).

### 2.2 The linear recursion (the object to import) — eq 3.33

```
E_t^DB = E_{t−1}^DB − α·E^B − β·P_t^BE
```

- `E^B` = nameplate energy, `P_t^BE` = hourly power/energy exchange, `α` = calendar coeff (always on),
  `β` = cycle coeff (only when power flows).
- Coefficients recovered by rearranging 3.33 against 20-yr runs of the full model (eqs 3.34–3.38):
  `α_year = −ΔE/E^B`, `α_hour = α_year,avg/8760`; `β_year = −(ΔE + α_hour·8760·E^B)/P^BE`, `β_hour = β_year,avg`.
- **Crucially, α and β are static within a solve** — they are cubic polynomials in temperature, selected
  offline per SoC-band, DoD-band and chemistry. This is the "fixed-point" the review notes: physical
  T/DoD fidelity at **linear** cost.

Temperature enters through `y = T_env/10`:

```
α_hour        = c1·y³ + c2·y² + c3·y + c4          (eq 3.36, params by SoC-band + chemistry)
β_hour,Li-ion = d1·y³ + d2·y² + d3·y + d4          (eq 3.39, params by DoD-band + chemistry)
β_hour,PbA    = d1·z³ + d2·z² + d3·z + d4 , z=(DOD−20)/10   (eq 3.40)
β_cycle-life  = β_model · (N_cyc,model / N_cyc,new)  (eqs 3.32/3.41 — cycle-life scaling ratio)
```

**α params (Table 3.14):**

| set | c1 | c2 | c3 | c4 |
|---|---|---|---|---|
| α 20%SoC LFP | 3.45e-10 | 1.24e-9 | 1.05e-8 | 1.97e-8 |
| α 20%SoC NMC | 8.32e-11 | 8.91e-10 | 6.71e-9 | 1.81e-8 |
| α 40%SoC LFP | 4.49e-10 | 1.61e-9 | 1.37e-8 | 2.56e-8 |
| α 40%SoC NMC | 9.21e-11 | 9.85e-10 | 7.42e-9 | 2.01e-8 |
| α 50%SoC PbA | — | — | — | 2.28e-6 (constant) |

**β params (Table 3.16):** DoD-band × chemistry (LFP/NMC at 50/60/70/80/90 %; PbA single set).

| set | d1 | d2 | d3 | d4 |
|---|---|---|---|---|
| β 50%DoD LFP | 9.09e-7 | −4.05e-6 | 1.33e-5 | 6.13e-6 |
| β 50%DoD NMC | 4.08e-6 | −1.35e-5 | 3.84e-5 | −7.52e-6 |
| β 60%DoD LFP | 8.53e-7 | −4.19e-6 | 1.32e-5 | 3.85e-6 |
| β 60%DoD NMC | 3.49e-6 | −1.15e-5 | 3.28e-5 | −6.21e-6 |
| β 70%DoD LFP | 7.55e-7 | −3.72e-6 | 1.17e-5 | 3.27e-6 |
| β 70%DoD NMC | 3.09e-6 | −1.01e-5 | 2.90e-5 | −5.25e-6 |
| β 80%DoD LFP | 6.34e-7 | −2.87e-6 | 9.19e-6 | 3.86e-6 |
| β 80%DoD NMC | 2.81e-6 | −9.06e-6 | 2.65e-5 | −4.42e-6 |
| β 90%DoD LFP | 6.07e-7 | −2.77e-6 | 8.70e-6 | 3.42e-6 |
| β 90%DoD NMC | 2.65e-6 | −8.42e-6 | 2.51e-5 | −3.73e-6 |
| β PbA (z) | −1.01e-7 | 1.53e-6 | −8.43e-6 | 2.81e-5 |

**DoD→α-band mapping** (β removes the calendar contribution using the average battery temperature):
Li-ion DoD∈[50,70]% uses the **40%SoC** α equation; DoD∈[80,90]% uses the **20%SoC** α; PbA uses its
single α everywhere.

Validation: the decomposition tracks the full model's SOH to ≈2 % over 20 yr (0.1–1.2 % LFP, up to 2 %
NMC). Turning ageing on moved NPC/LCOE by 5–20 % (~13.6 % avg) in the African case studies — the term
is economically material, not cosmetic.

### 2.3 The old prototype already coded these curves (recovered)

`…-Development_Batteries/Code/Initialize.py` (lines 206-253) builds `Alpha[t]`/`Beta[t]` **per hour** from
an hourly ambient series `T_amb` (`x = T_amb/10`), selecting the polynomial by `Battery_Type` (1=LFP,
2=NMC, 3=PbA) and `Battery_DoD`, and multiplying β by `cycle_coefficient = N_model/Battery_Cycles`
(`6400/…` LFP, `5000/…` NMC, `3000/…` PbA). The recursion (`Constraints.py`
`Battery_Bank_Degradation`) is `E_t = E_{t−1} − α·E_t − β·E_exch` per (scenario, year, hour), with an
**iterative (manual) SoH-triggered replacement** (`Battery_Iterative_Replacement`: run → read SOH series →
pick replacement year → re-run). This is the un-maintained, non-solving reference — but its coefficient
tables are exactly the dissertation's and are directly reusable.

> Note the prototype applied α to the *current state* `E_t` (implicit `E_t(1+α)=E_{t−1}−βP`), whereas
> eq 3.33 applies α to nameplate `E^B`. Use the **eq 3.33 form** (α·E^B) — it is linear and matches how
> MicroGridsPy already treats the exogenous rate (fraction of nominal).

---

## 3. Current MicroGridsPy implementation (as coded on this branch)

### 3.1 Multi-year (`core_formulation: dynamic`) — where degradation lives

`src/microgridspy/multi_year_model/{variables,constraints,objective,data}.py`,
`data_pipeline/battery_degradation_model.py`, `docs/methodology/battery.md`.

- **Cycle fade (endogenous, use-based)** — `constraints.py:529`:
  ```
  F_cyc[t,y,ω,k] = γ_cyc · (P_ch,dc + P_dis,dc)/2          # flat scalar γ, on DC-side throughput
  γ_cyc = (SoH0 − SoH_eol)/(N_cyc · DoD · SoH0)            # derived from rated cycle life
  ```
  Requires `loss_model = convex_loss_epigraph` (throughput is defined on the internal DC powers).
- **Effective capacity** — a **yearly state** `C_eff[y,ω,k]` (`battery_effective_energy_capacity`):
  ```
  C_eff ≤ C̄_bat(y,k)                                      # upper bound = exogenously-degraded nominal
  C_eff(y0) = SoH0 · C̄_bat(y0)                            # initial
  C_eff(y) ≤ C_eff(y−1) − Σ_t F_cyc(y−1)  [+ reset at commission years]   # INEQUALITY (≤), not ==
  ```
  It **feeds back** into operation: `SOC ≤ C_eff`, `SOC ≥ (1−DoD)·C_eff` (`constraints.py:589`).
- **Calendar fade (exogenous)** — a **flat %/yr** rate `r_cal` applied through the availability factor
  `g_{y,k}=(1−r_cal)^(age−1)` on the nominal capacity (`lifecycle.py:repeating_degradation_factor`).
  Solver-invisible. The earlier **SoC-linked calendar epigraph was removed** (`battery_calendar_fade_model.py`
  deleted in the working tree; `battery.md:185` confirms).
- **Objective coupling** — `objective.py:337`: `C_eff` enters the cost **only** as a `1e-9` tie-break
  credit (`−ε·ΣC_eff`), plus a `1e-6` no-simultaneous-charge/discharge regulariser. There is **no explicit
  degradation cost and no salvage** term; cycle fade bites the economics *only indirectly* by shrinking
  usable energy (→ needing more units / earlier binding of SOC limits).
- **Replacement / cohorts** — `inv_step` vintages; `replacement_active_mask` /
  `replacement_commission_mask` re-commission each cohort on a **fixed calendar lifetime**
  (`battery_calendar_lifetime_years`). At each commission year `C_eff` is force-reset to
  `SoH0·C̄_bat`. **Replacement is exogenous (calendar), not SoH-triggered.**
- **Power limits** — `P_ch,P_dis ≤ P_inv` (inverter), and `P_inv ≤ C_nominal·c_rate` uses **nominal**
  energy. So **power is not derated with SoH** (future_extensions "PENDING — Stage 3").
- **Stochastic recourse** — `scenario` dimension with weights; `enforcement ∈ {expected, scenario_wise}`.
  Investments (`battery_units`, `battery_inverter_power`) are **first-stage** (`inv_step` only); `C_eff`,
  `F_cyc`, SOC are **per-scenario recourse**. Annuity cash-flows are discounted in-horizon.

### 3.2 Typical-year (`core_formulation: steady_state`) — no degradation at all

`typical_year_model/variables.py:87` and `constraints.py:72` **raise** if `cycle_fade_enabled`. A single
representative year, no inter-year state, no `C_eff`. The exogenous flat %/yr can scale availability but
there is no multi-year propagation to make it meaningful. **Degradation is effectively out of scope here.**

### 3.3 Data pipeline — the blocking gap

**There is no ambient-temperature series anywhere in `src/microgridspy`** (grep for
`temperature|ambient|t_env`: zero hits outside generator/fuel). Andrade's α(T)/β(T) *cannot* be evaluated
until a temperature input exists. This is prerequisite work, not part of the LP change.

---

## 4. Benchmark / gap map

| Axis | Andrade decomposition | **MicroGridsPy today** | Gap |
|---|---|---|---|
| Family | linearised SEM | linearised SEM (partial) | same species |
| Cycle factors | **T(β), DoD-band**, throughput | flat `γ`·throughput (T- & depth-blind) | **P1 — biggest** |
| Calendar factors | **T(α)**, SoC-band | flat exogenous %/yr (T-blind, solver-invisible) | **P1-cal** |
| Endogenous cycle? | yes (fixed-pt) | yes, but weakly determined (`≤` + 1e-9) | **P2 — harden** |
| Depth resolution | banded β (still band-blind inside) | none beyond band | P3 |
| Power/`R_int` fade | dropped | dropped (+ power not SoH-derated) | minor |
| Replacement | iterative SoH (manual) | exogenous calendar cohort | P4 |
| Temperature input | hourly series (had it) | **absent** | **prerequisite** |
| Multi-step / annuities / scenarios | single-invest, iterative | **cohorts + annuities + recourse** ✅ | MGPy ahead |

MicroGridsPy is *ahead* on structure (cohorts, annuities, stochastic recourse, DC-side flows, endogenous
slot) and *behind* on coefficient physics (T, DoD). Close the cycle column first.

---

## 5. Interventions (ranked, with equation changes)

### Prerequisite — temperature input (both formulations)
Add an ambient-temperature timeseries to the data pipeline (period-indexed, and **per modeled year** in
multi-year so climate/warming can differ by year). Source it the way generation already is (NASA POWER /
user CSV). Expose `battery.technical.chemistry ∈ {LFP, NMC, lead_acid}`, `battery.depth_of_discharge`
(already present → gives the DoD band), and a `degradation_model.coefficient_source ∈ {cycle_life, andrade}`
switch. No LP change yet; this only makes α/β evaluable.

### P1 — Temperature- & depth-aware cycle term (the coefficient transplant)  ⟵ highest impact/effort
Replace the flat scalar `γ_cyc` with the **exogenous** Andrade `β`, evaluated offline per period/year from
temperature, the (fixed) DoD band and chemistry, times the cycle-life scaling ratio:

```
F_cyc[t,y,ω,k] = β_{y}(T_{t,y}, DoD-band, chem) · P^BE_{t,y,ω,k}
β_{y} = ( d1·y³ + d2·y² + d3·y + d4 ) · (N_cyc,model / N_cyc,user) ,   y = T_env/10
```
- **Stays fully linear**: `β_{y}` is a *coefficient array* (period×year), not a variable — DoD is a fixed
  input so the band is known up front; temperature is exogenous. This mirrors the existing `γ·throughput`
  slot exactly (`constraints.py:529`) — a coefficient swap plus a period/year index.
- **Convention reconciliation (do not skip):** the current slot uses `0.5·(P_ch,dc+P_dis,dc)`; Andrade
  regressed β against the hourly exchange `P^BE`. Match β's throughput definition to the code's (per unit
  of DC charge/discharge), or rescale β, so magnitudes agree. Cross-check by reproducing a 20-yr SOH
  trajectory against the offline law before trusting sizing runs.
- **Multi-year specifics:** `β_{y}` may vary by year (year-specific temperature); it multiplies the
  per-scenario throughput and accumulates into the **existing** `C_eff` year-link. Nothing in the cohort /
  annuity / recourse structure changes — `β` is a first-stage-invariant coefficient; `F_cyc` and `C_eff`
  stay per-scenario recourse.
- **Typical-year:** since there is no `C_eff` state, expose β only as a **throughput cost** in the
  objective (`Σ_t β·P^BE · unit_replacement_cost`) so the single-year dispatch still "feels" depth/temp
  wear without needing an inter-year state. (Lightweight; optional.)

### P1-calendar — Drive the calendar rate from α(T)
Keep calendar fade **exogenous and static-within-solve** (this is faithful to Andrade — α is *not*
SoC-endogenous in the decomposition) but make it temperature-derived instead of a flat user %/yr:

```
r_cal,y = α_hour(T̄_y, SoC-band, chem) · 8760          # per-year fraction, T-driven
g_{y,k} = (1 − r_cal,y)^(age−1)                        # replaces the flat rate in repeating_degradation_factor
α_hour  = c1·y³ + c2·y² + c3·y + c4                    # SoC-band per DoD map (§2.2)
```
- Low risk: it only reshapes the existing exogenous availability factor; no new variables. It answers the
  review's "frozen-temperature" complaint for the calendar channel.
- Do **not** resurrect the SoC-linked epigraph to chase Andrade — Andrade's α is banded/offline, so the
  removal actually *matches* the decomposition. (If SoC-endogenous calendar wear is wanted later, that is a
  step *beyond* Andrade, not part of it.)

### P2 — Make the endogenous solve reliable (don't abandon it)
The endogenous cycle slot is a pure LP; the review's "too slow / doesn't solve" is almost certainly
**degeneracy**, not intractability. Concrete hardening:
1. **Substitute `F_cyc` inline.** It is exactly `β·P^BE`; eliminating the `battery_cycle_fade` variable and
   its `8760·Y·S·K` definition constraints shrinks the model with zero modelling change.
2. **Tighten the `C_eff` year-link.** The `≤` link is pinned only by a `1e-9` credit → huge dual
   degeneracy. When exogenous fade is off, make it an **equality**; when both channels are on, keep `≤` but
   give `C_eff` a *real* small marginal value (below) so the state is well-determined.
3. **Give `C_eff` economic teeth.** Today it enters the objective at `1e-9`. Either (a) tie usable-capacity
   loss to a replacement/annuity signal, or (b) charge an explicit wear cost `Σ_t β·P^BE · c_repl` so the
   optimiser genuinely trades cycling against sizing (this is MicroGridsPy's structural advantage over
   HOMER — keep it).
4. **Clustering fallback.** If 8760×Y×S is still heavy, accumulate throughput over
   representative periods (already on the cross-cutting backlog) rather than full chronology.

### P3 — Depth weighting beyond the band (overtakes the dissertation)
Both flat-γ *and* Andrade's banded β carry the "one deep cycle = several shallow ones" error inside a band.
Upgrade the throughput to **weighted throughput (wAh)** — a SoC/DoD weight on `P^BE` (stays linear) — or a
**piecewise-linear DoD cost** (Xu et al. 2018) / **convex rainflow reformulation** (Shi et al. 2018), both
LP-compatible. Do **not** implement native rainflow counting inside the LP.

### P4 — Endogenous SoH-triggered replacement (later, higher risk)
Andrade did this iteratively (run → read SOH → set replacement year → re-run). To make it endogenous, link
an explicit SoH state to a replacement **decision** at an EOL threshold (Petrelli et al. 2021) — a
mixed-integer / fixed-point layer touching the annuity core. Only after P1–P3 give a trustworthy wear
signal; otherwise replacement triggers off a wrong signal. Interacts with the existing cohort mask: the
calendar-lifetime reset would become the *max* life, with SoH allowed to trigger earlier.

---

## 6. What NOT to do
- Don't chase ECM/electrochemical fidelity — Andrade shows a linear decomposition reproduces it to ≈2 %.
- Don't bolt native rainflow into the LP — it is a counting operator; use the convex reformulation.
- Don't keep flat exogenous %/yr as the *primary* mechanism — fine as a fallback/default, useless for
  trading operation against ageing.
- Don't make α or β decision variables — their power is that they are **exogenous** (LP-safe); endogenising
  them reintroduces the nonlinearity the decomposition exists to avoid.

## 7. Suggested order of work
1. Temperature input in the data pipeline (+ chemistry / DoD-band plumbing).  *(prereq)*
2. P1 β(T,DoD) transplant into the multi-year cycle slot + convention/units reconciliation + 20-yr SOH
   cross-check.  *(highest value)*
3. P1-calendar α(T)-driven rate.
4. P2 solve hardening (inline `F_cyc`, equality link, real `C_eff` value).
5. P3 depth weighting.
6. (optional) typical-year throughput-cost surrogate; P4 endogenous replacement.

*References:* Andrade 2023 (MSc, POLIMI/FCUL) eqs 3.20-3.41, Tables 3.5/3.6/3.9/3.14/3.16; Shamarova et al.
2022; Xu et al. 2018; Shi et al. 2018; Petrelli et al. 2021. See also `dev-notes/future_extensions.md`,
`docs/methodology/battery.md`.
