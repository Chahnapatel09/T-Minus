"""Lane C. The one web page.   streamlit run app/app.py"""
import base64
import json
import sys
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tminus import config as C  # noqa: E402
from tminus import crackdown as crackdown_mod  # noqa: E402

ASSETS = Path(__file__).resolve().parent / "assets"

st.set_page_config("La Pampa mining monitor", layout="wide")
st.title("La Pampa gold-mining monitor")
st.caption("Radar change detection over La Pampa, Madre de Dios, Peru (RADARSAT-2 Tropical Forests data).")


# ---------- data ----------
@st.cache_data
def load_meta(stamp):
    p = C.WEB / "meta.json"
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else None


@st.cache_data
def load_csv(name, stamp):
    p = C.OUT / name
    return pd.read_csv(p) if p.exists() else None


@st.cache_data
def load_json(name, stamp):
    p = C.OUT / name
    return json.loads(p.read_text(encoding="utf8")) if p.exists() else None


def stamp(name):
    """Changes when the pipeline rewrites a file, so the caches refresh."""
    p = C.OUT / name
    return p.stat().st_mtime if p.exists() else 0


@st.cache_data
def data_uri(path, mtime):
    return "data:image/png;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def image_uri(path):
    return data_uri(str(path), Path(path).stat().st_mtime)


def pretty(date):
    return f"{date[:4]}-{date[4:6]}-{date[6:]}"


def first_image(*patterns):
    for pat in patterns:
        found = sorted(ASSETS.glob(pat))
        if found:
            return found[0]
    return None


meta = load_meta(stamp("web/meta.json"))
alerts = load_csv("alerts.csv", stamp("alerts.csv"))
crack = load_csv("crackdown.csv", stamp("crackdown.csv"))
amw = load_csv("crackdown_amw.csv", stamp("crackdown_amw.csv"))
acc = load_json("accuracy.json", stamp("accuracy.json"))
NEEDS_RUN = "No results yet. Run `python -m tminus.pipeline`, then reload this page."

why, change, alert_tab, crackdown, accuracy, export = st.tabs(
    ["Why radar", "Change map", "Alerts", "Did the crackdown work?", "Accuracy", "Export"])

# ---------- why radar ----------
with why:
    st.subheader("Optical cannot see here. Radar can.")
    st.write(
        "La Pampa sits under cloud for much of the year, and optical satellites such as Sentinel-2 only "
        "see the cloud tops. Radar sends its own microwave pulse and listens for the echo, so cloud, "
        "haze and night make no difference. Intact forest gives a bright, rough echo. Cleared ground "
        "gives a dark one, and still water (mining ponds) is darker still. That drop in backscatter is "
        "what this monitor looks for.")
    optical = first_image("sentinel2*.png", "sentinel2*.jpg", "optical*.png", "optical*.jpg")
    radar = first_image("radar*.png", "radar*.jpg")
    if radar is None and meta:
        radar = C.WEB / f"scene_{meta['dates'][-1]}.png"
    left, right = st.columns(2)
    with left:
        st.markdown("**Sentinel-2 (optical)**")
        if optical:
            st.image(str(optical), caption="Cloud hides the ground")
        else:
            st.info("Add a cloudy Sentinel-2 screenshot as app/assets/sentinel2.png")
    with right:
        st.markdown("**RADARSAT-2 (radar), same week**")
        if radar and Path(radar).exists():
            st.image(str(radar), caption="Clear view through the cloud")
        else:
            st.info("Add a radar screenshot as app/assets/radar.png, or run the pipeline.")

