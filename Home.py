from __future__ import annotations

from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="MicroGridsPy - Planning",
    layout="wide",
)


ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DOCS_DIR = Path(__file__).resolve().parent / "docs"
REPOSITORY_URL = "https://github.com/AleOnori98/microgridspy-planning"
RAMP_URL = "https://github.com/AleOnori98/RAMP-Streamlit"
PVGIS_URL = "https://github.com/AleOnori98/PVGIS-Streamlit-App"
LV_TOPOLOGY_URL = "https://github.com/AleOnori98/LV-Distribution-Topology-Streamlit"
ONLINE_DOCS_URL = "https://microgridspy-documentation.readthedocs.io/en/latest/index.html"

ECOSYSTEM_TOOL_ROWS = (
    (
        {
            "title": "RAMP Demand Model",
            "description": "Bottom-up stochastic demand assessment for appliances, households, and community load evolution.",
            "image_name": "ramp_tool_card.png",
            "badge": "Upstream input layer",
            "repo_url": RAMP_URL,
        },
        {
            "title": "PVGIS Resource Assessment",
            "description": "Solar and wind resource estimation used to build planning-ready renewable input profiles.",
            "image_name": "pvgis_tool_card.png",
            "badge": "Upstream input layer",
            "repo_url": PVGIS_URL,
        },
    ),
    (
        {
            "title": "LV Distribution Topology Tool",
            "description": "Distribution network layout, pole placement, and topology design for the physical electrification layer.",
            "image_name": "distribution_tool_card.jpeg",
            "badge": "Network design layer",
            "repo_url": LV_TOPOLOGY_URL,
        },
        {
            "title": "Dispatch Simulation Module",
            "description": "Detailed operational analysis starting from a predefined system design, useful for operational realism and control studies.",
            "image_name": "simulation_tool_card.png",
            "badge": "Operational analysis layer",
        },
    ),
)

APP_PAGE_LINKS = (
    ("pages/0_Project_Setup.py", "1. Project Setup"),
    ("pages/1_Data_Audit_and_Visualization.py", "2. Data Audit and Visualization"),
    ("pages/3_Optimization.py", "3. Optimization"),
    ("pages/4_Results.py", "4. Results"),
)

REPOSITORY_REFERENCES = (
    "`README.md`: overall project scope and workflow",
    "`docs/DATA_CONTRACT.md`: canonical dataset contract",
    "`docs/Mathematical_Formulation.pdf`: formulation reference",
    "`docs/User_Guide.pdf`: user guide draft",
    "`projects/`: example projects and input templates",
)

PDF_PREVIEWS = (
    {
        "title": "Mathematical Formulation",
        "caption": "Complete formulation reference with the current model structure and equations.",
        "file_name": "Mathematical_Formulation.pdf",
        "key": "mathematical_formulation_preview",
    },
    {
        "title": "User Guide",
        "caption": "Working user guide preview. The document is available here, but it is still being updated.",
        "file_name": "User_Guide.pdf",
        "key": "user_guide_preview",
    },
)

USEFUL_LINKS = (
    ("Online Read-the-Docs Documentation (work in progress)", ONLINE_DOCS_URL),
)


def _asset(name: str) -> str:
    return str(ASSETS_DIR / name)


def _doc(name: str) -> Path:
    return DOCS_DIR / name


