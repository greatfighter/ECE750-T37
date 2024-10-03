import os
import sys
import json
import time
import pandas as pd
from sdcclient import IbmAuthHelper, SdMonitorClient
from datetime import datetime
import subprocess

SLEEP = 300
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
        self.FILTER = 'kube_namespace_name="group-4"'
    
    # Function to fetch data from IBM Cloud
    def fetch_data_from_ibm(self, id, aggregation):
        metric = [
            {"id": "kubernetes.deployment.name"},
            {"id": id, "aggregations": {"time": aggregation, "group": "avg"}}
        ]

        ok, res = self.sdclient.get_data(metrics=metric, start_ts=self.START, end_ts=self.END, sampling_s=self.SAMPLING, filter=self.FILTER)
        if ok:
            data = res
        else:
            print(res)
            sys.exit(1)
        
        if not os.path.exists('datasets'):
            os.mkdir('datasets')
            print("The 'datasets' directory is created.")

        filename = "datasets/" + id.replace(".", "_") + "_" + aggregation + "_metric.json"
        with open(filename, "w") as outfile: 
            json.dump(data, outfile)

class Analyzer:
    def __init__(self, metrics):
        self.weight_cpu = 0.2
        self.weight_memory = 0.2
        self.weight_latency = 0.45
        self.weight_tps = 0.15
        self.weight_gc_time = 0.15
        self.weight_cost = 0.1
        self.metrics = metrics
        self.services = SERVICE_TO_USE

    def triggerAdaptation(self, cpu, memory, latency, tps, gc_time):
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"Time: {current_time}, CPU: {cpu:.2f}%, Memory: {memory:.2f}%, Latency: {latency:.2f}ms, TPS: {tps:.2f}, GC Time: {gc_time:.2f}ms")
        return cpu > 80 or memory > 80 or latency > 1000 or tps < 50 or gc_time > 500

    def calculate_utility(self, cpu, memory, latency, tps, gc_time, cost):
        cpu_utility = self.weight_cpu * self.utility_preference_cpu(cpu)
        memory_utility = self.weight_memory * self.utility_preference_memory(memory)
        latency_utility = self.weight_latency * self.utility_preference_latency(latency)
        tps_utility = self.weight_tps * self.utility_preference_tps(tps)
        gc_time_utility = self.weight_gc_time * self.utility_preference_gc_time(gc_time)
        cost_utility = self.weight_cost * self.utility_preference_cost(cost)
        return cpu_utility + memory_utility + latency_utility + tps_utility + gc_time_utility + cost_utility

    def utility_preference_linear(self, value, min_value, max_value):
        # Clamp the value to ensure it's within the expected range, normalize the value between 0 and 1
        value = max(min(value, max_value), min_value)
        return 1 - (value - min_value) / (max_value - min_value)

    def utility_preference_cpu(self, cpu):
        return self.utility_preference_linear(cpu, 0, 100)

    def utility_preference_memory(self, memory):
        return self.utility_preference_linear(memory, 0, 100)

    def utility_preference_latency(self, latency):
        return self.utility_preference_linear(latency, 0, 2e9)

    def utility_preference_tps(self, tps):
        return self.utility_preference_linear(tps, 50, 100)

    def utility_preference_gc_time(self, gc_time):
        return self.utility_preference_linear(gc_time, 0, 500)

    def utility_preference_cost(self, cost):
        if cost == "cpu" or cost == "memory":
            return 1
        else:
            return 0.5

    def create_dataframe(self, filename):
        with open(filename, 'r') as file:
            data = json.load(file)
        new_data = [{"timestamp": entry['t'], "service": entry['d'][0], "value": entry['d'][1]} for entry in data["data"]]
        return pd.DataFrame(new_data)

    def process_data(self):
        print("Processing data...")  # Debugging line
        service_to_index = {service: idx for idx, service in enumerate(SERVICE_TO_USE)}
        outputs = [[0] * len(self.metrics) for _ in range(len(SERVICE_TO_USE))]

        for idx, (metric_id, aggregation) in enumerate(self.metrics):
            filename = "datasets/" + metric_id.replace('.', '_') + "_" + aggregation + "_metric.json"
            print(f"Loading data from {filename}")  # Debugging line
            df = self.create_dataframe(filename)
            df_filtered = df[df['service'].isin(SERVICE_TO_USE)]
            aggregationData = df_filtered.groupby('service')
            avg_values = aggregationData['value'].mean()

            for service, avg_value in avg_values.items():
                print(f"Service {service} has average {avg_value} for {metric_id}")  # Debugging line
                if service in service_to_index:
                    index = service_to_index[service]
                    outputs[index][idx] = avg_value

        print(f"Data processing complete: {outputs}")  # Debugging line
        return outputs

