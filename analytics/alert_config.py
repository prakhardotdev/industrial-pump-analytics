
# SIMULATION ONLY — NOT VALIDATED INDUSTRIAL LIMITS

ALERT_CONFIG = {
    "HIGH_TEMPERATURE": {
        "warning": 75.0,
        "critical": 85.0,
        "recovery": 70.0,
        "persistence": 3,
    },
    "HIGH_VIBRATION": {
        "warning": 4.0,
        "critical": 7.0,
        "recovery": 3.5,
        "persistence": 3,
    },
    "LOW_FLOW": {
        "minimum": 20.0,
        "recovery": 22.0,
        "persistence": 3,
    },
    "PRESSURE_ANOMALY": {
        "minimum": 1.0,
        "maximum": 6.0,
        "recovery_minimum": 1.2,
        "recovery_maximum": 5.8,
        "persistence": 3,
    },
    "STALE_TELEMETRY": {
        "freshness_seconds": 60,
    },
}





