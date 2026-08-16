"""A small, waypoint-based machining program (not a G-code parser)."""

PROGRAM_NAME = "PART_A_001.NC"

# Z=0 is the top of travel, so safe moves use Z=-20 and cuts use lower values.
CNC_PROGRAM = [
    {"type": "RAPID", "target": {"x": 100, "y": 50, "z": -20}},
    {"type": "SPINDLE_ON", "spindle_rpm": 8_500, "duration": 1.5},
    {"type": "RAPID", "target": {"x": 100, "y": 50, "z": -5}},
    {"type": "CUT", "target": {"x": 100, "y": 50, "z": -15}, "feed_rate": 600, "spindle_rpm": 8_500},
    {"type": "CUT", "target": {"x": 200, "y": 50, "z": -15}, "feed_rate": 1_200, "spindle_rpm": 8_500},
    {"type": "CUT", "target": {"x": 200, "y": 150, "z": -15}, "feed_rate": 1_200, "spindle_rpm": 8_500},
    {"type": "CUT", "target": {"x": 100, "y": 150, "z": -15}, "feed_rate": 1_200, "spindle_rpm": 8_500},
    {"type": "CUT", "target": {"x": 100, "y": 50, "z": -15}, "feed_rate": 1_200, "spindle_rpm": 8_500},
    {"type": "RAPID", "target": {"x": 100, "y": 50, "z": -40}},
    {"type": "TOOL_CHANGE", "tool": "T05", "tool_name": "10 mm End Mill", "duration": 3.0},
    {"type": "SPINDLE_ON", "spindle_rpm": 9_200, "duration": 1.0},
    {"type": "RAPID", "target": {"x": 150, "y": 100, "z": -8}},
    {"type": "CUT", "target": {"x": 150, "y": 100, "z": -30}, "feed_rate": 500, "spindle_rpm": 9_200},
    {"type": "DWELL", "duration": 1.5},
    {"type": "RAPID", "target": {"x": 150, "y": 100, "z": -40}},
    {"type": "SPINDLE_OFF", "duration": 1.0},
    {"type": "RAPID", "target": {"x": 0, "y": 0, "z": 0}},
    {"type": "END_CYCLE"},
]


def estimate_cycle_seconds() -> float:
    """Estimate ideal duration from distances and programmed feeds."""
    position = {"x": 0.0, "y": 0.0, "z": 0.0}
    seconds = 0.0
    for operation in CNC_PROGRAM:
        if "target" in operation:
            target = operation["target"]
            distance = sum((target[a] - position[a]) ** 2 for a in "xyz") ** 0.5
            rate = operation.get("feed_rate", 8_000)
            seconds += distance / rate * 60
            position = target.copy()
        seconds += operation.get("duration", 0.0)
    return seconds

