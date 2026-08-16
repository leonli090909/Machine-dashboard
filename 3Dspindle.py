"""Interactive 3D spindle and toolpath view for the CNC dashboard."""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
import streamlit as st


MOTION_TYPES = {"RAPID", "CUT"}


def _path_segments(program: list[dict[str, Any]], motion_type: str) -> tuple[list, list, list]:
    """Return line coordinates for all program moves of one type."""
    position = {"x": 0.0, "y": 0.0, "z": 0.0}
    xs: list[float | None] = []
    ys: list[float | None] = []
    zs: list[float | None] = []
    for operation in program:
        target = operation.get("target")
        if target is None:
            continue
        if operation["type"] == motion_type:
            xs.extend([position["x"], target["x"], None])
            ys.extend([position["y"], target["y"], None])
            zs.extend([position["z"], target["z"], None])
        position = target
    return xs, ys, zs


def _completed_path(program: list[dict[str, Any]], operation_index: int,
                    current: dict[str, float]) -> tuple[list[float], list[float], list[float]]:
    points = [{"x": 0.0, "y": 0.0, "z": 0.0}]
    for index, operation in enumerate(program):
        if index >= operation_index:
            break
        if operation.get("target") is not None:
            points.append(operation["target"])
    if operation_index < len(program) and program[operation_index].get("target") is not None:
        points.append(current)
    return ([point["x"] for point in points],
            [point["y"] for point in points],
            [point["z"] for point in points])


def _add_box(figure: go.Figure, bounds: tuple[float, float, float, float, float, float]) -> None:
    """Add a translucent rectangular workpiece."""
    x0, x1, y0, y1, z0, z1 = bounds
    x = [x0, x1, x1, x0, x0, x1, x1, x0]
    y = [y0, y0, y1, y1, y0, y0, y1, y1]
    z = [z0, z0, z0, z0, z1, z1, z1, z1]
    figure.add_trace(go.Mesh3d(
        x=x, y=y, z=z,
        i=[0, 0, 0, 4, 4, 4, 0, 1, 2, 3, 0, 1],
        j=[1, 2, 3, 5, 6, 7, 1, 2, 3, 0, 4, 5],
        k=[2, 3, 7, 6, 7, 3, 5, 6, 7, 4, 5, 6],
        color="#64748b", opacity=0.18, flatshading=True,
        name="Workpiece", hoverinfo="skip", showlegend=False,
    ))


def render_3d_spindle(simulator: Any, machine_config: dict[str, Any],
                      program: list[dict[str, Any]]) -> None:
    """Render the dashboard's full-width 3D motion module."""
    state = simulator.state
    current = {axis: float(state[f"{axis}_position"]) for axis in "xyz"}

    st.subheader("3D Spindle Motion")
    control_col, info_col = st.columns([1, 2])
    with control_col:
        show_path = st.toggle("Show full toolpath", value=True, key="spindle_3d_show_path")
    with info_col:
        operation = program[min(simulator.operation_index, len(program) - 1)]["type"]
        st.caption(
            f"Operation {simulator.operation_index + 1}/{len(program)} · {operation} · "
            f"{state['current_tool']} — {state['tool_name']}"
        )

    figure = go.Figure()
    _add_box(figure, (80, 220, 30, 170, -35, -5))

    if show_path:
        for motion_type, color, dash in (
            ("RAPID", "#22d3ee", "dash"),
            ("CUT", "#55e6ad", "solid"),
        ):
            x, y, z = _path_segments(program, motion_type)
            figure.add_trace(go.Scatter3d(
                x=x, y=y, z=z, mode="lines", name=f"{motion_type.title()} path",
                line={"color": color, "width": 4, "dash": dash}, opacity=0.42,
                hoverinfo="skip",
            ))

    completed_x, completed_y, completed_z = _completed_path(
        program, simulator.operation_index, current
    )
    figure.add_trace(go.Scatter3d(
        x=completed_x, y=completed_y, z=completed_z, mode="lines",
        name="Completed motion", line={"color": "#f8fafc", "width": 6},
        hoverinfo="skip",
    ))

    # The tool tip is the simulated XYZ position; the short shaft makes Z motion legible.
    shaft_top = current["z"] + 35
    figure.add_trace(go.Scatter3d(
        x=[current["x"], current["x"]],
        y=[current["y"], current["y"]],
        z=[current["z"], shaft_top],
        mode="lines", name="Spindle",
        line={"color": "#cbd5e1", "width": 12}, hoverinfo="skip",
    ))
    figure.add_trace(go.Scatter3d(
        x=[current["x"]], y=[current["y"]], z=[current["z"]],
        mode="markers", name="Tool tip",
        marker={"size": 7, "color": "#fbbf24", "symbol": "diamond"},
        hovertemplate="X %{x:.3f}<br>Y %{y:.3f}<br>Z %{z:.3f} mm<extra></extra>",
    ))

    axis_style = {
        "backgroundcolor": "#0b1220", "gridcolor": "#25344d",
        "zerolinecolor": "#475569", "showbackground": True,
    }
    figure.update_layout(
        height=600,
        margin={"l": 0, "r": 0, "t": 12, "b": 0},
        paper_bgcolor="#111c2e",
        font={"color": "#e5e7eb"},
        legend={"orientation": "h", "y": 1.02, "x": 0},
        uirevision="cnc-spindle-camera-v1",
        scene={
            "xaxis": {**axis_style, "title": "X (mm)", "range": [-20, 260]},
            "yaxis": {**axis_style, "title": "Y (mm)", "range": [-20, 210]},
            "zaxis": {**axis_style, "title": "Z (mm)", "range": [-65, 45]},
            "aspectmode": "manual",
            "aspectratio": {"x": 1.35, "y": 1.0, "z": 0.65},
            "camera": {"eye": {"x": 1.55, "y": 1.55, "z": 1.05}},
        },
    )
    st.plotly_chart(
        figure, use_container_width=True, key="spindle_3d_chart",
        config={"displaylogo": False, "scrollZoom": True},
    )
    st.caption(
        f"X {current['x']:+09.3f} mm  ·  Y {current['y']:+09.3f} mm  ·  "
        f"Z {current['z']:+09.3f} mm  ·  Feed {state['feed_rate']:,.0f} mm/min  ·  "
        f"Spindle {state['spindle_rpm']:,.0f} rpm"
    )
