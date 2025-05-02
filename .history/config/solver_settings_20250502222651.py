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
    
def get_solver_settings(solver: str, milp_formulation: bool) -> dict:
    if solver == "gurobi":
        return get_gurobi_settings(milp_formulation)
    elif solver == "glpk":
        return {
            "msg_lev": "GLP_MSG_ON",  # Control verbosity
            "tm_lim": 60000           # Time limit in milliseconds
        }
    elif solver == "scip":
        print("Configuring SCIP solver settings...")
        return {
            "limits/time": 600.0,                     # Increased time limit (in seconds)
            "display/verblevel": 4,                   # Verbosity level (0=silent, 5=maximum)
            "display/freq": 1,                        # Output frequency (1 = log every node)
            "heuristics/undercover/freq": -1,         # Disable undercover heuristic
            "presolving/maxrounds": 10,               # Increase presolving effort
            "separating/maxrounds": 10,               # Increase cuts/separation rounds
        }
    else:
        return {}