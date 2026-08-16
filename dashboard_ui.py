"""Upper-page presentation for the CNC dashboard.

This module intentionally owns only the interface from the machine header through
Active Alarms. Trend history and the 3D spindle view remain in ``app.py``.
"""
from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


ACCENTS = {
    "green": "#27e58b",
    "blue": "#28a9ff",
    "purple": "#b56cff",
    "yellow": "#ffd43b",
    "red": "#ff5263",
}


def apply_upper_dashboard_styles() -> None:
    st.markdown("""
    <style>
      :root { --panel:#0d1928; --panel2:#101e30; --line:#20344d; --muted:#8fa4bd; }
      .block-container {padding-top:1.25rem}
      .topbar {display:flex;align-items:center;justify-content:space-between;gap:20px;
        padding:18px 21px;margin-bottom:13px;border:1px solid var(--line);border-radius:12px;
        background:linear-gradient(135deg,#101e30 0%,#0b1624 75%);box-shadow:0 12px 35px #02060d55}
      .machine-kicker {font-size:11px;letter-spacing:.16em;color:#39aefc;font-weight:800;text-transform:uppercase}
      .machine-title {font-size:25px;font-weight:780;color:#f2f7ff;margin:3px 0 5px}
      .machine-meta {font-size:12px;color:var(--muted)}
      .state-pill {white-space:nowrap;padding:8px 13px;border-radius:8px;background:#0b392d;
        color:#35ed99;font-weight:800;font-size:13px;box-shadow:inset 0 0 0 1px #1c6d50}
      .kpi-card {height:112px;padding:14px 15px;border:1px solid var(--line);border-radius:10px;
        background:linear-gradient(145deg,#101e30,#0b1624);box-shadow:0 9px 24px #02060d40}
      .kpi-head {display:flex;align-items:center;gap:8px;color:#aebdd0;font-size:10px;
        font-weight:750;letter-spacing:.055em;text-transform:uppercase;white-space:nowrap}
      .kpi-icon {font-size:19px;color:var(--accent)}
      .kpi-value {font-size:24px;color:#f5f8fc;font-weight:700;margin:8px 0 8px;line-height:1}
      .kpi-unit {font-size:11px;color:#91a5bc;font-weight:500;margin-left:4px}
      .kpi-track {height:5px;background:#1c2a3b;border-radius:6px;overflow:hidden}
      .kpi-fill {height:100%;width:var(--fill);background:var(--accent);border-radius:6px;box-shadow:0 0 9px var(--accent)}
      .panel-label {display:flex;gap:8px;align-items:center;color:#dce7f5;font-size:12px;
        font-weight:780;letter-spacing:.045em;text-transform:uppercase;margin:5px 0 10px}
      .panel-label span {color:#31aef7;font-size:18px}
      .machine-card {border:1px solid var(--line);background:radial-gradient(circle at 50% 30%,#13263a,#07111d 72%);
        border-radius:10px;padding:11px 11px 8px;min-height:440px;box-shadow:0 9px 24px #02060d40}
      .machine-card img {border-radius:7px;display:block;width:100%}
      .asset-meta {display:flex;justify-content:space-between;color:#8398b0;font-size:10px;margin-top:9px}
      .axis-row {display:grid;grid-template-columns:28px 1fr;align-items:center;gap:8px;padding:7px 3px}
      .axis-letter {font-size:21px;font-weight:800;color:var(--axis)}
      .axis-value {font-family:ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--axis);font-size:14px;font-weight:700}
      .axis-range {height:5px;background:#1d2c40;border-radius:8px;margin-top:7px;overflow:hidden}
      .axis-range i {display:block;height:100%;width:var(--fill);background:var(--axis);border-radius:8px}
      .status-list {border:1px solid var(--line);border-radius:9px;background:#0a1522;padding:5px 12px}
      .status-row {display:flex;justify-content:space-between;gap:12px;padding:10px 1px;border-bottom:1px solid #17283b;
        font-size:11px;color:#8fa4bd}
      .status-row:last-child {border-bottom:0}.status-row b {color:#eef5ff;font-weight:600;text-align:right}
      .mini-pair {display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:9px}
      .mini-stat {border:1px solid var(--line);border-radius:8px;padding:11px;background:#0b1725;color:#8fa4bd;font-size:10px}
      .mini-stat strong {display:block;font-size:20px;margin-top:5px;color:var(--color)}
      .health-card {display:grid;grid-template-columns:29px 1fr auto;align-items:center;gap:9px;padding:10px;
        margin-bottom:7px;border:1px solid #1b3047;border-radius:8px;background:#0a1624}
      .health-icon {font-size:21px;color:var(--health)}.health-name {font-size:10px;color:#93a7bd}
      .health-value {font-size:15px;color:#eef5ff;margin-top:3px}.health-state {font-size:9px;font-weight:800;color:var(--health)}
      .alarm-empty {border:1px solid var(--line);border-radius:10px;padding:24px;text-align:center;background:#0a1624}
      .alarm-check {width:38px;height:38px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;
        border:2px solid #28e58b;color:#28e58b;font-size:21px;margin-bottom:7px}
      .alarm-empty b {display:block;color:#33e999;font-size:13px}.alarm-empty small {color:#8499b0}
      [data-testid="stSidebar"] {background:#091321;border-right:1px solid #1d3047}
    </style>
    """, unsafe_allow_html=True)