# ---------- change map ----------
with change:
    if not meta:
        st.info(NEEDS_RUN)
    else:
        dates = meta["dates"]
        st.subheader("Before and after")
        c1, c2 = st.columns(2)
        d_before = c1.selectbox("Before", dates, index=0, format_func=pretty)
        d_after = c2.selectbox("After", dates, index=len(dates) - 1, format_func=pretty)
        a = image_uri(C.WEB / f"scene_{d_before}.png")
        b = image_uri(C.WEB / f"scene_{d_after}.png")
        st.iframe(f"""
<div id="box" style="position:relative;width:100%;background:#000;line-height:0;user-select:none">
  <img src="{b}" style="width:100%;display:block">
  <img id="top" src="{a}" style="width:100%;position:absolute;left:0;top:0;clip-path:inset(0 50% 0 0)">
  <div id="bar" style="position:absolute;top:0;bottom:0;left:50%;width:2px;background:#fff"></div>
  <span style="position:absolute;left:8px;top:8px;background:#000a;color:#fff;font:12px sans-serif;padding:2px 6px;line-height:1.4">{pretty(d_before)}</span>
  <span style="position:absolute;right:8px;top:8px;background:#000a;color:#fff;font:12px sans-serif;padding:2px 6px;line-height:1.4">{pretty(d_after)}</span>
</div>
<input id="s" type="range" min="0" max="100" value="50" style="width:100%">
<script>
const s=document.getElementById('s'),t=document.getElementById('top'),bar=document.getElementById('bar');
s.oninput=()=>{{t.style.clipPath='inset(0 '+(100-s.value)+'% 0 0)';bar.style.left=s.value+'%';}};
</script>""", height=720)
        st.caption("Drag the slider. Dark patches that appear between the two dates are cleared ground or water.")

        st.subheader("Where the alerts are")
        (south, west), (north, east) = meta["bounds"]
        fmap = folium.Map(location=[(south + north) / 2, (west + east) / 2], zoom_start=11, tiles="OpenStreetMap")
        folium.raster_layers.ImageOverlay(image_uri(C.WEB / f"scene_{dates[-1]}.png"), bounds=meta["bounds"],
                                          name=f"Radar {pretty(dates[-1])}", opacity=0.8, show=False).add_to(fmap)
        folium.raster_layers.ImageOverlay(image_uri(C.WEB / "confidence.png"), bounds=meta["bounds"],
                                          name="Confidence (orange medium, red high)", opacity=0.9).add_to(fmap)
        lw, ls, le, ln = meta["la_pampa"]
        folium.Rectangle([[ls, lw], [ln, le]], color="#3388ff", weight=2, fill=False,
                         tooltip="La Pampa (approximate)").add_to(fmap)
        if alerts is not None:
            for _, r in alerts.head(200).iterrows():
                folium.CircleMarker(
                    [r.lat, r.lon], radius=4, color="#000", weight=1, fill=True,
                    fill_color="#d62728" if r.confidence == "high" else "#ff9f1c", fill_opacity=0.9,
                    tooltip=f"#{r.id} {r.type}, {r.area_ha} ha, priority {r.priority}").add_to(fmap)
        fmap.fit_bounds(meta["bounds"])
        folium.LayerControl().add_to(fmap)
        st_folium(fmap, height=560, use_container_width=True, returned_objects=[])

# ---------- alerts ----------
with alert_tab:
    if alerts is None:
        st.info(NEEDS_RUN)
    elif alerts.empty:
        st.success("No patches of %s ha or more were flagged." % C.MIN_PATCH_HA)
    else:
        f1, f2, f3, f4 = st.columns(4)
        kinds = f1.multiselect("Type", sorted(alerts["type"].unique()), default=sorted(alerts["type"].unique()))
        conf_pick = f2.selectbox("Confidence", ["all", "high only"])
        protected = f3.checkbox("Reserve buffer or Indigenous land only")
        top_n = f4.number_input("Show the top", min_value=5, max_value=500, value=20, step=5)
        view = alerts[alerts["type"].isin(kinds)]
        if conf_pick == "high only":
            view = view[view["confidence"] == "high"]
        if protected:
            view = view[view["in_buffer"] | view["in_indigenous"]]
        st.write(f"{len(view)} of {len(alerts)} alerts match, ranked by priority.")
        for _, r in view.head(int(top_n)).iterrows():
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
                c1.markdown(f"**#{int(r.id)}  {r.type}**  \n{r.area_ha} ha, first seen {r.first_seen}")
                c2.metric("Priority", f"{r.priority:.0f}")
                notes = [f"{r.confidence} confidence"]
                if r.in_buffer:
                    notes.append("in reserve buffer")
                if r.in_indigenous:
                    notes.append("on Indigenous land")
                if pd.notna(r.dist_road_m):
                    notes.append(f"{r.dist_road_m:.0f} m from road")
                if pd.notna(r.dist_river_m):
                    notes.append(f"{r.dist_river_m:.0f} m from river")
                c3.write(", ".join(notes))
                c4.link_button("Open in Google Maps", r.maps_url)

