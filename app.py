"""Streamlit dashboard for Industrial Machine Dashboard V1."""
import time

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from calculations import calculate_oee
from config import MACHINE_CONFIG
from simulator import CNCSimulator

st.set_page_config(page_title="Industrial Machine Dashboard V1", page_icon="⚙️", layout="wide")
st.markdown("""
<style>
  .stApp {background: #0b1220; color: #e5e7eb}
  [data-testid="stMetric"] {background:#111c2e;border:1px solid #25344d;border-radius:8px;padding:14px}
  .state {display:inline-block;padding:6px 12px;border-radius:16px;background:#123c32;color:#55e6ad;font-weight:700}
  .panel {background:#111c2e;border:1px solid #25344d;border-radius:8px;padding:14px;margin-bottom:10px}
  .normal {color:#55e6ad}.warning {color:#fbbf24}.critical {color:#fb7185}
</style>
""", unsafe_allow_html=True)

if "simulator" not in st.session_state:
    st.session_state.simulator = CNCSimulator()
if "last_update" not in st.session_state:
    st.session_state.last_update = time.monotonic()

sim: CNCSimulator = st.session_state.simulator

with st.sidebar:
    st.header("Simulation Control")
    power = st.toggle("Machine power", value=sim.powered_on)
    sim.set_power(power)
    if st.button("▶ Start Cycle", use_container_width=True):
        sim.start_cycle()
    pause_label = "▶ Resume" if sim.paused else "⏸ Pause"
    if st.button(pause_label, use_container_width=True, disabled=not sim.running or not sim.powered_on):
        sim.toggle_pause()
    if st.button("↺ Reset Simulation", use_container_width=True):
        sim.reset()
    speed = st.selectbox("Simulation Speed", [1, 5, 10], format_func=lambda x: f"{x}x")
    spindle_override = st.slider("Spindle RPM override", 50, 120, 100, 5) / 100
    feed_override = st.slider("Feed override", 50, 120, 100, 5) / 100
    st.caption("Overrides affect commanded values; no faults are injected.")

now = time.monotonic()
elapsed = min(2.0, now - st.session_state.last_update)
st.session_state.last_update = now
sim.tick(max(0.1, elapsed) * speed, spindle_override, feed_override)
state = sim.state

cycle = time.strftime("%H:%M:%S", time.gmtime(state["cycle_time_seconds"]))
st.markdown(f"## {MACHINE_CONFIG['machine_id']} — 3-AXIS MACHINING CENTER &nbsp; <span class='state'>● {state['status']}</span>", unsafe_allow_html=True)
st.caption(f"Program: {state['program_name']}  ·  Tool: {state['current_tool']} — {state['tool_name']}  ·  Cycle: {cycle}  ·  Simulation: {state['timestamp']:%Y-%m-%d %H:%M:%S}")

oee = calculate_oee(sim.runtime_seconds, sim.planned_seconds, state["parts_completed"],
                    state["parts_rejected"], MACHINE_CONFIG["ideal_cycle_time_seconds"])
kpis = st.columns(5)
kpis[0].metric("Spindle Speed", f"{state['spindle_rpm']:,.0f} rpm")
kpis[1].metric("Feed Rate", f"{state['feed_rate']:,.0f} mm/min")
kpis[2].metric("Spindle Load", f"{state['spindle_load']:.1f}%")
kpis[3].metric("Parts Today", f"{state['parts_completed']}")
kpis[4].metric("OEE", f"{oee['oee'] * 100:.1f}%")

left, center, right = st.columns([1, 1.15, 1.15])
with left:
    st.subheader("Axis Position")
    for axis in "XYZ":
        st.markdown(f"### `{axis}  {state[f'{axis.lower()}_position']:+09.3f} mm`")
    fig = go.Figure(go.Scatter(x=[state["x_position"]], y=[state["y_position"]], mode="markers",
                               marker={"size": 15, "color": "#22d3ee", "symbol": "cross"}))
    fig.update_layout(height=230, margin=dict(l=5, r=5, t=5, b=5), template="plotly_dark",
                      xaxis=dict(range=[0, 800], title="X (mm)"), yaxis=dict(range=[0, 500], title="Y (mm)"),
                      paper_bgcolor="#111c2e", plot_bgcolor="#0b1220", showlegend=False)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with center:
    st.subheader("Machine Status")
    st.markdown(f"**State:** {state['status']}  \n**Program:** {state['program_name']}  \n**Tool:** {state['current_tool']} — {state['tool_name']}  \n**Cycle elapsed:** {cycle}")
    st.progress(state["cycle_progress"] / 100, text=f"Cycle progress: {state['cycle_progress']:.1f}%")
    a, b = st.columns(2)
    a.metric("Parts completed", state["parts_completed"])
    b.metric("Parts rejected", state["parts_rejected"])
    st.caption(f"Availability {oee['availability']:.0%} · Performance {oee['performance']:.0%} · Quality {oee['quality']:.0%}")

with right:
    st.subheader("Machine Health")
    def health(value: float, warning: float, critical: float) -> tuple[str, str]:
        return ("CRITICAL", "critical") if value > critical else (("WARNING", "warning") if value > warning else ("NORMAL", "normal"))
    readings = [
        ("Spindle temperature", state["spindle_temperature"], "°C", MACHINE_CONFIG["spindle_temp_warning"], MACHINE_CONFIG["spindle_temp_critical"]),
        ("Spindle load", state["spindle_load"], "%", MACHINE_CONFIG["spindle_load_warning"], MACHINE_CONFIG["spindle_load_critical"]),
        ("Coolant temperature", state["coolant_temperature"], "°C", MACHINE_CONFIG["coolant_temp_warning"], MACHINE_CONFIG["coolant_temp_critical"]),
        ("Vibration", state["vibration"], "mm/s", MACHINE_CONFIG["vibration_warning"], MACHINE_CONFIG["vibration_critical"]),
    ]
    for label, value, unit, warning, critical in readings:
        label_status, css = health(value, warning, critical)
        st.markdown(f"<div class='panel'><b>{label}</b><br>{value:.1f} {unit} · <span class='{css}'>{label_status}</span></div>", unsafe_allow_html=True)

st.subheader("Active Alarms")
if sim.active_alarms:
    st.dataframe(pd.DataFrame(sim.active_alarms), use_container_width=True, hide_index=True)
else:
    st.success("No active alarms")

st.subheader("Historical Trends — Latest 30 Minutes")
trend_options = {
    "Spindle Load": ("spindle_load", "%"), "Spindle RPM": ("spindle_rpm", "rpm"),
    "Feed Rate": ("feed_rate", "mm/min"), "Vibration": ("vibration", "mm/s"),
    "Spindle Temperature": ("spindle_temperature", "°C"),
}
selected = st.selectbox("Signal", trend_options.keys(), label_visibility="collapsed")
column, unit = trend_options[selected]
trend = px.line(sim.history, x="timestamp", y=column, template="plotly_dark", labels={column: unit, "timestamp": "Simulation time"})
trend.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), paper_bgcolor="#111c2e", plot_bgcolor="#0b1220")
st.plotly_chart(trend, use_container_width=True, config={"displayModeBar": False})

# Streamlit reruns the script, preserving the simulator in session state.
time.sleep(0.75)
st.rerun()
