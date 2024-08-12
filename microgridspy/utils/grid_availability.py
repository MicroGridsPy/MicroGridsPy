import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st
import math

def Weibull_CDF(x, a, b):
    y = 1 - math.exp(-(x/a)**b)
    return y

def Weibull_distrib(x, a, b):
    y = (b/(a**b)) * x**(b-1) * math.exp(-(x/a)**b)
    return y

def simulate_grid_availability(average_n_outages, average_outage_duration, project_lifetime, year_grid_connection, periods):
    grid_lifetime = project_lifetime - year_grid_connection + 1
    lambda_TBO = 1620/60  # Weibull scale factor for Time Between Outages distrib.
    k_TBO = 0.77          # Weibull shape factor for TBO distrib.
    lambda_OD = 36/60     # Weibull scale factor for Outage Duration distrib.
    k_OD = 0.56           # Weibull shape factor for OD distrib.

    # Create the pre-connection matrix (all zeros)
    pre_connection_matrix = np.zeros((periods, year_grid_connection - 1))

    if average_n_outages == 0 and average_outage_duration == 0:
        grid_matrix = np.ones((periods, grid_lifetime))
    else:
        rng = np.random.default_rng()
        OD_tot = grid_lifetime * average_n_outages * average_outage_duration / 60
        TBO_tot = grid_lifetime * periods - OD_tot
        samples_OD = []
        while sum(samples_OD) < OD_tot:
            spl = lambda_OD * rng.weibull(k_OD, size=1)[0]
            samples_OD.append(spl)
            if sum(samples_OD) > OD_tot:
                samples_OD[-1] = math.ceil(samples_OD[-1] - (sum(samples_OD) - OD_tot))
        samples_TBO = []
        while len(samples_TBO) < len(samples_OD):
            spl = lambda_TBO * rng.weibull(k_TBO, size=1)[0]
            samples_TBO.append(spl)
        k = abs(TBO_tot / (sum(samples_TBO)))
        samples_TBO = np.multiply(samples_TBO, k).tolist()
        n_samples = len(samples_OD)

        grid = []
        for ii in range(0, n_samples):
            TBO = int(round(samples_TBO[ii]))
            OD = int(round(samples_OD[ii]))
            grid.extend([1] * TBO)
            grid.extend([0] * OD)
            if len(grid) >= grid_lifetime * periods:
                grid = grid[:grid_lifetime * periods]
                break

        grid_matrix = np.ones((periods, grid_lifetime))
        year_count = 0
        ff = 0
        for ii in range(len(grid)):
            if year_count == grid_lifetime:
                break
            grid_matrix[ff, year_count] = grid[ii]
            ff += 1
            if ff == periods:
                year_count += 1
                ff = 0

    # Combine pre-connection matrix and grid availability matrix
    grid_availability_lifetime = np.hstack((pre_connection_matrix, grid_matrix))
    
    grid_availability_lifetime = pd.DataFrame(grid_availability_lifetime, 
                                              columns=range(1, project_lifetime + 1),
                                              index=range(1, periods + 1))

    # Plot distributions
    plot_availability_distributions(samples_TBO, samples_OD, lambda_TBO, k_TBO, lambda_OD, k_OD)

    return grid_availability_lifetime

def plot_availability_distributions(samples_TBO, samples_OD, lambda_TBO, k_TBO, lambda_OD, k_OD):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))
    
    # TBO plot
    times_TBO = np.linspace(0, 500, 1000)
    ax1.hist(samples_TBO, bins=500, density=True, alpha=0.7, label='Samples')
    ax1.plot(times_TBO, [Weibull_distrib(x, lambda_TBO, k_TBO) for x in times_TBO], 'r--', linewidth=1, label='Weibull distribution')
    ax1.set_xlabel('Time Between Outages [h]', fontsize=10)
    ax1.set_title('Samples Distribution vs. Weibull distribution (TBO)', fontsize=12)
    ax1.legend(loc='upper right')
    ax1.grid(axis='y', alpha=0.75)
    
    # OD plot
    times_OD = np.linspace(0, 20, 1000)
    ax2.hist(samples_OD, bins=500, density=True, alpha=0.7, label='Samples')
    ax2.plot(times_OD, [Weibull_distrib(x, lambda_OD, k_OD) for x in times_OD], 'r--', linewidth=1, label='Weibull distribution')
    ax2.set_xlabel('Outage Duration [h]', fontsize=10)
    ax2.set_title('Samples distribution vs. Weibull distribution (OD)', fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(axis='y', alpha=0.75)
    
    plt.tight_layout()
    st.pyplot(fig)

