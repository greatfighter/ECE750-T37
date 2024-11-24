import gymnasium as gym
from gymnasium import spaces
import numpy as np
import os
import pandas as pd
import random  # Simulate metric responses if no live data

class ServiceMeshEnv(gym.Env):
    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datasets_test")
    def __init__(self, action_type="continuous", lc1 = 0.5, lc2 = 0.5, epsilon=0.1, **kwargs):
        super(ServiceMeshEnv, self).__init__()
        
        # Configure action space based on type
        self.action_type = action_type
        if action_type == "discrete":
            # Discrete action space: adjust weights in increments
            self.action_space = spaces.Discrete(3)
        elif action_type == "continuous":
            # Continuous action space: adjust weights between [-1.0, 1.0] for two leaf services
            self.action_space = spaces.Box(low=np.array([-1.0, -1.0]), high=np.array([1.0, 1.0]), dtype=np.float32)
        else:
            raise ValueError("Invalid action_type. Choose 'discrete' or 'continuous'.")

        # Observation space: two sets of metrics (latency, CPU utilization, request rate) for two services
        self.observation_space = spaces.Box(low=0, high=1, shape=(6,), dtype=np.float32)
        
        # Initialize environment state
        self.service_data = self._load_data()
        self.current_indices = {service: 0 for service in self.service_data.keys()}
        self.state = self._get_metrics()  # Will return metrics for both services
        self.done = False
        self.traffic_weights = [0.5, 0.5]  # Initial traffic weights for two services
        self.lc1 = lc1
        self.lc2 = lc2
        # Track the number of requests for each service
        self.nr1 = 0  # Number of requests for service 1
        self.nr2 = 0  # Number of requests for service 2

        # Track the total number of requests
        self.total_requests = 0
        self.epsilon = epsilon  # Exploration probability
        self.epsilon = 1.0  # Initial epsilon value
        self.epsilon_min = 0.1  # Minimum epsilon value
        self.epsilon_decay = 0.995  # Decay rate for epsilon

    # def _load_data(self):
    #     """
    #     Load CSV files from each service subdirectory into a dictionary.
    #     """
    #     service_data = {}
    #     for service_name in os.listdir(self.data_dir):
    #         service_path = os.path.join(self.data_dir, service_name)
    #         if os.path.isdir(service_path):
    #             service_data[service_name] = {}
    #             for file in os.listdir(service_path):
    #                 metric_path = os.path.join(service_path, file)
    #                 if file.endswith(".csv"):
    #                     # Load the metric data and sort by timestamp
    #                     metric_name = file.replace(".csv", "")
    #                     df = pd.read_csv(metric_path)
    #                     df = df.sort_values(by="timestamp")
    #                     service_data[service_name][metric_name] = df.reset_index(drop=True)
    #     return service_data

    # def _get_metrics(self):
    #     """
    #     Retrieve the next row of metrics for each service.
    #     """
    #     state = []
    #     for service, metrics in self.service_data.items():
    #         for metric_name, df in metrics.items():
    #             idx = self.current_indices[service]
    #             if idx < len(df):
    #                 state.append(df.loc[idx, "value"])
    #             else:
    #                 state.append(0.0)  # Use 0.0 if no more data is available
    #     return np.array(state, dtype=np.float32)

    def _load_data(self):
        """
        Load CSV files from each service subdirectory into a dictionary with normalized values.
        """
        service_data = {}
        
        for service_name in os.listdir(self.data_dir):
            service_path = os.path.join(self.data_dir, service_name)
            if os.path.isdir(service_path):
                service_data[service_name] = {}
                
                for file in os.listdir(service_path):
                    metric_path = os.path.join(service_path, file)
                    if file.endswith(".csv"):
                        # Load the metric data and sort by timestamp
                        metric_name = file.replace(".csv", "")
                        df = pd.read_csv(metric_path)
                        df = df.sort_values(by="timestamp")
                        
                        # Apply normalization based on the metric type
                        if metric_name == "cpu_quota_used_percent_avg":
                            # Min-Max normalization for CPU
                            min_value = df["value"].min()
                            max_value = df["value"].max()
                            df["value"] = (df["value"] - min_value) / (max_value - min_value)
                        elif metric_name in ["net_http_request_time_max", "net_request_count_in_sum"]:
                            # Log transformation followed by Min-Max normalization for latency and RPS
                            df["log_value"] = np.log10(df["value"])
                            min_log_value = df["log_value"].min()
                            max_log_value = df["log_value"].max()
                            df["normalized_value"] = (df["log_value"] - min_log_value) / (max_log_value - min_log_value)
                            # Replace original "value" with normalized version
                            df["value"] = df["normalized_value"]
                            df.drop(columns=["log_value", "normalized_value"], inplace=True)
                            
                        # Store the normalized data
                        service_data[service_name][metric_name] = df.reset_index(drop=True)
        return service_data

    def _get_metrics(self):
        """
        Retrieve the next row of metrics for each service, considering normalization.
        """
        state = []
        for service, metrics in self.service_data.items():
            for metric_name, df in metrics.items():
                idx = self.current_indices[service]
                if idx < len(df):
                    state.append(df.loc[idx, "value"])
                    # Increment index for the next call
                    self.current_indices[service] += 1
                else:
                    state.append(0.0)  # Use 0.0 if no more data is available
        return np.array(state, dtype=np.float32)

    # def step(self, action):
    #     """
    #     Execute the action in the environment, observe the result, and compute the reward.
    #     """
    #     if self.action_type == "discrete":
    #         if action == 0:
    #             self._adjust_weights(0.1, -0.1)  # Shift weight towards the first service
    #         elif action == 1:
    #             self._adjust_weights(-0.1, 0.1)  # Shift weight towards the second service
    #         elif action == 2:
    #             self._equalize_traffic()

    #     elif self.action_type == "continuous":
    #         weight_adjust_a = action[0]  # Continuous value for adjusting weight of first service
    #         weight_adjust_b = action[1]  # Continuous value for adjusting weight of second service
    #         self._adjust_weights(weight_adjust_a, weight_adjust_b)

    #     self.state = self._get_metrics()  # Update state with metrics of both services
    #     reward = self._compute_reward(self.state)  # Calculate the reward based on the updated state
    #     self.done = self._check_done()

    #     return self.state, reward, self.done, False, {}

    def step(self, action):
        """
        Execute the action in the environment, observe the result, and compute the reward.
        """
        # Exploration vs exploitation decision for discrete action space
        if self.action_type == "discrete":
            if random.random() < self.epsilon:
                action = self.action_space.sample()  # Exploration: random action
            else:
                action = action  # Exploitation: action provided by policy

            if action == 0:
                self._adjust_weights(0.1, -0.1)  # Shift weight towards the first service
            elif action == 1:
                self._adjust_weights(-0.1, 0.1)  # Shift weight towards the second service
            elif action == 2:
                self._equalize_traffic()

        elif self.action_type == "continuous":
            if random.random() < self.epsilon:
                # Exploration: random continuous actions within the action space bounds
                weight_adjust_a = random.uniform(self.action_space.low[0], self.action_space.high[0])
                weight_adjust_b = random.uniform(self.action_space.low[1], self.action_space.high[1])
            else:
                # Exploitation: use provided action values
                weight_adjust_a = action[0]
                weight_adjust_b = action[1]

            self._adjust_weights(weight_adjust_a, weight_adjust_b)

        self.state = self._get_metrics()  # Update state with metrics of both services
        reward = self._compute_reward(self.state)  # Calculate the reward based on the updated state
        self.done = self._check_done()

        # Decay epsilon for exploration-exploitation tradeoff
        self._decay_epsilon()

        return self.state, reward, self.done, False, {}

    def _decay_epsilon(self):
        """
        Gradually reduce the exploration probability (epsilon) during training.
        """
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def reset(self, **kwargs):
        """
        Reset the environment for a new episode.
        """
        self.state = self._get_metrics()
        self.done = False
        self.traffic_weights = [0.5, 0.5]  # Reset weights to initial values
        self.nr1 = 0
        self.nr2 = 0
        return self.state, {}

    # def _compute_reward(self, state):
    #     """
    #     Compute reward based on throughput and latency for both services.
    #     """
    #     service1_latency, service1_cpu_util, service1_request_rate, service2_latency, service2_cpu_util, service2_request_rate = state
        
    #     # Reward for Service 1
    #     throughput1 = service1_request_rate  # Throughput for Service 1 (request rate)
    #     latency1 = service1_latency  # Latency (response time) for Service 1
    #     r1 = throughput1 - latency1  # Reward for Service 1 (maximize throughput, minimize latency)

    #     # Reward for Service 2
    #     throughput2 = service2_request_rate  # Throughput for Service 2 (request rate)
    #     latency2 = service2_latency  # Latency (response time) for Service 2
    #     r2 = throughput2 - latency2  # Reward for Service 2 (maximize throughput, minimize latency)

    #     # Average Number of Requests (ANR) for both services
    #     anr = (self.nr1 + self.nr2) / 2.0  # Average request rate for both services
        
    #     # Final reward (weighted sum), considering traffic weights and ANR
    #     reward = self.lc1 * r1 + self.lc2 * r2 - anr  # Penalize higher ANR
    #     return reward

    def _compute_reward(self, state):
        """
        Compute a shaped reward based on throughput and latency for both services, with added noise to prevent overfitting.
        """
        # Unpack state variables (specific to your environment)
        service1_latency, service1_cpu_util, service1_request_rate, \
        service2_latency, service2_cpu_util, service2_request_rate = state

        # Reward for Service 1
        throughput1 = service1_request_rate  # Throughput for Service 1 (request rate)
        latency1 = service1_latency  # Latency (response time) for Service 1
        r1 = throughput1 - latency1  # Reward for Service 1 (maximize throughput, minimize latency)

        # Reward for Service 2
        throughput2 = service2_request_rate  # Throughput for Service 2 (request rate)
        latency2 = service2_latency  # Latency (response time) for Service 2
        r2 = throughput2 - latency2  # Reward for Service 2 (maximize throughput, minimize latency)

        # Average Number of Requests (ANR) for both services
        anr = (self.nr1 + self.nr2) / 2.0  # Average request rate for both services

        # Final reward (weighted sum), considering traffic weights and ANR
        reward = self.lc1 * r1 + self.lc2 * r2 - anr  # Penalize higher ANR

        # Add small random noise to the reward for better generalization
        reward += random.uniform(-0.01, 0.01)

        return reward


    def _adjust_weights(self, adjust_a, adjust_b):
        """
        Adjust traffic weights between two leaf services based on action values, preventing extreme shifts.
        """
        # Apply smaller adjustments and clamp to valid range
        self.traffic_weights[0] = min(max(self.traffic_weights[0] + adjust_a, 0.1), 0.9)
        self.traffic_weights[1] = min(max(self.traffic_weights[1] + adjust_b, 0.1), 0.9)

        total_weight = sum(self.traffic_weights)
        if total_weight > 0:
            self.traffic_weights = [w / total_weight for w in self.traffic_weights]
        else:
            self.traffic_weights = [0.5, 0.5]

        print(f"Adjusted traffic weights to: {self.traffic_weights}")


    def _equalize_traffic(self):
        """
        Equalize traffic between both services.
        """
        self.traffic_weights = [0.5, 0.5]
        print("Equalized traffic weights to 50% each.")

    def _check_done(self):
        """
        Define when an episode is considered finished.
        """
        # Example condition: episode ends if latency or CPU utilization is too high for either service
        return any(metric > 0.9 for metric in self.state)
