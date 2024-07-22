import os
import sys
import unittest
import pandas as pd
import numpy as np
import xarray as xr
from unittest.mock import patch, MagicMock
import logging
from datetime import datetime

# Ensure the project root directory is in the PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from microgridspy.model.parameters import ProjectParameters
from microgridspy.model.initialize import (
    initialize_sets,
    initialize_demand,
    initialize_resource,
    initialize_project_parameters,
    initialize_res_parameters,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TestInitialization(unittest.TestCase):
    """Test initialization functions in the model module."""

    def setUp(self):
        logger.info("Setting up test environment")
        self.mock_data = MagicMock(spec=ProjectParameters)
        
        # Set up the nested structure
        self.mock_data.project_settings = MagicMock()
        self.mock_data.project_settings.time_resolution = 8760
        self.mock_data.project_settings.start_date = datetime(2024, 1, 1)
        self.mock_data.project_settings.time_horizon = 10
        self.mock_data.project_settings.discount_rate = 0.05
        self.mock_data.project_settings.optimization_goal = 0
        self.mock_data.project_settings.land_use = 1

        self.mock_data.advanced_settings = MagicMock()
        self.mock_data.advanced_settings.num_scenarios = 1
        self.mock_data.advanced_settings.wacc_calculation = False
        self.mock_data.advanced_settings.multi_scenario_optimization = 0
        self.mock_data.advanced_settings.greenfield_investment = 0

        self.mock_data.renewables_params = MagicMock()
        self.mock_data.renewables_params.res_names = ['solar', 'wind']
        self.mock_data.renewables_params.res_nominal_capacity = [1000, 16700000]
        self.mock_data.renewables_params.res_inverter_efficiency = [0.95, 0.97]
        self.mock_data.renewables_params.res_specific_investment_cost = [1000, 1500]
        self.mock_data.renewables_params.res_specific_om_cost = [0.02, 0.03]
        self.mock_data.renewables_params.res_lifetime = [25, 20]
        self.mock_data.renewables_params.res_unit_co2_emission = [50, 40]

    def test_initialize_sets(self):
        logger.info("Testing initialize_sets function")
        sets = initialize_sets(self.mock_data)
    
        self.assertIsInstance(sets, xr.Dataset)
        self.assertEqual(len(sets.periods), 8760)
        self.assertEqual(len(sets.years), 10)
        self.assertEqual(len(sets.scenarios), 1)
        self.assertEqual(len(sets.renewable_sources), 2)
        self.assertEqual(sets.renewable_sources.values.tolist(), ['solar', 'wind'])
    
        # Check the year_steps array
        self.assertEqual(sets.year_steps.shape, (87600, 2))  # 10 years * 8760 steps, 2 components (year, step)
        self.assertEqual(sets.year_steps.dims, ('year_step', 'step'))
    
        logger.info("initialize_sets test completed successfully")

    @patch('microgridspy.model.initialize.read_csv_data')
    def test_initialize_demand(self, mock_read_csv):
        logger.info("Testing initialize_demand function")
        mock_data = pd.DataFrame(np.random.rand(8760, 10))  # 10 years * 1 scenario
        mock_read_csv.return_value = mock_data

        sets = initialize_sets(self.mock_data)
        demand = initialize_demand(sets)

        self.assertIsInstance(demand, xr.DataArray)
        self.assertEqual(demand.shape, (8760, 1, 10))  # (periods, scenarios, years)
        self.assertEqual(demand.dims, ('periods', 'scenarios', 'years'))
        
        logger.info("initialize_demand test completed successfully")

    @patch('microgridspy.model.initialize.read_csv_data')
    def test_initialize_resource(self, mock_read_csv):
        logger.info("Testing initialize_resource function")
        mock_data = pd.DataFrame(np.random.rand(8760, 2))  # 2 renewable sources * 1 scenario
        mock_read_csv.return_value = mock_data

        sets = initialize_sets(self.mock_data)
        resource = initialize_resource(sets)

        self.assertIsInstance(resource, xr.DataArray)
        self.assertEqual(resource.shape, (8760, 1, 2))  # (periods, scenarios, renewable_sources)
        self.assertEqual(resource.dims, ('periods', 'scenarios', 'renewable_sources'))
        
        logger.info("initialize_resource test completed successfully")

    def test_initialize_project_parameters(self):
        logger.info("Testing initialize_project_parameters function")
        sets = initialize_sets(self.mock_data)
        params = initialize_project_parameters(self.mock_data, sets)

        self.assertIsInstance(params, xr.Dataset)
        self.assertEqual(params.TIME_HORIZON.values, 10)
        self.assertEqual(params.DISCOUNT_RATE.values, 0.05)
        
        logger.info("initialize_project_parameters test completed successfully")

    def test_initialize_res_parameters(self):
        logger.info("Testing initialize_res_parameters function")
        sets = initialize_sets(self.mock_data)
        params = initialize_res_parameters(self.mock_data, sets)

        self.assertIsInstance(params, xr.Dataset)
        np.testing.assert_array_equal(params.RES_NOMINAL_CAPACITY.values, [1000, 2000])
        np.testing.assert_array_equal(params.RES_INVERTER_EFFICIENCY.values, [0.95, 0.97])
        np.testing.assert_array_equal(params.RES_SPECIFIC_INVESTMENT_COST.values, [1000, 1500])
        np.testing.assert_array_equal(params.RES_SPECIFIC_OM_COST.values, [0.02, 0.03])
        np.testing.assert_array_equal(params.RES_LIFETIME.values, [25, 20])
        np.testing.assert_array_equal(params.RES_UNIT_CO2_EMISSION.values, [50, 40])
        
        logger.info("initialize_res_parameters test completed successfully")

if __name__ == '__main__':
    unittest.main()