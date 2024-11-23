import os
import sys
import json
import time
import pandas as pd
from sdcclient import IbmAuthHelper, SdMonitorClient
from datetime import datetime
import global_var

class ScenarioMonitor:
	def __init__(self, url, api_key, guid):
		# Create a client object using the IBM Cloud API credentials
		ibm_headers = IbmAuthHelper.get_headers(url, api_key, guid)
		self.sdclient = SdMonitorClient(sdc_url=url, custom_headers=ibm_headers)

		# Sysdig Data API Query Parameters
		# Pull the latest 5 minutes of data
		self.START = -global_var.DURATION
		self.END = 0
		self.SAMPLING = 10
		self.FILTER = 'kube_namespace_name="group-4"' # None
	
	# Function to fetch data from IBM Cloud
	def fetch_data_from_ibm(self, id, aggregation):
		# Specify the metric to query
		metric = [
			# segmentation metric
			{"id": "kubernetes.deployment.name"},
			# Specify the ID for keys, and ID with aggregation for values
			{"id": id,
			"aggregations": {
				"time": aggregation,
				"group": "avg"
			}}
			# {"id": "cpu.used.percent", "aggregations": {"time": "timeAvg", "group": "avg"}}
			]

		# Query the metric
		ok, res = self.sdclient.get_data(metrics=metric,  # metrics list
										start_ts=self.START,  # start_ts = 600 seconds ago
										end_ts=self.END,
										sampling_s=self.SAMPLING,
										filter=self.FILTER)  # end_ts = now
		# print("Raw response data:", res)
		# Check if the query was successful
		if ok:
			data = res
		else:
			print(res)
			sys.exit(1)
		
		# Create a directory to store the datasets if it does not exist
		if not os.path.exists('datasets'):
			os.mkdir('datasets')
			print("The 'datasets' directory is created.")

		# Write the data to a json file
		filename = "datasets/" + id.replace(".", "_") + "_" + aggregation + "_metric.json"
		with open(filename, "w") as outfile: 
			json.dump(data, outfile)

class DataProcessor:
	def __init__(self, metrics):
		# set relative weight for each property
		# Set relative weights for each metric
		
		# Add weight for cost (CPU, memory, pod cost)
		self.metrics = metrics
		self.services = global_var.SERVICE_TO_USE

	def create_dataframe(self, filename):
		# Create a DataFrame from a JSON file
		with open(filename, 'r') as file:
			data = json.load(file)
		new_data = []
		for entry in data["data"]:
			new_entry = {}
			new_entry["timestamp"] = entry['t']
			new_entry["service"] = entry['d'][0]
			new_entry["value"] = entry['d'][1]
			new_data.append(new_entry)
		return pd.DataFrame(new_data)

	def process_data(self, create_new_file = False):
		# process data from json files
		# return: A dictionary where keys are services and values are DataFrames grouped by timestamp.
		service_to_index = {service: idx for idx, service in enumerate(global_var.SERVICE_TO_USE)}
		service_data_dict = {service: pd.DataFrame() for service in global_var.SERVICE_TO_USE}

		for idx, (metric_id, aggregation) in enumerate(self.metrics):
			filename = "datasets/" + metric_id.replace('.', '_') + "_" + aggregation + "_metric.json"
			df = self.create_dataframe(filename)
			
			# Print the metric_id and original dataframe for debugging
			# print(metric_id)
			# print(df)
			
			# Filter the dataframe to only include services in SERVICE_TO_USE
			# df_filtered = df[df['service'].isin(global_var.SERVICE_TO_USE)]
			# df_filtered['metric_name'] = f"{metric_id}_{aggregation}"  # Add a column to track metric names
			df_filtered = df[df['service'].isin(global_var.SERVICE_TO_USE)].copy()  # 使用 .copy() 创建副本
			df_filtered['metric_name'] = f"{metric_id}_{aggregation}"  # 添加新列
			grouped_data = df_filtered.groupby('service')
			# print (df_filtered)
			for service, service_data in grouped_data:
				# Append current metric data to the service-specific DataFrame
				service_pivot = service_data.pivot_table(
					index='timestamp',  # Group rows by timestamp
					columns='metric_name',  # Metrics become columns
					values='value',  # Values for each metric
					aggfunc='first'  # If duplicates exist, take the first
				).reset_index()

				# Merge with existing data for the service
				if not service_data_dict[service].empty:
					service_data_dict[service] = pd.merge(
						service_data_dict[service],
						service_pivot,
						on='timestamp',
						how='outer'
					)
				else:
					service_data_dict[service] = service_pivot

				# Create repository for each service
				service_folder = os.path.join('datasets', service)
				if not os.path.exists(service_folder):
					os.makedirs(service_folder)

				service_filename = os.path.join(service_folder, f"{metric_id.replace('.', '_')}_{aggregation}.csv")
				
				if not create_new_file and os.path.exists(service_filename):
					global_var.CREATE_NEW_FILE = False
					existing_data = pd.read_csv(service_filename)
					service_data = pd.concat([existing_data, service_data]).drop_duplicates().reset_index(drop=True)

				service_data.to_csv(service_filename, index=False)
				print(f"Data for {service} saved to {service_filename}")

		for service in global_var.SERVICE_TO_USE:
			if not service_data_dict[service].empty:
				metric_columns = [f"{metric_id}_{aggregation}" for metric_id, aggregation in self.metrics]
				service_data_dict[service] = service_data_dict[service][['timestamp'] + metric_columns]

		return service_data_dict

def main():
	# IBM Cloud API Credentials
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

	monitor = ScenarioMonitor(URL, APIKEY, GUID)
	data_processor = DataProcessor(core_metrics)

	while True:
		# Fetch data from IBM
		for id in avg_metric_ids:
			monitor.fetch_data_from_ibm(id, "avg")

		for id in sum_metric_ids:
			monitor.fetch_data_from_ibm(id, "sum")

		for id in max_metric_ids:
			monitor.fetch_data_from_ibm(id, "max")
		print(f"Pulling metrics from IBM Cloud")
		data_processor.process_data(global_var.CREATE_NEW_FILE)
		# Sleep for customizing second
		time.sleep(global_var.SLEEP)

if __name__ == "__main__":
	main()