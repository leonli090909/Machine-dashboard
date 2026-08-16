"""Configuration for the simulated CNC machine."""

MACHINE_CONFIG = {
    "machine_id": "CNC-01",
    "machine_name": "3-Axis Vertical Machining Center",
    "x_min": 0.0,
    "x_max": 800.0,
    "y_min": 0.0,
    "y_max": 500.0,
    "z_min": -500.0,
    "z_max": 0.0,
    "max_spindle_rpm": 12_000,
    "max_feed_mm_min": 10_000,
    "rapid_rate_mm_min": 8_000,
    "spindle_load_warning": 85.0,
    "spindle_load_critical": 100.0,
    "spindle_temp_warning": 65.0,
    "spindle_temp_critical": 75.0,
    "vibration_warning": 4.5,
    "vibration_critical": 7.0,
    "coolant_temp_warning": 35.0,
    "coolant_temp_critical": 45.0,
    "ambient_temperature": 24.0,
    "ideal_cycle_time_seconds": 60.0,
}

HISTORY_COLUMNS = [
    "timestamp", "status", "x_position", "y_position", "z_position",
    "spindle_rpm", "feed_rate", "spindle_load", "spindle_temperature",
    "coolant_temperature", "vibration", "parts_completed", "parts_rejected",
]

