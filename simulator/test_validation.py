
import json
import uuid
import time
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "synoquant/factory-01/pump-01/telemetry"

def make_payload():
    return {
        "event_id": str(uuid.uuid4()),
        "asset_id": "PUMP-001",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": 62.5,
        "vibration_mm_s": 2.1,
        "pressure_bar": 3.2,
        "flow_rate_m3_h": 45.0,
        "motor_current_a": 12.5,
        "energy_kwh": 0.25,
    }

def main():
    tests = [
        ("Negative vibration", {"vibration_mm_s": -5}),
        ("NaN temperature", {"temperature_c": "NaN"}),
        ("Unknown pump", {"asset_id": "PUMP-999"}),
    ]

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="pump-validation-test",
    )

    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_start()

        for name, changes in tests:
            payload = make_payload()
            payload.update(changes)

            info = client.publish(
                TOPIC,
                json.dumps(payload, allow_nan=False),
                qos=1,
            )
            info.wait_for_publish(timeout=5)

            if not info.is_published():
                raise RuntimeError(f"Publish failed: {name}")

            print(f"Published test: {name}")
            time.sleep(1)

    finally:
        client.loop_stop()
        client.disconnect()

if __name__ == "__main__":
    main()
