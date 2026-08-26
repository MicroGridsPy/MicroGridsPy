# Objective Function

Both planning modes minimize an **expected total system cost** built from annuitized
investment costs, expected operating costs, and optional externalities. The two modes share
the same economic logic but differ in how time is represented.

All monetary quantities are expressed in **real (inflation-free) terms**, measured in today's
money. Prices and costs are net of general inflation, and intertemporal discounting uses real
discount rates, so values at different times are directly comparable.

## Multi-Year Planning

The multi-year mode minimizes the **discounted expected system cost incurred within the
modelled horizon**, accounting for annualized investment payments, expected operating costs,
externality costs, and embodied-emission costs, all in present value:

\[
\min \; \sum_{y=1}^{H} \frac{SC_y}{(1+r_s)^{y}}
\]

where $r_s$ is the social discount rate and the **annual system cost** $SC_y$ is

\[
SC_y = \text{Annuity}_y
+ \sum_{\omega\in\Omega} p_\omega \left( \text{O}\&\text{M}_{y,\omega} + \text{Externalities}_{y,\omega} \right)
+ \text{EmbodiedEmissionCost}_y ,
\]

with $\omega\in\Omega$ the scenarios, each of probability $p_\omega$. The three cost blocks
decompose as

\[
\begin{aligned}
\text{Annuity}_y &= \sum_{j,k} \alpha_{j,k,y}\,\text{CAPEX}_{j,k}\,\text{CRF}_{j,k} \\[4pt]
\text{O}\&\text{M}_{y,\omega} &= \text{FixedO}\&\text{M}_{y,\omega} + \text{FuelCost}_{y,\omega}
+ \text{GridImportCost}_{y,\omega} - \text{GridExportRevenue}_{y,\omega} - \text{Subsidy}_{y,\omega} \\[4pt]
\text{Externalities}_{y,\omega} &= \text{LLCost}_{y,\omega} + \text{DirectEmissionCost}_{y,\omega} + \text{GridEmissionCost}_{y,\omega}
\end{aligned}
\]

where $\alpha_{j,k,y}$ is an **activation mask** that switches on the contribution of cohort
$k$ of technology $j$ from its commissioning step onward.

### Annuities and the capital recovery factor

Investment costs use an **annuity-based accounting framework** with explicit **investment
steps**. Each cohort of technology $j$, commissioned at step $\tau$ with present investment
cost $I_{j,\tau}$, technical lifetime $LT_j$, and weighted average cost of capital
$\text{WACC}_{j,\tau}$, is converted into a stream of constant annual payments through the
**capital recovery factor (CRF)**:

\[
\text{CRF}_{j,\tau} =
\frac{\text{WACC}_{j,\tau}\,(1+\text{WACC}_{j,\tau})^{LT_j}}
{(1+\text{WACC}_{j,\tau})^{LT_j}-1}
\]

The annuities are activated from the commissioning year and, in the current implementation,
persist over the remaining horizon through an implicit **like-for-like replacement** logic.
This represents phased investment and delayed deployment while avoiding explicit reinvestment
variables.

!!! note "Technical vs. economic lifetime"
    The annuity formulation implicitly spreads capital repayment over the **technical
    lifetime**; no distinction is made between technical and economic lifetime. Cohort annuity
    streams remain active over the remaining modelled horizon via an implicit replacement
    convention. This ensures internal consistency and avoids explicit reinvestment variables,
    but differs from a full-upfront-CAPEX accounting framework.

### Weighted Average Cost of Capital

The WACC represents the opportunity cost of capital:

\[
\text{WACC}_j =
\frac{E_j}{E_j + D_j}\,K^E_j
+ \frac{D_j}{E_j + D_j}\,K^D_j\,(1-T)
\]

where $E_j$ and $D_j$ are equity and debt shares, $K^E_j$ and $K^D_j$ the costs of equity and
debt, and $T$ the corporate tax rate. In MicroGridsPy the WACC is an explicit, configurable
parameter, able to represent concessional finance, public-sector investment, or policy-driven
de-risking.

### Dual-rate discounting

Intertemporal evaluation follows a **dual-rate logic**. Capital recovery for each technology
uses its WACC, while all system-level cash flows entering the objective — annuities, operating
costs, externalities, embodied-emission costs — are discounted to present value using a
**social discount rate** $r_s$. This separates financial opportunity costs at the asset level
from societal time preferences at the system level. Following the **Ramsey** formulation:

\[
r_s = \rho + \eta g
\]

where $\rho$ is the pure rate of time preference, $\eta$ the elasticity of marginal utility of
consumption, and $g$ the expected long-term growth of per-capita consumption.

### Time horizon, end-of-horizon bias, and accounting conventions

Long-term capacity expansion is conceptually an **infinite-horizon** problem, but optimization
is performed over a **finite modelled horizon**. This truncation can introduce **end-of-horizon
bias**, where investments near the terminal year are mis-valued if their remaining lifetime is
not accounted for — particularly for long-lived, capital-intensive technologies.

How horizon-end effects are treated depends on the **accounting convention**:

- Under a **full-upfront-CAPEX** convention, the entire investment is charged at commissioning
  and a **salvage value** correction is required for useful life beyond the horizon.
- Under an **annuity-based** convention, investment costs are annualized and only payments
  within the modelled years are counted, which naturally mitigates the most severe truncation
  effects.

MicroGridsPy's multi-year objective follows the **annuity-based** convention: only annualized
payments falling within the horizon enter the objective. A salvage-related quantity may still
be computed **in post-processing** for reporting, but it does **not** enter the optimization.
The formulation should therefore be read as a **finite-horizon approximation** of a long-term
planning problem, not one fully immune to terminal-horizon distortions.

## Typical-Year Planning

The typical-year mode minimizes the **expected equivalent annual cost (EAC)**. Investment
decisions are shared across scenarios; operational decisions and costs are scenario-specific:

\[
\min \; \text{Annuity}
+ \sum_{\omega\in\Omega} p_\omega \Big(
\text{FixedO}\&\text{M}_{\omega} + \text{FuelCost}_{\omega}
+ \text{GridImportCost}_{\omega} - \text{GridExportRevenue}_{\omega} - \text{Subsidy}_{\omega}
+ \text{LLCost}_{\omega} + \text{EmissionCost}_{\omega} \Big)
\]

!!! note "Discounting and sizing"
    In contrast to the multi-year formulation, **intertemporal discounting does not affect
    system sizing** in the typical-year model. Costs are evaluated on an annual basis and the
    system is assumed to operate indefinitely under stationary conditions; annuity-based
    capital recovery already embeds discounting at the asset level through the WACC. Sizing is
    therefore driven exclusively by the trade-off between annualized investment costs and
    expected annual operating costs.

## Relationship between the two objectives

Both objectives rely on the same bottom-up [cost accounting](cost-accounting.md). The
typical-year EAC is the **steady-state limit** of the multi-year objective under time-invariant
conditions: the multi-year model resolves investment, operating, and externality costs year by
year and discounts them, while the typical-year model annualizes investment over the technical
lifetime to yield horizon-independent annual equivalents.
