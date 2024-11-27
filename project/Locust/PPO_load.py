from locust import HttpUser, between, task, LoadTestShape

class UserBehavior(HttpUser):
    wait_time = between(3, 5)  # Longer wait times for stable, slower traffic

    @task
    def stable_load_task(self):
        # Simulate stable API calls
        self.client.get("/api/v1/status")
        self.client.get("/api/v1/data")

class PeriodicLoad(LoadTestShape):
    """
    Stable load pattern for PPO.
    """
    stages = [
        (30, 20, 5),   # Ramp up to 20 users over 30 seconds
        (30, 50, 5),   # Steady at 50 users for 30 seconds
        (30, 50, 5),   # Keep steady at 50 users
        (30, 0, 5)     # Ramp down to 0 users
    ]

    def tick(self):
        run_time = self.get_run_time()
        for duration, user_count, spawn_rate in self.stages:
            if run_time < duration:
                return user_count, spawn_rate
            run_time -= duration
        return None
