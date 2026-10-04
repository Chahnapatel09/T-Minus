"""Lane C. The one web page.   streamlit run app/app.py

The page itself is plain HTML/CSS/JS in app/web/. This file inlines it into one
document and hands it the pipeline's results, gathered by app/dashboard.py.
Until the pipeline has run, the page shows the sample values in app/web/data.js.
"""
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dashboard  # noqa: E402

WEB = Path(__file__).resolve().parent / "web"


@st.cache_data(show_spinner="Reading the pipeline results...")
def results(stamp):
    """Rebuilt only when the pipeline rewrites its files (the stamp changes)."""
    return dashboard.build()


def page():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "styles.css").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="styles.css">', f"<style>{css}</style>")
    for name in ("data.js", "scene.js", "app.js"):
        js = (WEB / name).read_text(encoding="utf-8")
        html = html.replace(f'<script src="{name}"></script>', f"<script>{js}</script>")
    data = results(dashboard.stamp())
    if data is not None:
        payload = json.dumps(data).replace("</", "<\\/")
        html = html.replace('<div id="app"></div>', f'<div id="app"></div><script>window.TMINUS_DATA = {payload};</script>')
    return html


st.set_page_config("T-Minus · Gold Mining Radar Monitor", layout="wide")
# The page brings its own layout: drop Streamlit's chrome and let the frame fill the window.
st.markdown(
    """<style>
    header, footer, [data-testid="stToolbar"], [data-testid="stDecoration"],
    [data-testid="stSkillsNudge"], [data-testid="stSkillsNudgeAnchor"] { display: none !important; }
    .stApp { background: #f3f4f6; }
    .stMainBlockContainer, .block-container { padding: 0 !important; max-width: 100% !important; }
    [data-testid="stMarkdownContainer"]:has(style) { display: none; }
    [data-testid="stVerticalBlock"] { gap: 0; }
    iframe { height: 100vh !important; display: block; border: 0; }
    </style>""",
    unsafe_allow_html=True,
)
st.iframe(page(), height=900, alt="T-Minus gold mining radar monitor")
