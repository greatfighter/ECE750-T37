import gymnasium as gym
from gymnasium import spaces
import numpy as np
import requests  # Use for service mesh APIs
import random    # Simulate metric responses if no live data

class ServiceMeshEnv(gym.Env):
    def __init__(self, action_type="continuous"):
        super(ServiceMeshEnv, self).__init__()
        
        # Configure action space based on type
        self.action_type = action_type
        if action_type == "discrete":
            # Discrete action space: scale up, scale down, route traffic
            self.action_space = spaces.Discrete(3)
        elif action_type == "continuous":
            # Continuous action space
            self.action_space = spaces.Box(low=np.array([-1.0, -1.0]), high=np.array([1.0, 1.0]), dtype=np.float32)
        else:
            raise ValueError("Invalid action_type. Choose 'discrete' or 'continuous'.")

        # Observation space: latency, CPU utilization, request rate
        self.observation_space = spaces.Box(low=0, high=1, shape=(3,), dtype=np.float32)
        
        # Initialize environment state
        self.state = self._get_metrics()
        self.done = False

    def _get_metrics(self):
        """
        Fetch metrics from service mesh monitoring tools like Prometheus.
        Here we simulate latency, CPU usage, and request rate.
        """
        latency = random.uniform(0, 1)     # Simulated latency (0 = low, 1 = high)
        cpu_util = random.uniform(0, 1)    # Simulated CPU utilization
        request_rate = random.uniform(0, 1) # Simulated request rate
        return np.array([latency, cpu_util, request_rate], dtype=np.float32)

    def step(self, action):
        """
        Execute the action in the environment, observe the result, and compute the reward.
        """
        if self.action_type == "discrete":
            # Discrete action handling
            if action == 0:
                self._scale_service('up', amount=0.1)  # Scale up by a fixed amount
            elif action == 1:
                self._scale_service('down', amount=0.1)  # Scale down by a fixed amount
            elif action == 2:
                self._route_traffic()

        elif self.action_type == "continuous":
            # Continuous action handling
            scale_up = action[0]  # Continuous value for scaling up
            scale_down = action[1]  # Continuous value for scaling down
            
            if scale_up > 0:
                self._scale_service('up', scale_up)
            if scale_down > 0:
                self._scale_service('down', scale_down)
            # Optionally: Add logic for routing traffic if action has more dimensions

        # Get new state and compute reward
        self.state = self._get_metrics()
        reward = self._compute_reward(self.state)
        self.done = self._check_done()

        # For gymnasium compatibility, include truncated flag (set it to False for now)
        return self.state, reward, self.done, False, {}

    def reset(self, **kwargs):
        """
        Reset the environment for a new episode.
        """
        self.state = self._get_metrics()
        self.done = False
        return self.state, {}

    def _compute_reward(self, state):
        """
        Compute reward based on metrics.
        """
        latency, cpu_util, request_rate = state
        reward = 0
        
        # Example reward: lower latency and CPU utilization are better
        if latency < 0.5:
            reward += 1
        if cpu_util < 0.5:
            reward += 1
        if request_rate > 0.7:
            reward -= 1  # Penalize if request rate is too high
        
        return reward

    def _scale_service(self, direction, amount):
        """
        Simulate scaling action in the service mesh.
        - For discrete actions: scale up or down by a fixed amount.
        - For continuous actions: scale by the 'amount' provided.
        """
        if self.action_type == "discrete":
            print(f"Scaling service {direction} by a fixed amount of {amount}...")
        elif self.action_type == "continuous":
            print(f"Scaling service {direction} by amount {amount}...")

    def _route_traffic(self):
        """
        Simulate routing traffic to different services.
        """
        print("Routing traffic...")  # Replace with actual API call

    def _check_done(self):
        """
        Define when an episode is considered finished.
        """
        # Example condition: episode ends if latency or CPU utilization is too high
        return any(metric > 0.9 for metric in self.state)