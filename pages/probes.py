import altair as alt
import pandas as pd
import streamlit as st

from auth import check_access_admin_only
from utils import load_data

check_access_admin_only()

# ---------------------------------------------------------------------------
# Probe definitions
# ---------------------------------------------------------------------------
PROBE_TYPES = ["Location", "Accelerometer", "Battery", "AmbientLight"]
PROBE_LABELS = {
    "Location": "Location",
    "Accelerometer": "Accelerometer",
    "Battery": "Battery",
    "AmbientLight": "Ambient light",
}

# High-frequency probes: plotting every reading is pointless and slow, so we downsample
# time series and default their tabs to a single participant.
HIGH_FREQUENCY = {"Accelerometer", "AmbientLight"}

# Cap points fed to Altair (its default guard is 5000 rows) and to the map.
MAX_TIMESERIES_POINTS = 5000
MAX_MAP_POINTS = 50_000

PALETTE = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def local_time(df: pd.DataFrame) -> pd.Series:
    """Vectorised UTC->local-naive using each row's tz offset string (e.g. '+05:30')."""
    offs = df["tz"].fillna("+00:00").astype(str)
    sign = offs.str[0].map({"+": 1, "-": -1}).fillna(1)
    parts = offs.str[1:].str.split(":", expand=True)
    hours = pd.to_numeric(parts[0], errors="coerce").fillna(0)
    minutes = pd.to_numeric(parts[1], errors="coerce").fillna(0) if parts.shape[1] > 1 else 0
    delta = pd.to_timedelta(sign * (hours * 60 + minutes), unit="m")
    return df["date"] + delta


def extract(sub: pd.DataFrame, fields, numeric=()) -> pd.DataFrame:
    """Pull dict keys out of the `data` column into their own columns."""
    out = sub.copy()
    for f in fields:
        out[f] = out["data"].apply(lambda d: (d or {}).get(f))
    for f in numeric:
        out[f] = pd.to_numeric(out[f], errors="coerce")
    return out