def _inject_css() -> None:
    st.markdown(
        """
        <style>
        :root {
            --mgpy-ink: #153243;
            --mgpy-muted: #5b6b73;
            --mgpy-accent: #1f7a8c;
            --mgpy-gold: #f4b942;
            --mgpy-surface: #f7fbfc;
            --mgpy-border: rgba(21, 50, 67, 0.10);
        }
        .featured-card {
            display: block;
            height: 0.01rem;
            margin: 0;
            padding: 0;
            opacity: 0;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:has(.featured-card) {
            border: 2px solid rgba(47, 128, 237, 0.95) !important;
            box-shadow: 0 8px 24px rgba(47, 128, 237, 0.10);
            background: linear-gradient(180deg, #ffffff 0%, #f7fbff 100%);
        }
        .featured-kicker {
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 999px;
            background: rgba(47, 128, 237, 0.12);
            color: #2f80ed;
            font-size: 0.82rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            margin-bottom: 0.4rem;
        }
        div[data-testid="stButton"]:has(button[kind="primary"]) button {
            background: linear-gradient(135deg, #2f80ed 0%, #1f7a8c 100%);
            border: 1px solid #2f80ed;
            color: white;
            font-weight: 700;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_featured_planning_card() -> None:
    with st.container(border=True):
        st.markdown('<div class="featured-card"></div>', unsafe_allow_html=True)
        col_image, col_body = st.columns([1.15, 1.45], gap="large")
        with col_image:
            st.image(_asset("planning_tool_card.png"), width="stretch")
        with col_body:
            st.markdown('<div class="featured-kicker">Core planning engine</div>', unsafe_allow_html=True)
            st.markdown("### MicroGridsPy Planning")
            st.write(
                "Techno-economic optimization of mini-grid systems under deterministic or stochastic assumptions. "
                "Use it to size renewables, batteries, generators, and grid interaction with either a representative typical year "
                "or a multi-year dynamic formulation with capacity expansion."
            )
            st.markdown(f"[GitHub repository]({REPOSITORY_URL})")
            if st.button("Open Project Setup", type="primary", key="open_project_setup"):
                st.switch_page("pages/0_Project_Setup.py")


def _tool_card(
    *,
    title: str,
    description: str,
    image_name: str,
    badge: str,
    repo_url: str | None = None,
) -> None:
    with st.container(border=True):
        st.image(_asset(image_name), width="stretch")
        st.caption(badge)
        st.markdown(f"**{title}**")
        st.write(description)
        if repo_url:
            st.markdown(f"[GitHub repository]({repo_url})")


def _render_pdf_preview(*, title: str, caption: str, file_name: str, key: str) -> None:
    pdf_path = _doc(file_name)
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.caption(caption)
        if not pdf_path.exists():
            st.warning(f"Missing file: `{pdf_path.name}`")
            return

        if hasattr(st, "pdf"):
            try:
                st.pdf(str(pdf_path), height=520, key=key)
            except Exception:
                st.info(
                    "PDF preview is unavailable in this Streamlit environment. "
                    "Install the PDF extra to enable embedded previews."
                )
        else:
            st.info(
                "This Streamlit version does not expose `st.pdf()` yet, so the embedded preview is not available."
            )

        with pdf_path.open("rb") as pdf_file:
            st.download_button(
                "Download PDF",
                data=pdf_file.read(),
                file_name=pdf_path.name,
                mime="application/pdf",
                key=f"{key}_download",
                use_container_width=True,
            )


def _render_markdown_bullets(title: str, items: tuple[str, ...]) -> None:
    bullet_lines = "\n".join(f"- {item}" for item in items)
    st.markdown(f"**{title}**\n\n{bullet_lines}")


def _render_useful_links() -> None:
    link_lines = "\n".join(f"- {label}: {url}" for label, url in USEFUL_LINKS)
    st.markdown(f"**Useful links**:\n\n{link_lines}")


def _render_ecosystem() -> None:
    st.title("Welcome to MicroGridsPy!")
    st.markdown(
        "**MicroGridsPy Planning** is the techno-economic optimization layer of the MicroGridsPy ecosystem."
    )
    st.markdown(
        "It supports off-grid and weak-grid mini-grid design, combining renewable generation, batteries, generators, "
        "optional grid interaction, stochastic scenarios, and both typical-year and multi-year capacity-expansion formulations. "
        "The broader ecosystem connects resource assessment, demand modelling, distribution design, planning, and detailed operational analysis into one coherent workflow."
    )

    _render_featured_planning_card()
    st.subheader("Ecosystem tools")
    for tool_row in ECOSYSTEM_TOOL_ROWS:
        columns = st.columns(len(tool_row), gap="large")
        for column, tool in zip(columns, tool_row):
            with column:
                _tool_card(**tool)


def _render_resources() -> None:
    st.subheader("Resources and Navigation")
    st.write(
        "Use this application as the planning workspace inside the broader ecosystem. "
        "The links below help you start a new project and locate the main reference material already available in this repository."
    )
    st.write("")

    c1, c2 = st.columns([1, 3.0], gap="large")
    with c1:
        st.markdown("**Start here in this app**")
        for page_path, label in APP_PAGE_LINKS:
            st.page_link(page_path, label=label)

    with c2:
        _render_markdown_bullets("Repository references", REPOSITORY_REFERENCES)

    st.write("")
    st.markdown("**At a glance**")
    info_cols = st.columns(3, gap="medium")
    with info_cols[0]:
        st.info("Planning modes: Typical-year for compact investment studies, multi-year for dynamic expansion and long-horizon planning.")
    with info_cols[1]:
        st.info("Backend: Python + Streamlit frontend, Linopy optimization backend, CSV/YAML/JSON project workflow.")
    with info_cols[2]:
        st.info("Use together: Resource, demand, planning, network, and dispatch modules can be combined at increasing levels of detail.")

    st.write("")
    st.markdown("**Documentation preview**")
    pdf_cols = st.columns(2, gap="large")
    for column, preview in zip(pdf_cols, PDF_PREVIEWS):
        with column:
            _render_pdf_preview(**preview)

    st.write("")
    _render_useful_links()



def _render_footer() -> None:
    st.subheader("Contacts")
    st.markdown("**Active Developer**")
    st.markdown(
        """
        **Alessandro Onori**  
        *Core Linopy optimization model, modeling advancements, and Streamlit UI development*
        """
    )

    st.markdown("**Technical Advisors**")
    st.markdown(
        """
        - Nicolò Stevanato, Politecnico di Milano
        - Riccardo Mereu, Politecnico di Milano
        - Emanuela Colombo, Politecnico di Milano
        """
    )

    st.subheader("License")
    st.markdown("Open-source research codebase. Refer to the repository materials for the current licensing terms.")


def render_home_page() -> None:
    _inject_css()
    _render_ecosystem()
    _render_resources()
    st.divider()
    _render_footer()


render_home_page()
