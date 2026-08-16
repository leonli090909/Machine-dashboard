"""Stateful CNC machining simulation."""
from __future__ import annotations

from datetime import datetime, timedelta
import math
import random

import pandas as pd

from alarms import AlarmManager
from cnc_program import CNC_PROGRAM, PROGRAM_NAME, estimate_cycle_seconds
from config import HISTORY_COLUMNS, MACHINE_CONFIG


class CNCSimulator:
    """Advance a deterministic program while deriving realistic sensor values."""

    def __init__(self) -> None:
        self.alarms = AlarmManager()
        self.reset()

    def reset(self) -> None:
        ambient = MACHINE_CONFIG["ambient_temperature"]
        self.simulation_time = datetime.now().replace(microsecond=0)
        self.state = {
            "timestamp": self.simulation_time, "status": "IDLE",
            "x_position": 0.0, "y_position": 0.0, "z_position": 0.0,
            "spindle_rpm": 0.0, "feed_rate": 0.0, "spindle_load": 0.0,
            "spindle_temperature": ambient, "coolant_temperature": ambient,
            "vibration": 0.15, "current_tool": "T01", "tool_name": "Face Mill",
            "program_name": PROGRAM_NAME, "cycle_time_seconds": 0.0,
            "cycle_progress": 0.0, "parts_completed": 0, "parts_rejected": 0,
        }
        self.running = False
        self.paused = False
        self.powered_on = True
        self.operation_index = 0
        self.operation_elapsed = 0.0
        self.runtime_seconds = 0.0
        self.planned_seconds = 0.0
        self.history = pd.DataFrame(columns=HISTORY_COLUMNS)
        self.active_alarms: list[dict] = []
        self.estimated_cycle_seconds = estimate_cycle_seconds()
        self.alarms = AlarmManager()
        self._record_history()

    def start_cycle(self) -> None:
        if self.powered_on and not self.running:
            self.running = True
            self.paused = False
            self.operation_index = 0
            self.operation_elapsed = 0.0
            self.state["cycle_time_seconds"] = 0.0

    def toggle_pause(self) -> None:
        if self.running:
            self.paused = not self.paused

    def set_power(self, powered_on: bool) -> None:
        """Power the machine on or place it in the safe OFF state."""
        self.powered_on = powered_on
        if not powered_on:
            self.running = False
            self.paused = False
            self.state.update(status="OFF", spindle_rpm=0.0, feed_rate=0.0)
        elif self.state["status"] == "OFF":
            self.state["status"] = "IDLE"

    def tick(self, seconds: float = 1.0, spindle_override: float = 1.0,
             feed_override: float = 1.0) -> None:
        seconds = max(0.0, min(seconds, 10.0))
        self.simulation_time += timedelta(seconds=seconds)
        self.state["timestamp"] = self.simulation_time
        self.planned_seconds += seconds

        if not self.powered_on:
            self.state.update(status="OFF", spindle_rpm=0.0, feed_rate=0.0)
        elif self.paused:
            self.state.update(status="IDLE", feed_rate=0.0)
            self._decelerate_spindle(seconds)
        elif self.running:
            self.runtime_seconds += seconds
            self.state["cycle_time_seconds"] += seconds
            self._run_program(seconds, spindle_override, feed_override)
        else:
            self.state.update(status="IDLE", spindle_rpm=0.0, feed_rate=0.0)

        self._update_sensors(seconds)
        self.active_alarms = self.alarms.evaluate(self.state)
        if any(a["severity"] == "CRITICAL" for a in self.active_alarms):
            self.state.update(status="ALARM", feed_rate=0.0, spindle_rpm=0.0)
            self.paused = True
        self._record_history()

    def _run_program(self, seconds: float, spindle_override: float, feed_override: float) -> None:
        remaining = seconds
        while remaining > 1e-6 and self.running:
            operation = CNC_PROGRAM[self.operation_index]
            consumed = self._execute(operation, remaining, spindle_override, feed_override)
            remaining -= consumed
            if consumed <= 1e-9:
                self._next_operation()

        self.state["cycle_progress"] = min(100.0, 100 * self.state["cycle_time_seconds"] / self.estimated_cycle_seconds)

    def _execute(self, op: dict, available: float, spindle_override: float, feed_override: float) -> float:
        kind = op["type"]
        if kind in {"RAPID", "CUT"}:
            self.state["status"] = "RAPID_MOVE" if kind == "RAPID" else "MACHINING"
            programmed_feed = MACHINE_CONFIG["rapid_rate_mm_min"] if kind == "RAPID" else op["feed_rate"]
            rate = programmed_feed * feed_override
            self.state["feed_rate"] = rate
            if kind == "CUT":
                self.state["spindle_rpm"] = op["spindle_rpm"] * spindle_override
            target = op["target"]
            delta = {a: target[a] - self.state[f"{a}_position"] for a in "xyz"}
            distance = math.sqrt(sum(value * value for value in delta.values()))
            if distance < 1e-6:
                return 0.0
            move_time = distance / rate * 60
            used = min(available, move_time)
            fraction = used / move_time
            for axis in "xyz":
                self.state[f"{axis}_position"] += delta[axis] * fraction
            if used >= move_time - 1e-9:
                self._next_operation()
            return used

        if kind == "END_CYCLE":
            self.state["parts_completed"] += 1
            self.running = False
            self.state.update(status="IDLE", cycle_progress=100.0, feed_rate=0.0, spindle_rpm=0.0)
            return available

        duration = op.get("duration", 0.0)
        status = {"TOOL_CHANGE": "TOOL_CHANGE", "DWELL": "MACHINING",
                  "SPINDLE_ON": "SETUP", "SPINDLE_OFF": "SETUP"}[kind]
        self.state.update(status=status, feed_rate=0.0)
        if kind == "SPINDLE_ON":
            self.state["spindle_rpm"] = op["spindle_rpm"] * spindle_override
        elif kind == "SPINDLE_OFF":
            self._decelerate_spindle(available)
        elif kind == "TOOL_CHANGE":
            self.state.update(spindle_rpm=0.0, current_tool=op["tool"], tool_name=op["tool_name"])
        used = min(available, max(0.0, duration - self.operation_elapsed))
        self.operation_elapsed += used
        if self.operation_elapsed >= duration - 1e-9:
            self._next_operation()
        return used

    def _next_operation(self) -> None:
        self.operation_index = min(self.operation_index + 1, len(CNC_PROGRAM) - 1)
        self.operation_elapsed = 0.0

    def _decelerate_spindle(self, seconds: float) -> None:
        self.state["spindle_rpm"] = max(0.0, self.state["spindle_rpm"] - 3_000 * seconds)

    def _update_sensors(self, seconds: float) -> None:
        machining = self.state["status"] == "MACHINING" and self.state["feed_rate"] > 0
        rpm_ratio = self.state["spindle_rpm"] / MACHINE_CONFIG["max_spindle_rpm"]
        feed_ratio = self.state["feed_rate"] / MACHINE_CONFIG["max_feed_mm_min"]
        base_load = (12 * rpm_ratio + 48 * feed_ratio + (36 if machining else 0))
        self.state["spindle_load"] = max(0.0, base_load + random.uniform(-2.0, 2.0))
        target_temp = MACHINE_CONFIG["ambient_temperature"] + self.state["spindle_load"] * 0.48
        response = min(1.0, seconds * (0.012 if machining else 0.006))
        self.state["spindle_temperature"] += (target_temp - self.state["spindle_temperature"]) * response
        coolant_target = MACHINE_CONFIG["ambient_temperature"] + (8 if machining else 0)
        self.state["coolant_temperature"] += (coolant_target - self.state["coolant_temperature"]) * min(1, seconds * 0.008)
        vibration = 0.15 + 0.7 * rpm_ratio + (1.2 + 1.8 * feed_ratio if machining else 0)
        self.state["vibration"] = max(0.0, vibration + random.uniform(-0.12, 0.12))

    def _record_history(self) -> None:
        row = {column: self.state[column] for column in HISTORY_COLUMNS}
        self.history.loc[len(self.history)] = row
        cutoff = self.simulation_time - timedelta(minutes=30)
        self.history = self.history[self.history["timestamp"] >= cutoff].reset_index(drop=True)
