def get_gurobi_settings(milp_formulation: bool) -> dict:
    """Get specific Gurobi settings based on the formulation type."""
    if milp_formulation:
        return {
            'Method': 3,
            'BarHomogeneous': 1,
            'Crossover': 1,
            'MIPFocus': 1,
            'BarConvTol': 1e-3,
            'OptimalityTol': 1e-3,
            'FeasibilityTol': 1e-4
        }
    else:
        return {
            'Method': 2,
            'BarHomogeneous': 0,
            'Crossover': 0,
            'BarConvTol': 1e-4,
            'OptimalityTol': 1e-4,
            'FeasibilityTol': 1e-4,
            'IterationLimit': 10000
        }