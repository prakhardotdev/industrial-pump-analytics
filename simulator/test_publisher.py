
import json
import sys
import time
import uuid
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "synoquant/factory-01/pump-01/telemetry"


def build_payload(
    temperature=62.5,
    vibration=2.1,
    flow=45.0,
    pressure=3.2,
):
    return {
        "event_id": str(uuid.uuid4()),
        "asset_id": "PUMP-001",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "temperature_c": temperature,
        "vibration_mm_s": vibration,
        "pressure_bar": pressure,
        "flow_rate_m3_h": flow,
        "motor_current_a": 12.5,
        "energy_kwh": 0.25,
    }


def publish_payload(client, payload):
    info = client.publish(TOPIC, json.dumps(payload), qos=1)
    info.wait_for_publish(timeout=5)

    if not info.is_published():
        raise RuntimeError("MQTT publish did not complete")


def main():
    mode = sys.argv[1].lower() if len(sys.argv) > 1 else "normal"

    valid_modes = {
        "normal",
        "high_temp",
        "critical_temp",
        "high_vibration",
        "low_flow",
        "pressure_anomaly",
        "duplicate",
    }

    if mode not in valid_modes:
        raise ValueError(f"Choose one of: {', '.join(sorted(valid_modes))}")

    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"pump-test-{uuid.uuid4().hex[:8]}",
    )

    try:
        client.connect(BROKER, PORT, keepalive=60)
        client.loop_start()

        if mode == "duplicate":
            payload = build_payload()
            print("Publishing the same event twice...")
            publish_payload(client, payload)
            time.sleep(1)
            publish_payload(client, payload)
            print("Duplicate test messages published.")

        elif mode in (
            "high_temp",
            "critical_temp",
            "high_vibration",
            "low_flow",
            "pressure_anomaly",
        ):
            for i in range(3):
                if mode == "high_temp":
                    payload = build_payload(temperature=80.0)
                elif mode == "critical_temp":
                    payload = build_payload(temperature=90.0)
                elif mode == "high_vibration":
                    payload = build_payload(vibration=8.0)
                elif mode == "low_flow":
                    payload = build_payload(flow=10.0)
                else:
                    payload = build_payload(pressure=7.0)

                publish_payload(client, payload)
                print(f"Published reading {i + 1}/3: {mode}")
                time.sleep(2.5)

            print("Three test readings published.")

        else:
            publish_payload(client, build_payload())
            print("Normal test reading published.")

    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
