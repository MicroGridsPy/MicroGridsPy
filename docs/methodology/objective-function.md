# Objective Function

Both planning modes minimize an **expected total system cost** built from annuitized
investment costs, expected operating costs, and optional externalities. The two modes
differ in how time is represented, but share the same underlying economic logic.

All monetary quantities are expressed in **real (inflation-free) terms**, measured in
today's money. Prices and costs are net of general inflation, and intertemporal discounting
uses real discount rates, so values occurring at different times are directly comparable.

## Multi-Year Planning

The multi-year mode minimizes the expected **Net Present Welfare Cost (NPWC)** over the
planning horizon, accounting for long-term investment decisions, system operation, and
external effects, all in present-value terms:

\[
\min \;
\sum_{y=1}^{H}
\frac{
\sum_j \text{Annuity}_{y,j}
+ \sum_{\omega\in\Omega} p_\omega \sum_j \left( \text{OPEX}_{y,j,\omega} + A^{ext}_{y,j,\omega} \right)
}{(1+r_s)^{y}}
\;-\;
\sum_j \frac{SV_j}{(1+r_s)^{H}}
\tag{1}
\]

where $\omega\in\Omega$ denotes the set of scenarios, each with probability $p_\omega$, and
$r_s$ is the social discount rate. The final term credits the **salvage value** of
long-lived assets at the end of the horizon.

### Annuities and the capital recovery factor

For a generic investment cohort of technology $j$ commissioned at step $\tau$, with present
investment cost $I_{j,\tau}$, technical lifetime $LT_j$, and weighted average cost of
capital $\text{WACC}_j$, the annualized investment cost is:

\[
\text{Annuity}_{j,\tau} = I_{j,\tau}\cdot CRF_j
\tag{2}
\]

with the **capital recovery factor (CRF)**:

\[
CRF_j = \frac{\text{WACC}_j\,(1+\text{WACC}_j)^{LT_j}}{(1+\text{WACC}_j)^{LT_j}-1}
\tag{3}
\]

The total annuity paid in a given model year sums the contributions of all investment
cohorts still within their technical lifetime, so capital costs are counted only while the
corresponding assets are available.

!!! note "Technical vs. economic lifetime"
    The annuity formulation implicitly assumes capital repayment is spread evenly over the
    **entire technical lifetime** of each technology — a fully amortized investment with
    constant annual payments. The current implementation makes **no distinction between
    technical and economic lifetime**. The formulation can be extended in future to allow an
    explicit economic lifetime or repayment period per technology.

### Weighted Average Cost of Capital

The WACC represents the opportunity cost of capital and is defined as:

\[
\text{WACC}_j =
\frac{E_j}{E_j + D_j}\,K^E_j
+ \frac{D_j}{E_j + D_j}\,K^D_j\,(1-T)
\tag{4}
\]

where $E_j$ and $D_j$ are the equity and debt shares, $K^E_j$ and $K^D_j$ the costs of
equity and debt, and $T$ the corporate tax rate.

!!! note "WACC as a configurable financing lever"
    Although the annuity structure mirrors project finance, MicroGridsPy treats the WACC as
    an explicit, configurable parameter. It can therefore represent concessional finance,
    public-sector investment, or policy-driven de-risking. Combined with externalities in
    the objective, the formulation extends naturally to **social cost–benefit analysis**.
    The WACC is assumed constant over time per technology, but the cohort-based structure
    allows time-dependent WACC values in principle.

### Dual-rate discounting

Intertemporal evaluation follows a **dual-rate** logic. Capital recovery for individual
technologies uses their respective WACC values, while all system-level cash flows entering
the objective — investment annuities, operational costs, externalities — are discounted to
present value using a **social discount rate** $r_s$. This separates financial opportunity
costs at the asset level from societal time preferences at the system level.

In welfare-based analysis, $r_s$ is commonly defined through the **Ramsey formulation**:

\[
r_s = \rho + \eta g
\tag{5}
\]

where $\rho$ is the pure rate of time preference, $\eta$ the elasticity of marginal utility
of consumption, and $g$ the expected long-term growth rate of per-capita consumption.

### Salvage value

For assets whose technical lifetime exceeds the planning horizon, an economically
consistent salvage value is credited at the end of the horizon. For a cohort of technology
$j$ commissioned in year $\tau$:

\[
SV_{j,\tau} =
\begin{cases}
\text{InvPresent}_{j,\tau}\cdot
\dfrac{(1+\text{WACC}_j)^{LT_j} - (1+\text{WACC}_j)^{H-\tau}}{(1+\text{WACC}_j)^{LT_j}-1},
& H-\tau < LT_j, \\[2ex]
0, & H-\tau \ge LT_j.
\end{cases}
\tag{6}
\]

This credits the fraction of unrecovered capital associated with the asset's remaining
technical lifetime beyond the horizon, discounted with the technology-specific WACC.
Economic consistency implies the annualized cost of an asset is **invariant to the chosen
horizon**: evaluating an investment over a truncated horizon *with salvage* yields the same
annual cost as evaluating it over its full lifetime. This ensures neutrality between early
and late investments.

## Typical-Year Planning

The typical-year mode minimizes the expected **equivalent annual cost (EAC)**. Investment
decisions are shared across scenarios; operational decisions and costs are scenario-specific:

\[
\min \;
\sum_j \big[ \text{CAPEX}_j\cdot CRF_j(\text{WACC}_j, LT_j) \big]
+ \sum_{\omega\in\Omega} p_\omega \sum_j
\left( \text{OPEX}_{j,\omega} + \text{FuelCost}_{j,\omega} + A^{ext}_{j,\omega} \right)
\tag{7}
\]

The first term is the annualized investment cost; the second is the expected annual
operating cost and externalities across scenarios.

!!! note "Discounting and sizing"
    In contrast to the multi-year formulation, **intertemporal discounting does not affect
    system sizing** in the typical-year model. All costs are evaluated on an annual basis and
    the system is assumed to operate indefinitely under stationary conditions; annuity-based
    capital recovery already embeds discounting at the asset level through the WACC. Sizing
    is driven exclusively by the trade-off between annualized investment costs and expected
    annual operating costs.

## Relationship between the two objectives

Both objectives rely on the same bottom-up [cost accounting](cost-accounting.md). The
typical-year EAC can be interpreted as the **steady-state limit** of the multi-year NPWC
under time-invariant conditions: the multi-year model resolves investment, operational, and
externality costs year by year and discounts them to present value, while the typical-year
model annualizes investment over the technical lifetime to yield horizon-independent annual
equivalents.
