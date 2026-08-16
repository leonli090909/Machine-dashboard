"""Alarm rules and lifecycle management."""
from datetime import datetime

from config import MACHINE_CONFIG


class AlarmManager:
    def __init__(self) -> None:
        self.alarms: dict[str, dict] = {}

    def _set(self, alarm_id: str, active: bool, severity: str,
             source: str, message: str, timestamp: datetime) -> None:
        existing = self.alarms.get(alarm_id)
        if active and (not existing or not existing["active"]):
            self.alarms[alarm_id] = {
                "alarm_id": alarm_id, "timestamp": timestamp.isoformat(timespec="seconds"),
                "severity": severity, "source": source, "message": message, "active": True,
            }
        elif existing and not active:
            existing["active"] = False

    def evaluate(self, state: dict) -> list[dict]:
        c, now = MACHINE_CONFIG, state["timestamp"]
        rules = [
            ("A001", state["spindle_load"] > c["spindle_load_warning"], "WARNING", "Spindle", "Spindle load is high"),
            ("A002", state["spindle_load"] > c["spindle_load_critical"], "CRITICAL", "Spindle", "Spindle load is critical"),
            ("A003", state["spindle_temperature"] > c["spindle_temp_warning"], "WARNING", "Spindle", "Spindle temperature is high"),
            ("A004", state["spindle_temperature"] > c["spindle_temp_critical"], "CRITICAL", "Spindle", "Spindle temperature is critical"),
            ("A005", state["vibration"] > c["vibration_warning"], "WARNING", "Spindle", "Vibration is high"),
            ("A006", state["vibration"] > c["vibration_critical"], "CRITICAL", "Spindle", "Vibration is critical"),
            ("A007", not self._inside_travel(state), "CRITICAL", "Axis", "Axis position is outside travel limits"),
        ]
        for rule in rules:
            self._set(*rule, now)
        return [alarm for alarm in self.alarms.values() if alarm["active"]]

    @staticmethod
    def _inside_travel(state: dict) -> bool:
        c = MACHINE_CONFIG
        return (c["x_min"] <= state["x_position"] <= c["x_max"] and
                c["y_min"] <= state["y_position"] <= c["y_max"] and
                c["z_min"] <= state["z_position"] <= c["z_max"])

