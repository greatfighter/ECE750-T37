from locust import HttpUser, task, between, LoadTestShape
import random


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
            print("Failed to create order:", response.text)


class RandomLoadShape(LoadTestShape):
    """
    A load shape to generate random RPS patterns where RPS follows U{5,10,15,20}.
    """
    step_time = 30  # Change RPS every 30 seconds
    max_duration = 900  # Total test duration (e.g., 5 minutes)

    def tick(self):
        """
        Adjust user count dynamically to match randomly generated RPS values.
        """
        run_time = self.get_run_time()

        # End the test after max_duration
        if run_time > self.max_duration:
            return None

        # Generate random RPS (U{5, 10, 15, 20})
        random_rps = random.choice([25, 50, 5, 125, 10, 15, 30])

        # Calculate the required number of users to achieve the target RPS
        # Each user generates ~1 request/second due to wait_time (1–2 sec)
        user_count = random_rps

        return user_count, user_count  # Spawn rate matches the user count
