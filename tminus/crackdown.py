"""Lane B. Did the crackdown work? Hectares newly cleared, inside La Pampa vs outside."""
from datetime import datetime

import numpy as np
import pandas as pd

from . import config as C
from . import rio

COLUMNS = ["period", "start", "end", "days", "phase", "inside_ha", "outside_ha",
           "inside_ha_per_month", "outside_ha_per_month"]


def _day(date):
    return datetime.strptime(date, "%Y%m%d")


def table(conf, change_idx, dates, profile):
    """Hectares cleared per period, inside C.LA_PAMPA vs elsewhere, before and after C.CRACKDOWN.

    A period is the gap between two consecutive scenes; a pixel counts in the period of the scene
    where the rule detector first flagged it and the confidence map still shows it. Pixels flagged
    only by the model have no date and are left out. phase is "before" (period ends on or before the
    crackdown), "after" (starts on or after it) or "straddles".
    """
    inside = rio.la_pampa_mask(profile)
    ha = C.RES * C.RES / 10_000
    hit = (conf > 0) & (change_idx >= 0)
    rows = []
    for i in range(1, len(dates)):
        new = hit & (change_idx == i)
        days = (_day(dates[i]) - _day(dates[i - 1])).days
        months = max(days, 1) / 30.4375
        ins = float((new & inside).sum()) * ha
        out = float((new & ~inside).sum()) * ha
        if dates[i] <= C.CRACKDOWN:
            phase = "before"
        elif dates[i - 1] >= C.CRACKDOWN:
            phase = "after"
        else:
            phase = "straddles"
        rows.append({
            "period": f"{dates[i - 1]} to {dates[i]}",
            "start": _day(dates[i - 1]).strftime("%Y-%m-%d"),
            "end": _day(dates[i]).strftime("%Y-%m-%d"),
            "days": days, "phase": phase,
            "inside_ha": round(ins, 2), "outside_ha": round(out, 2),
            "inside_ha_per_month": round(ins / months, 2), "outside_ha_per_month": round(out / months, 2),
        })
    return pd.DataFrame(rows, columns=COLUMNS)


def amw_table(amw, profile):
    """Independent check from Amazon Mining Watch (optical): hectares of mining first confirmed each
    year, inside La Pampa vs elsewhere. 2018 also holds everything mined before monitoring began."""
    inside = rio.la_pampa_mask(profile)
    ha = C.RES * C.RES / 10_000
    rows = []
    for year in np.unique(amw[amw > 0]).astype(int):
        hit = amw == year
        rows.append({"year": year, "inside_ha": round(float((hit & inside).sum()) * ha, 1),
                     "outside_ha": round(float((hit & ~inside).sum()) * ha, 1)})
    return pd.DataFrame(rows, columns=["year", "inside_ha", "outside_ha"])


def summary(tbl):
    """Average hectares per month before and after the crackdown, inside vs outside La Pampa.

    Periods that straddle the crackdown date are left out. Returns a DataFrame indexed by phase.
    """
    out = {}
    for phase in ("before", "after"):
        part = tbl[tbl["phase"] == phase]
        months = part["days"].sum() / 30.4375
        out[phase] = {
            "inside_ha_per_month": part["inside_ha"].sum() / months if months else np.nan,
            "outside_ha_per_month": part["outside_ha"].sum() / months if months else np.nan,
        }
    return pd.DataFrame(out).T
