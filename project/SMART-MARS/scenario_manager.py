from collections import deque
from collections import defaultdict
import numpy as np

class ScenarioManager:
	def __init__(self, ema_alpha=0.2, ema_threshold=5, variance_threshold=10, concurrency_threshold=100):
		"""
		Initialize the scenario manager
		:param ema_alpha: EMA smoothing factor (0 < alpha <= 1)
		:param ema_threshold: Threshold for detecting load fluctuation based on EMA
		:param variance_threshold: Threshold for detecting load fluctuation based on variance
		:param concurrency_threshold: Threshold for detecting high concurrency based on active connections
		"""
		self.ema_alpha = ema_alpha
		self.ema_value = None  # Initial EMA value
		self.ema_threshold = ema_threshold
		self.variance_threshold = variance_threshold
		self.concurrency_threshold = concurrency_threshold

	def calculate_combined_load(self, metrics):
		"""
		Calculate the combined load value
		:param metrics: A dictionary of metrics, e.g., {'cpu_usage': 50, 'memory_usage': 60, 'connections': 200, 'requests': 1000}
		:return: Combined load value
		"""
		weights = {
			"cpu_usage": 0.4,        # Weight for CPU usage
			"memory_usage": 0.3,     # Weight for memory usage
			"connections": 0.2,      # Weight for network connections
			"requests": 0.1          # Weight for request count
		}
		# Normalize and calculate weighted combined load
		load = (
			weights["cpu_usage"] * (metrics["cpu_usage"] / 100) +
			weights["memory_usage"] * (metrics["memory_usage"] / 100) +
			weights["connections"] * (metrics["connections"] / 1000) +
			weights["requests"] * (metrics["requests"] / 1000)
		)
		return load * 100  # Convert to percentage

	def calculate_ema(self, current_load):
		"""
		Calculate the EMA (Exponential Moving Average) of the load
		:param current_load: Current load value
		:return: Updated EMA value
		"""
		if self.ema_value is None:
			self.ema_value = current_load
		else:
			self.ema_value = self.ema_alpha * current_load + (1 - self.ema_alpha) * self.ema_value
		return self.ema_value

	def calculate_variance(self, load_list):
		"""
		Calculate the variance of the load
		:param load_list: List of recent load values
		:return: Variance of the load (0 if load_list is empty)
		"""
		if not load_list:  # Handle empty load_list
			return 0
		return np.var(load_list)

	def detect_load_fluctuation(self, current_load, load_list):
		"""
		Detect load fluctuation scenario
		:param current_load: Current load value
		:param load_list: List of recent load values
		:return: Whether a load fluctuation is detected (True/False)
		"""
		ema = self.calculate_ema(current_load)

		# Handle empty load_list gracefully
		if not load_list:
			print("Warning: load_list is empty. Skipping variance-based fluctuation detection.")
			return abs(current_load - ema) > self.ema_threshold

		variance = self.calculate_variance(load_list)
		if abs(current_load - ema) > self.ema_threshold or variance > self.variance_threshold:
			return True
		return False

	def detect_concurrency(self, metrics):
		"""
		Detect high concurrency scenario
		:param metrics: A dictionary of metrics
		:return: Whether high concurrency is detected (True/False)
		"""
		return metrics["connections"] > self.concurrency_threshold

	def analyze_scenario(self, metrics, load_list):
		"""
		Analyze the current scenario
		:param metrics: A dictionary of metrics, e.g., {'cpu_usage': 50, 'memory_usage': 60, 'connections': 200, 'requests': 1000}
		:param load_list: List of recent load values
		:return: Scenario analysis result
		"""
		current_load = self.calculate_combined_load(metrics)
		fluctuation = self.detect_load_fluctuation(current_load, load_list)
		high_concurrency = self.detect_concurrency(metrics)

		scenario = []
		if fluctuation:
			scenario.append("Load Fluctuation")
		if high_concurrency:
			scenario.append("High Concurrency")

		return scenario, current_load


# Example Usage
if __name__ == "__main__":
	# Initialize a defaultdict for recent loads for each service
	recent_loads_dict = defaultdict(lambda: deque(maxlen=10))  # Automatically removes the oldest element when new elements are added

	# Example input metrics
	service_data_dict = {
		"service1": pd.DataFrame({
			"timestamp": [1732321590, 1732321591, 1732321592],
			"cpu_usage_avg": [75, 78, 80],
			"memory_usage_avg": [60, 63, 65],
			"connections": [120, 130, 140],
			"requests": [500, 550, 600]
		}),
		"service2": pd.DataFrame({
			"timestamp": [1732321590, 1732321591, 1732321592],
			"cpu_usage_avg": [85, 90, 95],
			"memory_usage_avg": [68, 70, 75],
			"connections": [150, 160, 170],
			"requests": [650, 700, 750]
		})
	}

	# Initialize the manager
	manager = ScenarioManager(ema_alpha=0.2, ema_threshold=5, variance_threshold=10, concurrency_threshold=100)

	# Simulate metrics input over time
	for service, df in service_data_dict.items():
		print(f"\nProcessing data for {service}")
		
		# Ensure the DataFrame is sorted by timestamp
		df = df.sort_values(by="timestamp").reset_index(drop=True)

		# Iterate through rows of the DataFrame
		for _, row in df.iterrows():
			metrics = {
				"cpu_usage": row["cpu_usage_avg"],
				"memory_usage": row["memory_usage_avg"],
				"connections": row["connections"],
				"requests": row["requests"]
			}
			# Analyze the scenario
			scenario, current_load = manager.analyze_scenario(metrics, list(recent_loads_dict[service]))

			# Add the current load to the service's recent loads deque
			recent_loads_dict[service].append(current_load)

			# Print results
			print(f"Timestamp: {row['timestamp']}, Current combined load: {current_load:.2f}")
			print(f"Recent loads for {service}: {list(recent_loads_dict[service])}")
			if scenario:
				print(f"Detected scenarios for {service}: {', '.join(scenario)}")
			else:
				print(f"No abnormal scenarios detected for {service}")
			print("-" * 50)
