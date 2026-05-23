"""
Locust load test for MetroPulse WebSocket simulation.

Usage:
  locust -f tests/load/locustfile.py --host=http://localhost:8000
"""
import json
import time
from locust import FastHttpUser, task, between


class SimulationUser(FastHttpUser):
    wait_time = between(5, 15)

    @task
    def run_simulation(self):
        payload = {
            "type": "START",
            "params": {
                "fdi": {"tech": -20, "manufacturing": 10, "realEstate": -5},
                "publicWorksZone": None,
                "horizonMonths": 6,
            },
        }

        start = time.time()
        with self.client.ws_connect("/ws/simulate") as ws:
            ws.send(json.dumps(payload))
            frames_received = 0
            done_received = False

            while frames_received < 6 and not done_received:
                message = ws.receive(timeout=10)
                if message is None:
                    break
                data = json.loads(message)
                if data.get("type") == "FRAME":
                    frames_received += 1
                elif data.get("type") == "DONE":
                    done_received = True

        elapsed = (time.time() - start) * 1000
        self.environment.events.request_success.fire(
            request_type="WS",
            name="simulation",
            response_time=elapsed,
            response_length=0,
        )
