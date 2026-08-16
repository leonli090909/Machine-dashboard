"""Streamlit dashboard for Industrial Machine Dashboard V1."""
import importlib.util
from pathlib import Path
import time

import plotly.express as px
import streamlit as st

from calculations import calculate_oee
from cnc_program import CNC_PROGRAM
from config import MACHINE_CONFIG
from dashboard_ui import render_upper_dashboard
from simulator import CNCSimulator


@st.cache_resource
def load_3d_spindle_module():
    """Load the separately maintained module whose requested filename starts with a digit."""
    module_path = Path(__file__).with_name("3Dspindle.py")
    spec = importlib.util.spec_from_file_location("dashboard_3d_spindle", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load 3D spindle module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

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

oee = calculate_oee(sim.runtime_seconds, sim.planned_seconds, state["parts_completed"],
                    state["parts_rejected"], MACHINE_CONFIG["ideal_cycle_time_seconds"])
render_upper_dashboard(
    sim, MACHINE_CONFIG, oee, cycle, Path(__file__).with_name("assets") / "cnc-machine.png"
)

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

spindle_3d = load_3d_spindle_module()
spindle_3d.render_3d_spindle(sim, MACHINE_CONFIG, CNC_PROGRAM)

# Streamlit reruns the script, preserving the simulator in session state.
time.sleep(0.75)
st.rerun()
