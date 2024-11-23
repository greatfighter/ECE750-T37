from locust import HttpUser, task, between, LoadTestShape
import random
import math


class UserBehavior(HttpUser):
    wait_time = between(1, 2)  # Minimal wait time to simulate higher concurrency
    host = "http://istio-ingressgateway-istio-system.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud/"

    @task
    def simulate_order_interactions(self):
        """
        Simulate interactions with the 'orders' service:
        1. Creating a new order (POST /)
        2. Fetching the created order by ID (GET /{id})
        """
        # Create a new order
        order_data = {
            "creditCard": "4111111111111111",
            "product": "Product A",
            "customer": "Customer A"
        }
        response = self.client.post("/", json=order_data)

        if response.status_code == 201:
            # Fetch the created order
            order_id = response.json().get('id')
            self.client.get(f"/{order_id}")
        else:
            print(f"Failed to create order. Status code: {response.status_code}, Response: {response.text}")


class SinusoidalLoadShape(LoadTestShape):
    """
    A load shape to generate a sinusoidal RPS pattern.
    """
    step_time = 1  # Adjust RPS every second to create a smooth sinusoidal pattern
    max_duration = 900  # Total test duration (e.g., 15 minutes)
    T = 60  # Period in seconds (adjustable, e.g., 60s for one full sinusoidal cycle)
    phi = random.uniform(0, 2 * math.pi)  # Random phase shift to vary the pattern

    def tick(self):
        """
        Adjust user count dynamically to match sinusoidal RPS values.
        """
        run_time = self.get_run_time()

        # End the test after max_duration
        if run_time > self.max_duration:
            return None

        # Apply the sinusoidal formula for RPS:
        # l_i(t) = 12.5 + 7.5 * sin(2π * t / T + φ)
        rps = 12.5 + 7.5 * math.sin(2 * math.pi * run_time / self.T + self.phi)

        # Ensure RPS is non-negative and round to the nearest integer
        rps = max(0, round(rps))

        # Calculate the required number of users to achieve the target RPS
        user_count = rps

        return user_count, user_count  # Spawn rate matches the user count
