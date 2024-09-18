"""
This module provides the main entry point for the MicroGridsPy Streamlit application.
It sets up the main layout of the application, including the navigation menu in the sidebar and the main content area.
The application manages session state to keep track of the current page being viewed and displays the appropriate page based on user interactions.
"""

import streamlit as st

from config.path_manager import PathManager
from microgridspy.gui.utils import render_footer
from microgridspy.gui.views.settings_page import settings_page
from microgridspy.gui.views.advanced_settings import advanced_settings
from microgridspy.gui.views.demand_page import demand_assessment
from microgridspy.gui.views.new_project import new_project
from microgridspy.gui.views.resource_page import resource_assessment
from microgridspy.gui.views.renewables_page import renewables_technology
from microgridspy.gui.views.battery_page import battery_technology
from microgridspy.gui.views.generator_page import generator_technology
from microgridspy.gui.views.grid_page import grid_technology
from microgridspy.gui.views.profit_page import project_profitability
from microgridspy.gui.views.grid_network import grid_routing
from microgridspy.gui.views.run_page import run_model
from microgridspy.gui.views.plots_dashboard import plots_dashboard

st.set_page_config(
    page_title="MicroGridsPy User Interface",
    page_icon=":bar_chart:",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': PathManager.DOCS_URL,
        'Report a bug': f'mailto:{PathManager.MAIL_CONTACT}',
        'About': (
            "**MicroGridsPy** has been developed within **SESAM group** in the *Department of Energy Engineering* at Politecnico di Milano."
            "The research activity of SESAM focuses on the use of mathematical models for the study of systems, components and processes in the energy field and industrial ecology."
            "MicroGridsPy is based on the original model by **Sergio Balderrama** (Universidad Mayor de San Simón) and **Sylvain Quoilin** (Université de Liège) and it is developed in the open on **GitHub**: Contributions are very welcome!"
        )
    }
)


def main() -> None:
    """
    Main entry point for the Streamlit application.

    This function sets up the main layout of the application, including the navigation menu
    in the sidebar and the main content area. It manages the session state to keep track of 
    the current page being viewed and displays the appropriate page based on user interactions.
    """

    # Ensure that 'new_project_completed' flag is in session state
    if 'new_project_completed' not in st.session_state:
        st.session_state.new_project_completed = False

    # Sidebar for navigation
    st.sidebar.title("Navigation Menu")

    # Determine if buttons should be enabled
    buttons_enabled = st.session_state.new_project_completed

    # Navigation buttons
    if st.sidebar.button("Project Settings", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Project Settings"

    if st.sidebar.button("Advanced Settings", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Advanced Settings"

    if st.sidebar.button("Resource Assessment", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Resource Assessment"

    if st.sidebar.button("Demand Assessment", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Demand Assessment"

    if st.sidebar.button("Renewables Characterization", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Renewables Characterization"

    if st.sidebar.button("Battery Characterization", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Battery Characterization"

    if st.sidebar.button("Generator Characterization", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Generator Characterization"

    if st.sidebar.button("Grid Connection", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Grid Connection"

    if st.sidebar.button("Mini-Grid Optimization", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Optimization"

    if st.sidebar.button("Grid Network", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Grid Network"

    if st.sidebar.button("Results Dashboard", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Results"

    if st.sidebar.button("Project Profitability", disabled=not buttons_enabled):
        if buttons_enabled:
            st.session_state.page = "Project Profitability"

    # Set default page to "New Project" if no page is set in session state
    if 'page' not in st.session_state:
        st.session_state.page = "New Project"

    # Dictionary to store frame references (views)
    pages = {
        "New Project": new_project,
        "Project Settings": settings_page,
        "Advanced Settings": advanced_settings,
        "Resource Assessment": resource_assessment,
        "Demand Assessment": demand_assessment,
        "Renewables Characterization": renewables_technology,
        "Battery Characterization": battery_technology,
        "Generator Characterization": generator_technology,
        "Grid Connection": grid_technology,
        "Optimization": run_model,
        "Grid Network": grid_routing,
        "Results": plots_dashboard,
        "Project Profitability": project_profitability,
    }

    # Display the selected frame
    # This will call the function associated with the current page stored in session state
    pages[st.session_state.page]()

    # If the current page is "New Project", check for completion and update the flag
    if st.session_state.page == "New Project":
        if check_new_project_completion():
            st.session_state.new_project_completed = True

    # Render the footer
    render_footer()


def check_new_project_completion() -> bool:
    """
    Check if the New Project page has been completed.

    Returns:
        bool: True if the New Project page is completed, False otherwise.
    """
    return 'project_name' in st.session_state and 'default_values' in st.session_state


if __name__ == "__main__":
    main()
