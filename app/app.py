"""Lane C. The one web page.   streamlit run app/app.py"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tminus import config as C  # noqa: E402

st.set_page_config("La Pampa mining monitor", layout="wide")
st.title("La Pampa gold-mining monitor")

why, change, alert_tab, crackdown, accuracy, export = st.tabs(
    ["Why radar", "Change map", "Alerts", "Did the crackdown work?", "Accuracy", "Export"])

with why:
    st.info("TODO: cloudy Sentinel-2 next to clear radar from the same week")

with change:
    st.info("TODO: map with before/after slider and confidence overlay")

with alert_tab:
    st.info("TODO: alert cards with Google Maps links")

with crackdown:
    st.info("TODO: hectares cleared per year, La Pampa vs outside, before and after Feb 2019")

with accuracy:
    st.info("TODO: hits, misses, false alarms, precision and recall")

with export:
    st.info("TODO: KML / GeoJSON / CSV downloads")
