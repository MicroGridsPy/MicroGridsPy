"""
This module provides utility functions for rendering the footer in the MicroGridsPy Streamlit application.
It includes functions to convert images to base64 strings and to render a footer with links to documentation, GitHub, and contact email.
"""
import base64
import streamlit as st

from typing import Tuple, Any
from io import BytesIO
from pathlib import Path
from PIL import Image

from config.path_manager import PathManager



def get_base64_image(image_path: Path, width: int, height: int) -> str:
    """Convert image to base64 string after resizing."""
    img = Image.open(image_path)
    img = img.resize((width, height), Image.LANCZOS)
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"


def render_footer() -> None:
    """Render the footer with icons linking to documentation, GitHub, and contact email."""
    doc_icon_base64 = get_base64_image(PathManager.ICONS_PATH / "doc_icon.ico", 20, 20)
    github_icon_base64 = get_base64_image(PathManager.ICONS_PATH / "github_icon.ico", 20, 20)
    mail_icon_base64 = get_base64_image(PathManager.ICONS_PATH / "mail_icon.ico", 20, 20)

    st.markdown(
        f"""
        <div class="footer">
            <div class="footer-right">
                <a href="{PathManager.DOCS_URL}" target="_blank">
                    <img src="{doc_icon_base64}" alt="Documentation" class="footer-icon">
                </a>
                <a href="{PathManager.GITHUB_URL}" target="_blank">
                    <img src="{github_icon_base64}" alt="GitHub" class="footer-icon">
                </a>
                <a href="mailto:{PathManager.MAIL_CONTACT}">
                    <img src="{mail_icon_base64}" alt="Contact" class="footer-icon">
                </a>
            </div>
        </div>
        <style>
        .footer {{
            position: fixed;
            left: 0;
            bottom: 0;
            width: 100%;
            background-color: #f1f1f1;
            text-align: center;
            padding: 10px;
        }}

        .footer-right {{
            float: right;
        }}
        </style>
        """,
        unsafe_allow_html=True)

def initialize_session_state(default_values: Any, settings_type: str) -> None:
    """Initialize session state variables from default values."""
    for key, value in vars(getattr(default_values, settings_type)).items():
        if key not in st.session_state:
            st.session_state[key] = value


def csv_upload_interface(key_prefix: str) -> Tuple[Any, str, str]:
    """
    Create an interface for CSV file upload with delimiter and decimal selection.
    
    Args:
        key_prefix (str): A prefix for Streamlit widget keys to avoid conflicts.
    
    Returns:
        Tuple[st.file_uploader, str, str]: Uploaded file, selected delimiter, and decimal separator.
    """
    delimiter_options = {
        "Comma (,)": ",",
        "Semicolon (;)": ";",
        "Tab (\\t)": "\t"}
    
    decimal_options = {
        "Dot (.)": ".",
        "Comma (,)": ","}
    
    delimiter = st.selectbox("Select delimiter", list(delimiter_options.keys()), key=f"{key_prefix}_delimiter")
    decimal = st.selectbox("Select decimal separator", list(decimal_options.keys()), key=f"{key_prefix}_decimal")
    
    delimiter_value = delimiter_options[delimiter]
    decimal_value = decimal_options[decimal]
    
    uploaded_file = st.file_uploader(f"Choose a CSV file", type=["csv"], key=f"{key_prefix}_uploader")
    
    return uploaded_file, delimiter_value, decimal_value