def _kpi(label: str, icon: str, value: str, unit: str, color: str, fill: float) -> None:
    st.markdown(f"""
    <div class="kpi-card" style="--accent:{color};--fill:{max(2, min(100, fill)):.1f}%">
      <div class="kpi-head"><span class="kpi-icon">{icon}</span>{escape(label)}</div>
      <div class="kpi-value">{escape(value)}<span class="kpi-unit">{escape(unit)}</span></div>
      <div class="kpi-track"><div class="kpi-fill"></div></div>
    </div>""", unsafe_allow_html=True)


def _health_status(value: float, warning: float, critical: float) -> tuple[str, str]:
    if value > critical:
        return "CRITICAL", ACCENTS["red"]
    if value > warning:
        return "WARNING", ACCENTS["yellow"]
    return "NORMAL", ACCENTS["green"]


def render_upper_dashboard(simulator: Any, machine_config: dict[str, Any], oee: dict[str, float],
                           cycle: str, machine_image: Path) -> None:
    """Render all dashboard content through the Active Alarms section."""
    state = simulator.state
    apply_upper_dashboard_styles()

    st.markdown(f"""
    <div class="topbar">
      <div>
        <div class="machine-kicker">Smart CNC Monitor · {escape(machine_config['machine_id'])}</div>
        <div class="machine-title">{escape(machine_config['machine_id'])} — 3-Axis Machining Center</div>
        <div class="machine-meta">Program: {escape(state['program_name'])} &nbsp;·&nbsp; Tool: {escape(state['current_tool'])} — {escape(state['tool_name'])} &nbsp;·&nbsp; Cycle: {cycle} &nbsp;·&nbsp; Simulation: {state['timestamp']:%Y-%m-%d %H:%M:%S}</div>
      </div>
      <div class="state-pill">● {escape(state['status'])}</div>
    </div>""", unsafe_allow_html=True)

    kpis = st.columns(5)
    with kpis[0]:
        _kpi("Spindle Speed", "◉", f"{state['spindle_rpm']:,.0f}", "rpm", ACCENTS["green"], state['spindle_rpm'] / machine_config['max_spindle_rpm'] * 100)
    with kpis[1]:
        _kpi("Feed Rate", "↗", f"{state['feed_rate']:,.0f}", "mm/min", ACCENTS["blue"], state['feed_rate'] / machine_config['max_feed_mm_min'] * 100)
    with kpis[2]:
        _kpi("Spindle Load", "◌", f"{state['spindle_load']:.1f}", "%", ACCENTS["purple"], state['spindle_load'])
    with kpis[3]:
        _kpi("Parts Today", "▣", str(state['parts_completed']), "pcs", ACCENTS["yellow"], min(100, state['parts_completed'] * 10))
    with kpis[4]:
        _kpi("OEE", "▥", f"{oee['oee'] * 100:.1f}", "%", ACCENTS["green"], oee['oee'] * 100)

    machine_col, axis_col, status_col, health_col = st.columns([1.0, 1.08, 1.0, 1.08])
    with machine_col:
        encoded_machine = base64.b64encode(machine_image.read_bytes()).decode("ascii")
        st.markdown('<div class="panel-label"><span>▦</span>Machine Overview</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="machine-card"><img src="data:image/png;base64,{encoded_machine}" alt="Modern 3-axis CNC machining center"><div class="asset-meta"><span>3-AXIS VMC</span><span>{escape(state["status"])}</span></div></div>',
            unsafe_allow_html=True,
        )

    with axis_col:
        st.markdown('<div class="panel-label"><span>⌖</span>Axis Position</div>', unsafe_allow_html=True)
        axis_specs = (
            ("X", state['x_position'], machine_config['x_min'], machine_config['x_max'], ACCENTS['green']),
            ("Y", state['y_position'], machine_config['y_min'], machine_config['y_max'], ACCENTS['blue']),
            ("Z", state['z_position'], machine_config['z_min'], machine_config['z_max'], ACCENTS['purple']),
        )
        for axis, value, low, high, color in axis_specs:
            fill = (value - low) / max(1, high - low) * 100
            st.markdown(f'<div class="axis-row" style="--axis:{color};--fill:{max(0, min(100, fill)):.1f}%"><div class="axis-letter">{axis}</div><div><div class="axis-value">{value:+09.3f} mm</div><div class="axis-range"><i></i></div></div></div>', unsafe_allow_html=True)
        figure = go.Figure(go.Scatter(
            x=[state['x_position']], y=[state['y_position']], mode="markers",
            marker={"size": 12, "color": ACCENTS['green'], "symbol": "cross"},
        ))
        figure.update_layout(
            height=225, margin={"l": 5, "r": 5, "t": 18, "b": 5}, template="plotly_dark",
            xaxis={"range": [0, 800], "title": "X (mm)", "gridcolor": "#183047"},
            yaxis={"range": [0, 500], "title": "Y (mm)", "gridcolor": "#183047"},
            paper_bgcolor="#0d1928", plot_bgcolor="#091522", showlegend=False,
        )
        st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})

    with status_col:
        st.markdown('<div class="panel-label"><span>⬡</span>Machine Status</div>', unsafe_allow_html=True)
        rows = (
            ("State", state['status']), ("Program", state['program_name']),
            ("Tool", f"{state['current_tool']} — {state['tool_name']}"), ("Cycle elapsed", cycle),
        )
        row_html = "".join(f'<div class="status-row"><span>{escape(label)}</span><b>{escape(str(value))}</b></div>' for label, value in rows)
        st.markdown(f'<div class="status-list">{row_html}</div>', unsafe_allow_html=True)
        st.progress(state['cycle_progress'] / 100, text=f"Cycle progress · {state['cycle_progress']:.1f}%")
        st.markdown(f'<div class="mini-pair"><div class="mini-stat" style="--color:{ACCENTS["green"]}">Parts completed<strong>{state["parts_completed"]}</strong></div><div class="mini-stat" style="--color:{ACCENTS["red"]}">Parts rejected<strong>{state["parts_rejected"]}</strong></div></div>', unsafe_allow_html=True)
        st.caption(f"Availability {oee['availability']:.0%} · Performance {oee['performance']:.0%} · Quality {oee['quality']:.0%}")

    with health_col:
        st.markdown('<div class="panel-label"><span>♡</span>Machine Health</div>', unsafe_allow_html=True)
        health_items = (
            ("♨", "Spindle temperature", state['spindle_temperature'], "°C", machine_config['spindle_temp_warning'], machine_config['spindle_temp_critical']),
            ("◔", "Spindle load", state['spindle_load'], "%", machine_config['spindle_load_warning'], machine_config['spindle_load_critical']),
            ("♦", "Coolant temperature", state['coolant_temperature'], "°C", machine_config['coolant_temp_warning'], machine_config['coolant_temp_critical']),
            ("〽", "Vibration", state['vibration'], "mm/s", machine_config['vibration_warning'], machine_config['vibration_critical']),
        )
        for icon, label, value, unit, warning, critical in health_items:
            health_state, color = _health_status(value, warning, critical)
            st.markdown(f'<div class="health-card" style="--health:{color}"><div class="health-icon">{icon}</div><div><div class="health-name">{escape(label)}</div><div class="health-value">{value:.1f} {escape(unit)}</div></div><div class="health-state">{health_state}</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="panel-label"><span style="color:#ff5263">♧</span>Active Alarms</div>', unsafe_allow_html=True)
    if simulator.active_alarms:
        st.dataframe(pd.DataFrame(simulator.active_alarms), width="stretch", hide_index=True)
    else:
        st.markdown('<div class="alarm-empty"><div class="alarm-check">✓</div><b>No active alarms</b><small>All monitored systems are operating normally</small></div>', unsafe_allow_html=True)
