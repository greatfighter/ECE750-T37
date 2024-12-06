from locust import HttpUser, task, constant, LoadTestShape
import os
import sys
from locust.main import main

# Set a fixed random seed for reproducibility
import random
random.seed(42)

class UserBehavior(HttpUser):
    wait_time = constant(1.5)  # Fixed wait time for consistent load
    # Replace with your actual host URL
    host = "http://istio-ingressgateway-istio-system.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud/"

    @task
    def simulate_order_interactions(self):
        """
        Simulate interactions with the 'orders' service:
        1. Creating a new order (POST /)
        2. Fetching the created order by ID (GET /{id})
        """
        order_data = {
            "creditCard": "4111111111111111",
            "product": "Product A",
            "customer": "Customer A"
        }
        response = self.client.post("/", json=order_data)

        if response.status_code == 201:
            order_id = response.json().get('id')
            self.client.get(f"/{order_id}")
        else:
            print("Failed to create order:", response.text)

class DeterministicLoadShape(LoadTestShape):
    step_time = 30  # Step time for changing load
    max_duration = 10800  # Max test duration (in seconds)
    rps_sequence = [25, 50, 5, 125, 10, 15, 30]  # Predefined sequence of RPS
    current_index = 0

    def tick(self):
        run_time = self.get_run_time()

        if run_time > self.max_duration:
            return None

        target_rps = self.rps_sequence[self.current_index]
        user_count = target_rps

        if run_time // self.step_time > self.current_index:
            self.current_index = (self.current_index + 1) % len(self.rps_sequence)

        return user_count, user_count

if __name__ == "__main__":
    # Configure CSV output
    csv_prefix = "deterministic_test_results"
    os.environ["LOCUST_CSV"] = csv_prefix

    # Run Locust in headless mode and export CSV results
    sys.argv.extend([
        "--headless",
        "--csv", csv_prefix,  # Specify prefix for CSV files
        "-u", "100",  # Total number of users
        "-r", "10",   # Spawn rate (users per second)
        "-t", "3h"    # Test duration (3 hours)
    ])

    # Run the Locust test
    main()
