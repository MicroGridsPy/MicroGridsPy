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


def csv_upload_interface(key_prefix: str) -> Tuple[st.file_uploader, str, str]:
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