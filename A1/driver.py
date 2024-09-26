import os
import sys
import json
import time
import pandas as pd
from sdcclient import IbmAuthHelper, SdMonitorClient
from datetime import datetime

SLEEP = 60
SERVICE_TO_USE = [
    'acmeair-mainservice',
    'acmeair-authservice',
    'acmeair-flightservice',
    'acmeair-customerservice',
    'acmeair-bookingservice'
]

def bytes_to_mb(bytes_value):
    mb_value = bytes_value / (1024 * 1024)
    return mb_value

class Monitor:
    def __init__(self, url, api_key, guid):
        # Create a client object using the IBM Cloud API credentials
        ibm_headers = IbmAuthHelper.get_headers(url, api_key, guid)
        self.sdclient = SdMonitorClient(sdc_url=url, custom_headers=ibm_headers)

        # Sysdig Data API Query Parameters
        # Pull the latest 5 minutes of data
        self.START = -SLEEP
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

class Analyzer:
    def __init__(self, metrics):
        # set relative weight for each property
        # Set relative weights for each metric
        self.weight_cpu = 0.2      # CPU usage weight
        self.weight_memory = 0.2   # Memory usage weight
        self.weight_latency = 0.45 # Latency weight
        self.weight_tps = 0.15     # Transactions per second (TPS) weight
        self.weight_gc_time = 0.15 # GC time weight
        
        # Add weight for cost (CPU, memory, pod cost)
        self.weight_cost = 0.1     # Cost weight (initialized)
        self.metrics = metrics
        self.services = ['acmeair-bookingservice', 'acmeair-customerservice', 'acmeair-authservice',
                         'acmeair-flightservice', 'acmeair-mainservice']

    def triggerAdaptation(self, cpu, memory, latency, tps, gc_time):
        # Check whether adaptation is needed based on CPU, memory, and latency values
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"Time: {current_time}, CPU: {cpu:.2f}%, Memory: {memory:.2f}%, Latency: {latency:.2f}ms, TPS: {tps:.2f}, GC Time: {gc_time:.2f}ms")
        if cpu > 80 or memory > 80 or latency > 1000 or tps < 50 or gc_time > 500:
            return True
        else:
            return False
    
    def utility_preference_cpu(self, cpu):
        # Determine the utility preference for CPU usage
        if cpu < 25:
            return 1
        elif cpu < 50:
            return 0.5
        else:
            return 0

    def utility_preference_memory(self, memory):
        # Determine the utility preference for memory usage
        if memory < 25:
            return 1
        elif memory < 50:
            return 0.5
        else:
            return 0
    
    def utility_preference_latency(self, latency):
        # Determine the utility preference for latency
        if latency < 1e7:
            return 1
        elif latency < 2e7:
            return 0.5
        else:
            return 0
    
    def utility_preference_tps(self, tps):
        # Determine the utility preference for TPS
        if tps > 100:
            return 1
        elif tps > 50:
            return 0.5
        else:
            return 0

    def utility_preference_gc_time(self, gc_time):
        # Determine the utility preference for GC
        if gc_time < 200:
            return 1
        elif gc_time < 500:
            return 0.5
        else:
            return 0

    def utility_preference_cost(self, cost):
        # Determine the utility preference for cost (cpu, memory, pod)
        if cost == "cpu" or cost == "memory":
            return 1
        else:
            return 0.5

    def calculate_utility(self, cpu, memory, latency, tps, gc_time, cost):
        # Calculate the overall utility score based on weighted preferences
        cpu_utility = self.weight_cpu * self.utility_preference_cpu(cpu)
        memory_utility = self.weight_memory * self.utility_preference_memory(memory)
        latency_utility = self.weight_latency * self.utility_preference_latency(latency)
        tps_utility = self.weight_tps * self.utility_preference_tps(tps)
        gc_time_utility = self.weight_gc_time * self.utility_preference_gc_time(gc_time)
        cost_utility = self.weight_cost * self.utility_preference_cost(cost)
        return cpu_utility + memory_utility + latency_utility + tps_utility + gc_time_utility + cost_utility

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

    def process_data(self):
        # process data from json files
        service_to_index = {service: idx for idx, service in enumerate(SERVICE_TO_USE)}
    
        # Initialize outputs with the same length as SERVICE_TO_USE and metrics
        outputs = [[0] * len(self.metrics) for _ in range(len(SERVICE_TO_USE))]

        for idx, (metric_id, aggregation) in enumerate(self.metrics):
            filename = "datasets/" + metric_id.replace('.', '_') + "_" + aggregation + "_metric.json"
            df = self.create_dataframe(filename)
            
            # Print the metric_id and original dataframe for debugging
            # print(metric_id)
            # print(df)
            
            # Filter the dataframe to only include services in SERVICE_TO_USE
            df_filtered = df[df['service'].isin(SERVICE_TO_USE)]
            
            # Group the filtered dataframe by 'service'
            aggregationData = df_filtered.groupby('service')
            avg_values = aggregationData['value'].mean()

            # Map the average values back to the correct index in outputs
            for service, avg_value in avg_values.items():
                if service in service_to_index:
                    index = service_to_index[service]
                    outputs[index][idx] = avg_value
        # exit(1)

        for i in range(5):
            cpu = outputs[i][0]
            memory = outputs[i][1]
            latency = outputs[i][2]
            tps = outputs[i][3]
            gc_time = outputs[i][4]
            print ("##########################")
            print(f"Service: {SERVICE_TO_USE[i]}")  # Print the current service name
            adaptation = self.triggerAdaptation(cpu, memory, latency, tps, gc_time)
            if adaptation:
                print(f"{self.services[i]} requires adaptation")
                self.find_best_strategy(outputs[i])
            else:
                print(f"No adaptation required for {self.services[i]}")

    def find_best_strategy(self, output):
        cpu = output[0]
        memory = output[1]
        latency = output[2]
        tps = output[3]
        gc_time = output[4]
        
        # Strategy 1: Increase CPU resources (assume increasing CPU reduces CPU usage and latency)
        # Increasing CPU lowers CPU usage and latency, slightly improves TPS, GC time remains unchanged
        utility1 = self.calculate_utility(cpu / 1.5, memory, latency / 1.2, tps * 1.1, gc_time, "cpu")
        
        # Strategy 2: Increase memory resources (assume increasing memory reduces GC time and latency)
        # Increasing memory reduces memory usage and GC time, slightly improves TPS, and lowers latency
        utility2 = self.calculate_utility(cpu, memory / 2.0, latency / 1.1, tps * 1.05, gc_time / 1.5, "memory")
        
        # Strategy 3: Increase the number of Pods (assume more Pods improve TPS and reduce latency)
        # Adding more Pods significantly improves TPS and reduces latency, with minor impact on CPU and memory usage
        utility3 = self.calculate_utility(cpu / 1.2, memory / 1.2, latency / 1.5, tps * 1.5, gc_time / 1.1, "pod")
        
        # Strategy 4: Optimize garbage collection (assume optimizing GC time improves overall performance)
        # Reducing GC time improves performance by optimizing JVM or allocating more memory
        utility4 = self.calculate_utility(cpu, memory, latency / 1.05, tps, gc_time / 2.0, "gc")
        
        # Calculate utilities for each strategy and select the best one
        utilities = {
            'Increase CPU': utility1,
            'Increase Memory': utility2,
            'Increase Pod': utility3,
            'Optimize GC': utility4
        }
        
        # Select the strategy with the highest utility value
        best_strategy = max(utilities, key=utilities.get)
        print(f"Best strategy: {best_strategy}")


