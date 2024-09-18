import os
import sys
import json
import time
import pandas as pd
import heapq
from sdcclient import IbmAuthHelper, SdMonitorClient

class Monitor:
    def __init__(self, url, api_key, guid):
        # Create a client object using the IBM Cloud API credentials
        ibm_headers = IbmAuthHelper.get_headers(url, api_key, guid)
        self.sdclient = SdMonitorClient(sdc_url=url, custom_headers=ibm_headers)

        # Sysdig Data API Query Parameters
        # Pull the latest 5 minutes of data
        self.START = -600
        self.END = 0
        self.SAMPLING = 10
        self.FILTER = None #'kubernetes.namespace.name="acmeair-g4"'
    
    # Function to fetch data from IBM Cloud
    def fetch_data_from_ibm_cloud(self, id, aggregation):
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
        self.weight_cpu = 0.2
        self.weight_memory = 0.2
        self.weight_latency = 0.45
        self.weight_cost = 0.15
        self.metrics = metrics
        self.services = ['acmeair-bookingservice', 'acmeair-customerservice', 'acmeair-authservice',
                         'acmeair-flightservice', 'acmeair-mainservice']

    def triggerAdaptation(self, cpu, memory, latency):
        # Check whether adaptation is needed based on CPU, memory, and latency values
        print(f"CPU: {cpu:.2f}, memory: {memory:.2f}, latency: {latency:.2f}")
        if cpu > 50 or memory > 50 or latency > 2e7:
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
    
    def utility_preference_cost(self, cost):
        # Determine the utility preference for cost (cpu, memory, pod)
        if cost == "cpu" or cost == "memory":
            return 1
        else:
            return 0.5

    def calculate_utility(self, cpu, memory, latency, cost):
        # Calculate the overall utility score based on weighted preferences
        cpu_utility = self.weight_cpu * self.utility_preference_cpu(cpu)
        memory_utility = self.weight_memory * self.utility_preference_memory(memory)
        latency_utility = self.weight_latency * self.utility_preference_latency(latency)
        cost_utility = self.weight_cost * self.utility_preference_cost(cost)
        return cpu_utility + memory_utility + latency_utility + cost_utility

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
        # perform data preprocessing and check whether adaptation is required
        outputs = [[0]*len(self.metrics) for i in range(5)]
        for idx, (metric_id, aggregation) in enumerate(self.metrics):
            filename = "datasets/" + metric_id + "_" + aggregation + "_metric.json"
            df = self.create_dataframe(filename)
            aggregationData = df.groupby('service')
            avg_values = aggregationData['value'].mean()
            for i in range(5):
                outputs[i][idx] = avg_values.iloc[i]

        # for each service, determine whether adaptation is needed
        for i in range(5):
            cpu = outputs[i][0]
            memory = outputs[i][1]
            latency = outputs[i][2]
            adaptation = self.triggerAdaptation(cpu, memory, latency)
            if adaptation:
                print(f"{self.services[i]} requires adaptation")
                self.find_best_strategy(outputs[i])
            else:
                print(f"No adaptation required for {self.services[i]}")

    def find_best_strategy(self, output):
        # Find the best adaptation strategy based on utility functions
        cpu = output[0]
        memory = output[1]
        latency = output[2]
        # strategy1: increase cpu
        utility1 = self.calculate_utility(cpu / 2.0, memory, latency / 2.0, "cpu")
        # strategy2: increase memory
        utility2 = self.calculate_utility(cpu, memory / 2.0, latency / 2.0, "memory")
        # strategy3: increase pod
        utility3 = self.calculate_utility(cpu / 2.0, memory / 2.0, latency / 4.0, "pod")

        if utility1 > utility2 and utility1 > utility3:
            print("Best strategy: Increase cpu")
        elif utility2 > utility1 and utility2 > utility3:
            print("Best strategy: Increase memory")
        else:
            print("Best strategy: Increase pod")

def main():
    # IBM Cloud API Credentials
    URL = "https://ca-tor.monitoring.cloud.ibm.com"
    APIKEY = "E5wgqSh1yPF_s_0NSLPF94zSA3mK2fx1go3GUQqxbFde"
    GUID = "3fed93bc-00f4-4651-8ce2-e73ba4b9a918"

    # metrices: time aggregation is average
    avg_metric_ids = ["cpu.quota.used.percent",
                      "cpu.used.percent",
                      "memory.limit.used.percent",
                      "memory.bytes.used",
                      "mongodb.connections.current",
                      "jvm.class.loaded",
                      "jvm.class.unloaded",
                      "jvm.gc.global.time",
                      "jvm.gc.global.count",
                      "jvm.thread.count",
                      "jvm.heap.used",
                      "jvm.nonHeap.used"
                      ]

    # metrices: time aggregation is maximum
    max_metric_ids = [
        "net.http.request.time"
    ]

    # metrices: time aggregation is summation
    sum_metric_ids = [
        "net.connection.count.out",
        "net.request.count.in"
    ]

    # metrices: core metrics used to perform adaptation analysis
    core_metrics = [
        ("cpu.quota.used.percent", "avg"),
        ("memory_limit_used_percent", "avg"),
        ("net_http_request_time", "max")
    ]

    monitor = Monitor(URL, APIKEY, GUID)
    analyzer = Analyzer(core_metrics)

    while True:
        # Fetch data from IBM Cloud
        for id in avg_metric_ids:
            monitor.fetch_data_from_ibm_cloud(id, "avg")

        for id in sum_metric_ids:
            monitor.fetch_data_from_ibm_cloud(id, "sum")

        for id in max_metric_ids:
            monitor.fetch_data_from_ibm_cloud(id, "max")
        print(f"Pulling metrics from IBM Cloud")
        analyzer.process_data()
        # Sleep for 5 minutes (300 seconds)
        time.sleep(300)

if __name__ == "__main__":
    main()