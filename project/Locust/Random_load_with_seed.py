from locust import HttpUser, task, constant, LoadTestShape
import random

# Set a fixed random seed for reproducibility
random.seed(42)

class UserBehavior(HttpUser):
    wait_time = constant(1.5)  # Fixed wait time for consistent load
    # host = "http://istio-ingressgateway-istio-system.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud/"
    host = "http://istio-ingressgateway-istio-system.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud/"  

    @task
    def simulate_order_interactions(self):
        # Fixed payload for order creation
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
    step_time = 30
    max_duration = 10800
    rps_sequence = [25, 50, 5, 125, 10, 15, 30]  # Predefined sequence
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