def downsample(df: pd.DataFrame, n: int = MAX_TIMESERIES_POINTS) -> pd.DataFrame:
    if len(df) <= n:
        return df
    step = max(1, -(-len(df) // n))  # ceil division
    return df.iloc[::step]


def color_map(codes) -> dict:
    return {c: PALETTE[i % len(PALETTE)] for i, c in enumerate(sorted(codes))}


def pick_participant(sub: pd.DataFrame, key: str) -> pd.DataFrame:
    """For high-frequency probes, restrict to one participant to keep charts readable."""
    codes = sorted(sub["pid"].unique())
    if len(codes) <= 1:
        return sub
    chosen = st.selectbox("Participant", codes, key=key)
    return sub[sub["pid"] == chosen]


# ---------------------------------------------------------------------------
# Per-probe renderers
# ---------------------------------------------------------------------------
def render_location(sub: pd.DataFrame, colors: dict):
    loc = extract(
        sub,
        ["latitude", "longitude", "altitude", "speed", "accuracy"],
        numeric=["latitude", "longitude", "altitude", "speed", "accuracy"],
    )
    valid = loc.dropna(subset=["latitude", "longitude"])
    valid = valid[(valid["latitude"].between(-90, 90)) & (valid["longitude"].between(-180, 180))]

    if valid.empty:
        st.info("No valid location fixes in the current selection.")
        return

    st.metric("Location fixes", f"{len(valid):,}")

    plotted = valid
    if len(valid) > MAX_MAP_POINTS:
        plotted = valid.sample(MAX_MAP_POINTS, random_state=0)
        st.caption(f"Showing a random {MAX_MAP_POINTS:,} of {len(valid):,} fixes on the map.")

    map_df = pd.DataFrame({
        "lat": plotted["latitude"].values,
        "lon": plotted["longitude"].values,
        "color": plotted["pid"].map(colors).values,
    })
    st.map(map_df, latitude="lat", longitude="lon", color="color")

    col1, col2 = st.columns(2)
    with col1:
        st.caption("Fix accuracy (m)")
        acc = valid.dropna(subset=["accuracy"])
        if acc.empty:
            st.text("No accuracy reported.")
        else:
            chart = (
                alt.Chart(downsample(acc))
                .mark_bar()
                .encode(
                    x=alt.X("accuracy:Q", bin=alt.Bin(maxbins=40), title="accuracy (m)"),
                    y=alt.Y("count()", title="fixes"),
                )
            )
            st.altair_chart(chart, use_container_width=True)
    with col2:
        st.caption("Speed over time (m/s)")
        spd = valid.dropna(subset=["speed"])
        if spd.empty:
            st.text("No speed reported.")
        else:
            chart = (
                alt.Chart(downsample(spd))
                .mark_line(opacity=0.7)
                .encode(
                    x=alt.X("local:T", title="time"),
                    y=alt.Y("speed:Q", title="speed (m/s)"),
                    color=alt.Color("pid:N", title="participant"),
                    tooltip=["local:T", "speed:Q", "pid:N"],
                )
                .interactive()
            )
            st.altair_chart(chart, use_container_width=True)


def render_accelerometer(sub: pd.DataFrame, colors: dict):
    sub = pick_participant(sub, key="accel_pid")
    acc = extract(sub, ["x", "y", "z"], numeric=["x", "y", "z"]).dropna(subset=["x", "y", "z"])
    if acc.empty:
        st.info("No accelerometer readings in the current selection.")
        return

    acc = acc.sort_values("local")
    acc["magnitude"] = (acc["x"] ** 2 + acc["y"] ** 2 + acc["z"] ** 2) ** 0.5

    # Effective sample rate from median inter-sample gap.
    gaps = acc["local"].diff().dt.total_seconds().dropna()
    gaps = gaps[gaps > 0]
    rate = f"{1 / gaps.median():.1f} Hz" if not gaps.empty else "n/a"
    c1, c2 = st.columns(2)
    c1.metric("Readings", f"{len(acc):,}")
    c2.metric("Median sample rate", rate)

    plot = downsample(acc)
    melted = plot.melt(
        id_vars=["local"], value_vars=["x", "y", "z"], var_name="axis", value_name="value"
    )
    st.caption("Acceleration per axis (g)")
    axes = (
        alt.Chart(melted)
        .mark_line(opacity=0.7)
        .encode(
            x=alt.X("local:T", title="time"),
            y=alt.Y("value:Q", title="acceleration (g)"),
            color=alt.Color("axis:N", scale=alt.Scale(domain=["x", "y", "z"])),
            tooltip=["local:T", "axis:N", "value:Q"],
        )
        .interactive()
    )
    st.altair_chart(axes, use_container_width=True)

    st.caption("Movement magnitude")
    mag = (
        alt.Chart(plot)
        .mark_line(opacity=0.7, color="#d62728")
        .encode(
            x=alt.X("local:T", title="time"),
            y=alt.Y("magnitude:Q", title="|acceleration| (g)"),
            tooltip=["local:T", "magnitude:Q"],
        )
        .interactive()
    )
    st.altair_chart(mag, use_container_width=True)


def render_battery(sub: pd.DataFrame, colors: dict):
    bat = extract(sub, ["level", "state", "source"], numeric=["level"]).dropna(subset=["level"])
    if bat.empty:
        st.info("No battery readings in the current selection.")
        return

    # level is 0..1 from the probe; show as %.
    bat = bat.sort_values("local")
    bat["percent"] = bat["level"] * 100

    st.caption("Battery level over time")
    line = (
        alt.Chart(downsample(bat))
        .mark_line(point=True, opacity=0.8)
        .encode(
            x=alt.X("local:T", title="time"),
            y=alt.Y("percent:Q", title="battery (%)", scale=alt.Scale(domain=[0, 100])),
            color=alt.Color("pid:N", title="participant"),
            tooltip=["local:T", "percent:Q", "state:N", "source:N", "pid:N"],
        )
        .interactive()
    )
    st.altair_chart(line, use_container_width=True)

    if bat["state"].notna().any():
        st.caption("Time spent in each battery state")
        states = bat.groupby("state").size().reset_index(name="readings")
        bars = (
            alt.Chart(states)
            .mark_bar()
            .encode(
                x=alt.X("readings:Q", title="readings"),
                y=alt.Y("state:N", sort="-x", title="state"),
                tooltip=["state:N", "readings:Q"],
            )
        )
        st.altair_chart(bars, use_container_width=True)


def render_ambient_light(sub: pd.DataFrame, colors: dict):
    sub = pick_participant(sub, key="light_pid")
    lig = extract(sub, ["lux", "brightness"], numeric=["lux", "brightness"])
    lig["value"] = lig["lux"].where(lig["lux"].notna(), lig["brightness"])
    lig = lig.dropna(subset=["value"]).sort_values("local")
    if lig.empty:
        st.info("No ambient-light readings in the current selection.")
        return

    unit = "lux" if lig["lux"].notna().any() else "brightness"
    st.metric("Readings", f"{len(lig):,}")
    st.caption(f"Ambient light over time ({unit})")
    chart = (
        alt.Chart(downsample(lig))
        .mark_line(opacity=0.7, color="#ff7f0e")
        .encode(
            x=alt.X("local:T", title="time"),
            y=alt.Y("value:Q", title=unit),
            tooltip=["local:T", "value:Q"],
        )
        .interactive()
    )
    st.altair_chart(chart, use_container_width=True)


RENDERERS = {
    "Location": render_location,
    "Accelerometer": render_accelerometer,
    "Battery": render_battery,
    "AmbientLight": render_ambient_light,
}


# ---------------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------------
st.title("Probes")

study = st.session_state.get("study")
datums = load_data(study)

if datums is None or datums.empty:
    st.info("No data is available.")
    st.stop()

probes = datums[datums["type"].isin(PROBE_TYPES)].copy()
if probes.empty:
    st.info("No probe data has been collected for this study yet.")
    st.stop()

probes["local"] = local_time(probes)
probes["day"] = probes["local"].dt.date
probes["hour"] = probes["local"].dt.hour

present_types = [p for p in PROBE_TYPES if p in set(probes["type"])]

# ---- Filters ----
with st.sidebar:
    st.header("Filters")
    selected_types = st.multiselect(
        "Probe", present_types, default=present_types,
        format_func=lambda p: PROBE_LABELS[p],
    )
    participants = sorted(probes["pid"].unique())
    selected_pids = st.multiselect("Participant", participants, default=participants)
    min_day, max_day = probes["day"].min(), probes["day"].max()
    date_range = st.date_input(
        "Date range", (min_day, max_day), min_value=min_day, max_value=max_day
    )

f = probes[
    probes["type"].isin(selected_types) & probes["pid"].isin(selected_pids)
]
if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
    start, end = date_range
    f = f[(f["day"] >= start) & (f["day"] <= end)]

if f.empty:
    st.warning("No probe data matches the selected filters.")
    st.stop()

colors = color_map(f["pid"].unique())

# ---- KPIs ----
k1, k2, k3, k4 = st.columns(4)
k1.metric("Probe datums", f"{len(f):,}")
k2.metric("Participants", f["pid"].nunique())
k3.metric("Probe types", f["type"].nunique())
k4.metric("Days covered", (f["day"].max() - f["day"].min()).days + 1)

# ---- Collection over time ----
st.subheader("Collection over time")
by_day = f.groupby(["day", "type"]).size().reset_index(name="count")
area = (
    alt.Chart(by_day)
    .mark_area(opacity=0.75)
    .encode(
        x=alt.X("day:T", title="day"),
        y=alt.Y("count:Q", title="readings", stack=True),
        color=alt.Color("type:N", title="probe"),
        tooltip=["day:T", "type:N", "count:Q"],
    )
    .properties(height=280)
)
st.altair_chart(area, use_container_width=True)

# ---- Time-of-day (background sanity check) ----
st.subheader("Time-of-day distribution")
st.caption(
    "Readings around the clock — including overnight — indicate background collection "
    "is working, not just while the app is open."
)
by_hour = f.groupby(["hour", "type"]).size().reset_index(name="count")
hour_chart = (
    alt.Chart(by_hour)
    .mark_bar()
    .encode(
        x=alt.X("hour:O", title="hour of day (local)"),
        y=alt.Y("count:Q", title="readings"),
        color=alt.Color("type:N", title="probe"),
        tooltip=["hour:O", "type:N", "count:Q"],
    )
    .properties(height=260)
)
st.altair_chart(hour_chart, use_container_width=True)

# ---- Collection context (foreground vs background) ----
st.subheader("Collection context")
st.caption(
    "Whether each reading was captured with the app in the foreground or while it was in the "
    "background. Plenty of background readings confirm collection keeps running when the app "
    "isn't open, not just while it is."
)
ctx = extract(f, ["appState"])
ctx["appState"] = ctx["appState"].fillna("unknown")

bg = int((ctx["appState"] == "background").sum())
fg = int((ctx["appState"] == "foreground").sum())
m1, m2 = st.columns(2)
m1.metric("Background readings", f"{bg:,}", f"{bg / len(ctx):.0%} of total")
m2.metric("Foreground readings", f"{fg:,}", f"{fg / len(ctx):.0%} of total")

st.caption("Readings by app state")
by_state = ctx.groupby("appState").size().reset_index(name="count")
state_chart = (
    alt.Chart(by_state)
    .mark_bar()
    .encode(
        x=alt.X("count:Q", title="readings"),
        y=alt.Y("appState:N", sort="-x", title="app state"),
        color=alt.Color("appState:N", legend=None),
        tooltip=["appState:N", "count:Q"],
    )
)
st.altair_chart(state_chart, use_container_width=True)

st.caption("Readings over time by app state — confirms background collection continues around the clock.")
state_over_time = ctx.groupby(["day", "appState"]).size().reset_index(name="count")
state_area = (
    alt.Chart(state_over_time)
    .mark_area(opacity=0.75)
    .encode(
        x=alt.X("day:T", title="day"),
        y=alt.Y("count:Q", title="readings", stack=True),
        color=alt.Color("appState:N", title="app state"),
        tooltip=["day:T", "appState:N", "count:Q"],
    )
    .properties(height=240)
)
st.altair_chart(state_area, use_container_width=True)

# ---- Participant coverage ----
st.subheader("Participant coverage")
st.caption("Readings per participant per day — gaps reveal who has stopped collecting.")
coverage = f.groupby(["pid", "day"]).size().reset_index(name="count")
heat = (
    alt.Chart(coverage)
    .mark_rect()
    .encode(
        x=alt.X("day:T", title="day"),
        y=alt.Y("pid:O", title="participant"),
        color=alt.Color("count:Q", title="readings", scale=alt.Scale(scheme="viridis")),
        tooltip=["pid:O", "day:T", "count:Q"],
    )
    .properties(height=alt.Step(18))
)
st.altair_chart(heat, use_container_width=True)

# ---- Per-probe detail ----
st.subheader("Probe detail")
tabs = st.tabs([PROBE_LABELS[p] for p in selected_types])
for tab, ptype in zip(tabs, selected_types):
    with tab:
        RENDERERS[ptype](f[f["type"] == ptype], colors)

# ---- Raw data ----
with st.expander("Raw probe datums"):
    raw = extract(f, ["appState"])
    table = (
        raw[["local", "pid", "type", "appState", "data"]]
        .sort_values("local", ascending=False)
        .rename(columns={"local": "time"})
        .reset_index(drop=True)
    )
    st.dataframe(table, use_container_width=True)
    st.download_button(
        "Download CSV",
        table.assign(data=table["data"].astype(str)).to_csv(index=False).encode("utf-8"),
        file_name=f"{study}_probes.csv",
        mime="text/csv",
    )