# ---------- crackdown ----------
with crackdown:
    if crack is None:
        st.info(NEEDS_RUN)
    else:
        st.write(f"Operation Mercury began in February 2019 ({pretty(C.CRACKDOWN)}). "
                 "Hectares newly cleared in La Pampa, against the rest of the area.")
        summ = crackdown_mod.summary(crack)
        m1, m2, m3, m4 = st.columns(4)
        for col, phase, where, label in [(m1, "before", "inside", "La Pampa, before"),
                                         (m2, "after", "inside", "La Pampa, after"),
                                         (m3, "before", "outside", "Outside, before"),
                                         (m4, "after", "outside", "Outside, after")]:
            v = summ.loc[phase, f"{where}_ha_per_month"]
            col.metric(label, "n/a" if pd.isna(v) else f"{v:.1f} ha/month")
        year = crack.assign(year=crack["end"].str[:4]).groupby("year")[["inside_ha", "outside_ha"]].sum()
        st.markdown("**Hectares cleared per year**")
        st.bar_chart(year.rename(columns={"inside_ha": "La Pampa", "outside_ha": "Outside"}))
        st.caption("A year is only as complete as the scenes we have for it. The rate per month below "
                   "is the fair comparison.")
        rate = crack.set_index("end")[["inside_ha_per_month", "outside_ha_per_month"]]
        st.markdown("**Hectares cleared per month, by scene interval**")
        st.line_chart(rate.rename(columns={"inside_ha_per_month": "La Pampa", "outside_ha_per_month": "Outside"}))
        st.dataframe(crack, hide_index=True)
        st.caption("The interval that contains the crackdown date is marked 'straddles' and is left out of the "
                   "before and after averages. Patches flagged only by the model have no date and are not counted.")
    if amw is not None and not amw.empty:
        st.subheader("Independent check: Amazon Mining Watch")
        st.write("New mining per year from Amazon Mining Watch, mapped from optical Sentinel-2 imagery by "
                 "Earth Genome, so it does not depend on our radar. 2018 also holds everything mined before then.")
        st.bar_chart(amw.astype({"year": str}).set_index("year")
                     .rename(columns={"inside_ha": "La Pampa", "outside_ha": "Outside"}))
        st.caption("Source: Amazon Mining Watch (Earth Genome, Pulitzer Center, Amazon Conservation), CC BY 4.0.")

# ---------- accuracy ----------
with accuracy:
    if acc is None:
        st.info(NEEDS_RUN)
    else:
        def table(block):
            names = {"rule": "Rule only", "model": "Model only", "combined": "Combined (either)",
                     "both": "Both agree (high)"}
            df = pd.DataFrame(block).T.rename(index=names)
            df = df.rename(columns={"hits": "Hits", "misses": "Misses", "false_alarms": "False alarms",
                                    "precision": "Precision", "recall": "Recall"})
            return df.style.format({"Precision": "{:.1%}", "Recall": "{:.1%}"}, na_rep="n/a")

        if "held_out" in acc:
            st.subheader("Held-out map blocks")
            st.write(f"Graded on {acc['held_out_pixels']:,} pixels in 2 km blocks the model never saw in "
                     f"training, against {acc.get('label_source', 'the mining labels')} "
                     f"(scene {pretty(acc['label_date'])}).")
            st.dataframe(table(acc["held_out"]))
            if len(acc.get("variants", {})) > 1:
                st.subheader("Does the foundation model help?")
                st.write("The same random forest, trained with and without features from a pretrained radar "
                         "network (ResNet50, SSL4EO-S12 Sentinel-1). The better one makes the map: "
                         f"**{acc['model_used']}**.")
                st.dataframe(table(acc["variants"]))
        else:
            st.info("The model was not trained (no labels: run `python -m tminus.labels`), "
                    "so there is no held-out score.")
        if "eye_points" in acc:
            st.subheader("Points checked by eye")
            st.write(f"{acc['eye_points_n']} points checked by eye on the imagery.")
            st.dataframe(table(acc["eye_points"]))
        st.caption("Hits: mining found. Misses: mining not found. False alarms: flagged where there is no mining. "
                   "Precision = hits / (hits + false alarms). Recall = hits / (hits + misses).")

# ---------- export ----------
with export:
    if alerts is None:
        st.info(NEEDS_RUN)
    else:
        st.write("Alert points with their ranking, ready for field teams or GIS.")
        for fname, mime, label in [("alerts.kml", "application/vnd.google-earth.kml+xml", "KML (Google Earth)"),
                                   ("alerts.geojson", "application/geo+json", "GeoJSON (GIS)"),
                                   ("alerts.csv", "text/csv", "CSV (spreadsheet)")]:
            p = C.OUT / fname
            if p.exists():
                st.download_button(f"Download {label}", p.read_bytes(), file_name=fname, mime=mime)