class Planner:
    def __init__(self, analyzer):
        self.analyzer = analyzer  # Store a reference to the Analyzer instance

    def generate_adaptation_plan(self, adaptation_options):
        print(f"Length of adaptation_options: {len(adaptation_options)}")
        print(f"Adaptation options: {adaptation_options}")  # Debugging line

        optimal_plans = [None for _ in range(len(adaptation_options))]
        print(f"Length of optimal_plans: {len(optimal_plans)}")  # Debugging line

        for idx, plans in enumerate(adaptation_options):
            print(f"Processing plans for index {idx}: {plans}")  # Debugging line
            
            if plans:  # Check if plans is not empty
                option = {'utility': -float('inf'), 'plan': None}
                
                if isinstance(plans, list) and len(plans) == 5:  # Check if it's a list and has 5 elements
                    cpu, memory, latency, tps, gc_time = plans
                    
                    # Calculate utility using the Analyzer's method
                    utility = self.analyzer.calculate_utility(cpu, memory, latency, tps, gc_time, cost=0)
                    print(f"Calculated utility for plan {plans}: {utility}")  # Debugging line
                    
                    if utility > option['utility']:
                        print(f"New optimal plan for index {idx} with utility {utility}")
                        option = {'utility': utility, 'plan': plans}

                if option['utility'] > -float('inf'):
                    optimal_plans[idx] = option['plan']
                    
            print(f"Optimal plan selected for index {idx}: {optimal_plans[idx]}")  # Debugging line
        return optimal_plans

class Executor:
    def __init__(self):
        pass

    def execute(self, adaptation_plans, configurations):
        for idx, adaptation_plan in enumerate(adaptation_plans):
            if adaptation_plan:
                print(f"Executing plan {adaptation_plan} for service {adaptation_plan['service']}")  # Debugging line
                cpu = adaptation_plan["cpu"]
                memory = adaptation_plan["memory"]
                replica = adaptation_plan['replica']
                service = adaptation_plan['service']
                command = f"./config.sh cpu={cpu} memory={memory} replica={replica} service={service}"
                res = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

                if res.returncode == 0:
                    configurations[idx] = adaptation_plan
                    print(f"Execution successful for {service}:\n{res.stdout}")  # Debugging line
                else:
                    print(f"Adaptation failed for {service} with error:\n{res.stderr}")  # Debugging line

def main():
    URL = "https://ca-tor.monitoring.cloud.ibm.com"
    APIKEY = "E5wgqSh1yPF_s_0NSLPF94zSA3mK2fx1go3GUQqxbFde"
    GUID = "3fed93bc-00f4-4651-8ce2-e73ba4b9a918"
    SLEEP = 300  # Define SLEEP interval (in seconds)

    avg_metric_ids = [
        "cpu.quota.used.percent",          
        "memory.limit.used.percent",       
        "jvm.gc.global.time"
    ]

    max_metric_ids = [
        "net.http.request.time" 
    ]

    sum_metric_ids = [
        "net.request.count.in"
    ]

    core_metrics = [
        ("cpu.quota.used.percent", "avg"),
        ("memory.limit.used.percent", "avg"),
        ("net.http.request.time", "max"),
        ("net.request.count.in", "sum"),
        ("jvm.gc.global.time", "avg")
    ]

    # Instantiate the Monitor, Analyzer, Planner, and Executor
    monitor = Monitor(URL, APIKEY, GUID)
    analyzer = Analyzer(core_metrics)
    planner = Planner(analyzer)  # Pass analyzer instance
    executor = Executor()

    current_configurations = [{"cpu": 500, "memory": 512, "replica": 1} for _ in range(3)]

    while True:
        try:
            # Fetch data for average metrics
            for id in avg_metric_ids:
                monitor.fetch_data_from_ibm(id, "avg")

            # Fetch data for sum metrics
            for id in sum_metric_ids:
                monitor.fetch_data_from_ibm(id, "sum")

            # Fetch data for max metrics
            for id in max_metric_ids:
                monitor.fetch_data_from_ibm(id, "max")

            # Process the data
            adaptation_options = analyzer.process_data()
            optimal_plans = planner.generate_adaptation_plan(adaptation_options)
            executor.execute(optimal_plans, current_configurations)

        except Exception as e:
            print(f"An error occurred: {e}")  # Basic error handling

        time.sleep(SLEEP)  # Wait before the next cycle

if __name__ == "__main__":
    main()