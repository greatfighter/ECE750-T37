from scenario_monitor import *
from scenario_manager import *
import global_var

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
			print(df.head())  # Print the first few rows of the DataFrame for preview
		else:
			print("No data available for this service.")
		print("-" * 50)

def main():
	URL = "https://ca-tor.monitoring.cloud.ibm.com"
	APIKEY = "E5wgqSh1yPF_s_0NSLPF94zSA3mK2fx1go3GUQqxbFde"
	GUID = "3fed93bc-00f4-4651-8ce2-e73ba4b9a918"

	# metrices: time aggregation is average
	avg_metric_ids = [
		"cpu.quota.used.percent",
		"cpu.used.percent",
		"cpu.cores.used",        
		"memory.limit.used.percent",             
	]

	# metrices: time aggregation is maximum
	max_metric_ids = [
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
		("net.connection.count.in", "sum"),
		("net.request.count.in", "sum"),
	]

	# Variable for monitor and data manipulation
	scenario_monitor = ScenarioMonitor(URL, APIKEY, GUID)
	data_processor = DataProcessor(core_metrics)
	
	# Variable for scenario manager
	recent_loads = deque(maxlen=10)  # Initialize a deque with a maximum length of 10, automatically removes the oldest element when new elements are added
	scenario_manager = ScenarioManager(ema_alpha=0.2, ema_threshold=5, variance_threshold=10, concurrency_threshold=100)

	while True:
		# Fetch data from IBM
		for id in avg_metric_ids:
			scenario_monitor.fetch_data_from_ibm(id, "avg")

		for id in sum_metric_ids:
			scenario_monitor.fetch_data_from_ibm(id, "sum")

		for id in max_metric_ids:
			scenario_monitor.fetch_data_from_ibm(id, "max")
		print(f"Pulling metrics from IBM Cloud")
		service_data_dict = data_processor.process_data(global_var.CREATE_NEW_FILE)
		print_service_data(service_data_dict)
		exit()
		# for metrics in metrics_list:
		# 	# Analyze the scenario
		# 	scenario, current_load = scenario_manager.analyze_scenario(metrics, list(recent_loads))

		# 	# Add the current load to the deque
		# 	recent_loads.append(current_load)

		# 	# Print results
		# 	print(f"Current combined load: {current_load:.2f}")
		# 	print(f"Recent loads: {list(recent_loads)}")
		# 	if scenario:
		# 		print(f"Detected scenarios: {', '.join(scenario)}")
		# 	else:
		# 		print("No abnormal scenarios detected")
		# 	print("-" * 50)

		# # Sleep for customizing second
		time.sleep(global_var.SLEEP)

if __name__ == '__main__':
	main()
