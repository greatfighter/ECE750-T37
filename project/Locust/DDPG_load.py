from locust import HttpUser, between, task, LoadTestShape
import random

class UserBehavior(HttpUser):
    wait_time = between(0.5, 1)  # Shorter wait time for higher throughput

    @task
    def high_concurrency_task(self):
        # Simulate high concurrency API calls with slightly different paths
        endpoint = random.choice(["/api/v1/process", "/api/v1/submit"])
        self.client.get(endpoint)

class PeriodicLoad(LoadTestShape):
    """
    High concurrency load for DDPG to maximize throughput.
    """
    stages = [
        (20, 50, 10),  # Ramp up to 50 users in 20 seconds
        (20, 150, 15), # Ramp up to 150 users quickly
        (20, 200, 25), # Keep the load at 200 users
        (20, 50, 10),  # Ramp down to 50 users
        (20, 0, 5)     # Ramp down to 0 users
    ]

    def tick(self):
        run_time = self.get_run_time()
        for duration, user_count, spawn_rate in self.stages:
            if run_time < duration:
                return user_count, spawn_rate
            run_time -= duration
        return None
