from locust import HttpUser, between, task, LoadTestShape
import uuid

class UserBehavior(HttpUser):
    wait_time = between(5, 10)  # Simulate low concurrency with a 5-10 second wait time

    # Target the orders service via service discovery or Istio
    # host = "http://orders-group-4.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud"
    # host = "http://41e441d4-ca-tor.lb.appdomain.cloud"
    host = "http://istio-ingressgateway-istio-system.mycluster-ca-tor-2-bx2-4x-04e8c71ff333c8969bc4cbc5a77a70f6-0000.ca-tor.containers.appdomain.cloud/"
    # Optionally, add any headers required for authentication or service communication
    # headers = {
    #     "Authorization": "Bearer sha256~wpuBTcaPF5B9y1eGp9lBVhWOXnhrRwtdAK-nMOtRgYo"  # Replace with actual JWT token if needed
    # }

    @task
    def simulate_order_interactions(self):
        """
        Simulate basic interactions with the 'orders' service:
        1. Creating a new order (POST /)
        2. Fetching the created order by ID (GET /{id})
        """
        # Simulate creating a new order (POST /)
        order_data = {
            "creditCard": "4111111111111111",
            "product": "Product A",
            "customer": "Customer A"
        }
        response = self.client.post("/", json=order_data)

        # Check if the POST request was successful and capture the created order ID
        if response.status_code == 201:
            order_id = response.json().get('id')  # Assuming the response contains the order ID

            # Fetch the created order using the returned ID (GET /{id})
            self.client.get(f"/{order_id}")

        else:
            print("Failed to create order:", response.text)

class PeriodicLoad(LoadTestShape):
    """
    Defines a low-concurrency load shape suitable for testing environments with service mesh like Istio.
    """
    stages = [
        (60, 50, 1),  # Ramp up to 5 users over 60 seconds
        (60, 100, 1), # Ramp up to 10 users
        (60, 10, 1),  # Maintain 10 users for 60 seconds
        (60, 0, 1)    # Ramp down to 0 users
    ]

    def tick(self):
        """
        Determines the number of users and spawn rate for each stage of the load test.
        """
        run_time = self.get_run_time()
        for duration, user_count, spawn_rate in self.stages:
            if run_time < duration:
                return user_count, spawn_rate
            run_time -= duration
        return None
