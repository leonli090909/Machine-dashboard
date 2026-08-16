"""Understandable production KPI calculations."""


def calculate_oee(runtime: float, planned_time: float, completed: int,
                  rejected: int, ideal_cycle_time: float) -> dict[str, float]:
    """Return Availability, Performance, Quality, and OEE as 0..1 ratios."""
    availability = min(1.0, runtime / planned_time) if planned_time > 0 else 0.0
    total = completed + rejected
    theoretical = runtime / ideal_cycle_time if ideal_cycle_time > 0 else 0.0
    performance = min(1.0, total / theoretical) if theoretical > 0 else 0.0
    quality = completed / total if total else 1.0
    return {
        "availability": availability,
        "performance": performance,
        "quality": quality,
        "oee": availability * performance * quality,
    }

