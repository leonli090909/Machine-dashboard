# Industrial Machine Dashboard V1

An educational Streamlit application that simulates and visualizes one 3-axis CNC vertical machining center: **CNC-01**. It demonstrates deterministic machine motion, related industrial sensor readings, alarm lifecycles, production KPIs, OEE, and in-memory historical trends.

## Project structure

- `app.py` — Streamlit controls and dashboard
- `simulator.py` — machine state, motion interpolation, sensors, and history
- `cnc_program.py` — predefined machining operations and waypoints
- `calculations.py` — OEE calculation
- `alarms.py` — threshold rules and alarm lifecycle
- `config.py` — travel limits, thresholds, and constants

## How the simulator works

The machine follows a predefined operation list containing rapid moves, cuts, spindle commands, a dwell, a tool change, and cycle completion. Axis coordinates are interpolated from the current position to each target based on feed rate. Spindle load is derived from RPM, feed, and cutting state; load drives gradual heating, while cutting also raises vibration. Small sensor noise adds realism without randomizing the programmed motion.

History stays in a Pandas DataFrame for the latest 30 simulated minutes. Alarm records are created once when a condition becomes active and marked inactive when it clears. OEE is calculated as Availability × Performance × Quality.

## Install and run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Use **Start Cycle** in the sidebar. Choose 1x, 5x, or 10x speed, pause/resume the cycle, adjust normal feed/RPM overrides, or reset the simulation.
