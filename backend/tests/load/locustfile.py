"""
Locust load test for the MetroPulse API (health and India Twin read paths).

Usage:
  locust -f tests/load/locustfile.py --host=http://localhost:8000
"""
from locust import FastHttpUser, between, task


class TwinReader(FastHttpUser):
    wait_time = between(1, 5)

    @task(1)
    def health(self):
        self.client.get("/api/health", name="health")

    @task(3)
    def indicators(self):
        self.client.get("/api/twin/indicators", name="twin indicators")

    @task(3)
    def resolve_place(self):
        self.client.get("/api/twin/places/resolve", params={"q": "Pune"}, name="twin resolve")