def generate_flow_chart(res_names: list) -> None:
    has_battery: bool = st.session_state.system_configuration in [0, 1]
    has_generator: bool = st.session_state.system_configuration in [0, 2]
    has_grid_connection: bool = st.session_state.grid_connection

    mermaid_code = "flowchart TB\n"
    if st.session_state.distribution_type == "Alternating Current":
        idx_connected_to_battery = [idx for idx, connection_type in enumerate(st.session_state.res_connection_types) if connection_type == "Connected with the same Inverter as the Battery to the Microgrid"]
        idx_not_connected_to_battery = [idx for idx, connection_type in enumerate(st.session_state.res_connection_types) if connection_type != "Connected with the same Inverter as the Battery to the Microgrid"]
        if idx_connected_to_battery:
            mermaid_code += "subgraph Shared_System [DC Subystem]\n"
            for idx in idx_connected_to_battery:
                mermaid_code += f"{res_names[idx].replace(' ', '_')} --> DC_System\n"
            mermaid_code += "Battery <--> DC_System\n"
            mermaid_code += "DC_System <--> Inverter_DC_System\n"
            mermaid_code += "end\n"
            mermaid_code += "Inverter_DC_System <--> Microgrid\n"
            for idx in idx_not_connected_to_battery:
                if st.session_state.res_connection_types[idx] == "Connected with a AC-AC Converter to the Microgrid":
                    mermaid_code += f"{res_names[idx].replace(' ', '_')} --> AC-AC_Converter_{res_names[idx].replace(' ', '_')}\n"
                    mermaid_code += f"AC-AC_Converter_{res_names[idx].replace(' ', '_')} --> Microgrid\n"
                else:
                    mermaid_code += f"{res_names[idx].replace(' ', '_')} --> Microgrid\n"
            if has_generator:
                mermaid_code += "Generator --> Microgrid\n"
            if has_grid_connection:
                if st.session_state.grid_connection_type == 0:
                    mermaid_code += "Grid --> Transformer\n"
                    mermaid_code += "Transformer --> Microgrid\n"
                elif st.session_state.grid_connection_type == 1:
                    mermaid_code += "Grid <--> Transformer\n"
                    mermaid_code += "Transformer <--> Microgrid\n"

        else:
            for idx in range(len(res_names)):
                if st.session_state.res_connection_types[idx] == "Connected with a seperate Inverter to the Microgrid":
                    mermaid_code += f"{res_names[idx].replace(' ', '_')} --> Inverter_{res_names[idx].replace(' ', '_')}\n"
                    mermaid_code += f"Inverter_{res_names[idx].replace(' ', '_')} --> Microgrid\n"
                elif st.session_state.res_connection_types[idx] == "Connected with a AC-AC Converter to the Microgrid":
                    mermaid_code += f"{res_names[idx].replace(' ', '_')} --> AC-AC_Converter_{res_names[idx].replace(' ', '_')}\n"
                    mermaid_code += f"AC-AC_Converter_{res_names[idx].replace(' ', '_')} --> Microgrid\n"
                else:
                    mermaid_code += f"{res_names[idx].replace(' ', '_')} --> Microgrid\n"
            if has_battery:
                mermaid_code += "Battery <--> Inverter_Battery\n"
                mermaid_code += "Inverter_Battery <--> Microgrid\n"
            if has_generator:
                mermaid_code += "Generator --> Microgrid\n"
            if has_grid_connection:
                if st.session_state.grid_connection_type == 0:
                    mermaid_code += "Grid --> Transformer\n"
                    mermaid_code += "Transformer --> Microgrid\n"
                elif st.session_state.grid_connection_type == 1:
                    mermaid_code += "Grid <--> Transformer\n"
                    mermaid_code += "Transformer <--> Microgrid\n"
    
    else:
        for idx in range(len(res_names)):
            if st.session_state.res_current_types[idx] == "Direct Current":
                mermaid_code += f"{res_names[idx].replace(' ', '_')} --> Microgrid\n"
            elif st.session_state.res_current_types[idx] == "Alternating Current":
                mermaid_code += f"{res_names[idx].replace(' ', '_')} --> Rectifier_{res_names[idx].replace(' ', '_')}\n"
                mermaid_code += f"Rectifier_{res_names[idx].replace(' ', '_')} --> Microgrid\n"
        if has_battery:
            mermaid_code += "Battery <--> Microgrid\n"
        if has_generator:
            mermaid_code += "Generator --> Rectifier_Generator\n"
            mermaid_code += "Rectifier_Generator --> Microgrid\n"
        if has_grid_connection:
            if st.session_state.grid_connection_type == 0:
                mermaid_code += "Grid --> Transformer\n"
                mermaid_code += "Transformer --> Microgrid\n"
            elif st.session_state.grid_connection_type == 1:
                mermaid_code += "Grid <--> Transformer\n"
                mermaid_code += "Transformer <--> Microgrid\n"

    # Add final connection to Load
    mermaid_code += "Microgrid --> Load\n"

    # Wrap Mermaid code in the HTML template
    mermaid_html = f"""
        <style>
            .mermaid {{
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }}
            svg {{
                font-family: 'Arial', sans-serif;
                background-color: #ffffff;
                border-radius: 10px;
                padding: 10px;
            }}
            text {{
                fill: #000000 !important; /* Black text */
                font-size: 14px;
                font-weight: 500;
            }}
            rect {{
                fill: #ffffff !important;  /* White background for boxes */
                stroke: #dd9d72 !important; /* Orange border */
                stroke-width: 2;
                rx: 8;
                ry: 8;
            }}
            path {{
                stroke: #000000 !important; /* Black arrows */
            }}
            .edgeLabelBackground {{
                fill: #ffffff !important; /* White background for edge labels */
            }}
        </style>

        <div class="mermaid">
        {mermaid_code}
        </div>

        <script type="module">
            import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
            mermaid.initialize({{
                startOnLoad: true,
                themeVariables: {{
                    background: "#ffffff",
                    primaryColor: "#dd9d72",
                    edgeLabelBackground: "#ffffff",
                    fontSize: "14px",
                    fontFamily: "Arial",
                    nodeBorder: "#dd9d72",
                    clusterBkg: "#ffffff",
                    nodeTextColor: "#000000",
                }},
            }});
        </script>
    """

    # Display the updated flowchart with styles
    st.components.v1.html(mermaid_html, height=500)
