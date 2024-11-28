from locust import HttpUser, between, task, LoadTestShape
import random

class UserBehavior(HttpUser):
    wait_time = between(1, 2)  # Fast wait times to simulate quick adaptation

    @task
    def dynamic_load_task(self):
        # Randomly simulate different API endpoints or parameters
        endpoint = random.choice(["/api/v1/resource", "/api/v1/update"])
        self.client.get(endpoint)

class PeriodicLoad(LoadTestShape):
    """
    Rapid load fluctuation pattern for SAC.
    """
    stages = [
        (10, 10, 5),   # Ramp up to 10 users in 10 seconds
        (10, 100, 10),  # Ramp up to 100 users in 10 seconds
        (10, 50, 20),   # Ramp down to 50 users quickly
        (10, 0, 10)     # Ramp down to 0 users quickly
    ]

    def tick(self):
        run_time = self.get_run_time()
        for duration, user_count, spawn_rate in self.stages:
            if run_time < duration:
                return user_count, spawn_rate
            run_time -= duration
        return None