def main():
    # IBM Cloud API Credentials
    URL = "https://ca-tor.monitoring.cloud.ibm.com"
    APIKEY = "E5wgqSh1yPF_s_0NSLPF94zSA3mK2fx1go3GUQqxbFde"
    GUID = "3fed93bc-00f4-4651-8ce2-e73ba4b9a918"

    # metrices: time aggregation is average
    avg_metric_ids = [
        "cpu.quota.used.percent",          
        "memory.limit.used.percent",       
        "jvm.gc.global.time"         
    ]

    # metrices: time aggregation is maximum
    max_metric_ids = [
        "net.http.request.time" 
    ]

    # metrices: time aggregation is summation
    sum_metric_ids = [
        "net.request.count.in"
    ]

    # metrices: core metrics used to perform adaptation analysis
    core_metrics = [
        ("cpu.quota.used.percent", "avg"),
        ("memory.limit.used.percent", "avg"),
        ("net.http.request.time", "max"),
        ("net.request.count.in", "sum"),
        ("jvm.gc.global.time", "avg")
    ]

    monitor = Monitor(URL, APIKEY, GUID)
    analyzer = Analyzer(core_metrics)

    while True:
        # Fetch data from IBM
        for id in avg_metric_ids:
            monitor.fetch_data_from_ibm(id, "avg")

        for id in sum_metric_ids:
            monitor.fetch_data_from_ibm(id, "sum")

        for id in max_metric_ids:
            monitor.fetch_data_from_ibm(id, "max")
        print(f"Pulling metrics from IBM Cloud")
        analyzer.process_data()
        # Sleep for 5 minutes (300 seconds)
        time.sleep(SLEEP)

if __name__ == "__main__":
    main()