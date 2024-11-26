from scenario_monitor import *
from scenario_manager import *
import global_var as gv
import time
import logging
import numpy as np
from stable_baselines3 import PPO, DDPG, A2C  # Change this to the model you used
from RL_model_training.Agent import Environment_test as Environment  # Import your environment

def print_service_data(service_data_dict):
	"""
	Print the contents of the service_data_dict in a structured format.
	:param service_data_dict: Dictionary where keys are service names and values are DataFrames
	"""
	print("=== Service Data Summary ===")
	for service, df in service_data_dict.items():
		print(f"\nService: {service}")
		print(f"Number of Records: {len(df)}")
		if not df.empty:
			print("Data Preview:")
			print(df)  # Print the first few rows of the DataFrame for preview
		else:
			print("No data available for this service.")
		print("-" * 50)

def adapt_data_to_scenario_manager(service_data_dict):
	"""
	Preprocess the service_data_dict by renaming specific columns and retaining only the desired columns.
	Combine all services into a single DataFrame.
	:param service_data_dict: Dictionary where keys are services and values are DataFrames
	:return: A single combined DataFrame with renamed and filtered columns
	"""
	# Column mapping for renaming
	column_mapping = {
		"cpu.quota.used.percent_avg": "cpu_usage_avg",
		"memory.limit.used.percent_avg": "memory_usage_avg",
		"net.connection.count.in_sum": "connections",
		"net.request.count.in_sum": "requests"
	}
	desired_columns = ["timestamp"] + list(column_mapping.keys())

	# List to store processed DataFrames
	processed_service_data = {}
	# Process each service
	for service, df in service_data_dict.items():
		# Ensure that the required columns are present
		missing_columns = set(column_mapping.keys()).difference(df.columns)
		if missing_columns:
			raise KeyError(f"The following required columns are missing in the DataFrame for service {service}: {missing_columns}")

		# Rename columns
		df = df.rename(columns=column_mapping)

		# Retain only the desired columns
		df = df[["timestamp"] + list(column_mapping.values())]

		# Add the processed DataFrame to the dictionary
		processed_service_data[service] = df

	return processed_service_data

def analyze_scenario(scenario_manager):
	for service, df in processed_service_data.items():
		print(f"\nProcessing data for {service}")
		
		# Ensure the DataFrame is sorted by timestamp
		df = df.sort_values(by="timestamp").reset_index(drop=True)
		vote = []

		# Iterate through rows of the DataFrame
		for _, row in df.iterrows():
			metrics = {
				"cpu_usage": row["cpu_usage_avg"],
				"memory_usage": row["memory_usage_avg"],
				"connections": row["connections"],
				"requests": row["requests"]
			}
			# Analyze the scenario
			scenario, current_load = scenario_manager.analyze_scenario(metrics, list(recent_loads_dict[service]))

			# Add the current load to the service's recent loads deque
			recent_loads_dict[service].append(current_load)

			# Evaluate the all timestamp across the period
			if scenario:
				vote.append(1)
			else:
				vote.append(0)

		count_1 = vote.count(1)
		count_0 = vote.count(0)
		if count_1 > count_0:
			print(f"Detected scenarios for {service}")
			return True
		else:
			print(f"No abnormal scenarios detected for {service}")
	return False

def main():
	# metrices: time aggregation is average
	avg_metric_ids = [
		"cpu.quota.used.percent",
		"cpu.used.percent",
		"cpu.cores.used",        
		"memory.limit.used.percent",             
	]

	# metrices: time aggregation is maximum
	max_metric_ids = [
		"net.http.request.time"
	]

	# metrices: time aggregation is summation
	sum_metric_ids = [
		"net.connection.count.in",
		"net.request.count.in"
	]

	# metrices: core metrics used to perform adaptation analysis
	core_metrics = [
		("cpu.quota.used.percent", "avg"),
		("memory.limit.used.percent", "avg"),
		("cpu.used.percent", "avg"),
		("cpu.cores.used", "avg"),
		("net.http.request.time", "max"),
		("net.connection.count.in", "sum"),
		("net.request.count.in", "sum"),
	]

	# Variable for monitor and data manipulation
	scenario_monitor = ScenarioMonitor(gv.URL, gv.APIKEY, gv.GUID)
	data_processor = DataProcessor(core_metrics)
	model_manager = ModelManager(gv.MODEL_PATH)
	
	# Variable for scenario manager
	recent_loads_dict = defaultdict(lambda: deque(maxlen=30))  # Automatically removes the oldest element when new elements are added
	scenario_manager = ScenarioManager(ema_alpha=0.2, ema_threshold=5, variance_threshold=10, concurrency_threshold=100)

	while True:
		# Fetch data from IBM
		for id in avg_metric_ids:
			scenario_monitor.fetch_data_from_ibm(id, "avg")

		for id in sum_metric_ids:
			scenario_monitor.fetch_data_from_ibm(id, "sum")

		for id in max_metric_ids:
			scenario_monitor.fetch_data_from_ibm(id, "max")
		print(f"Pulling metrics from Prometheus")

		service_data_dict = data_processor.process_data(gv.CREATE_NEW_FILE)
		processed_service_data = adapt_data_to_scenario_manager(service_data_dict)
		# For DEBUG
		# print (processed_service_data)

		detect_scenario = analyze_scenario(scenario_manager)
		if detect_scenario:
			pass

		# # Sleep for customizing second
		time.sleep(gv.SLEEP)

if __name__ == '__main__':
	main()
