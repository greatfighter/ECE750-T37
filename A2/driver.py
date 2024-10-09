import os
import sys
import json
import time
import pandas as pd
from sdcclient import IbmAuthHelper, SdMonitorClient
from datetime import datetime
import subprocess

SLEEP = 60
SERVICE_TO_USE = [
    'acmeair-mainservice',
    'acmeair-authservice',
    'acmeair-flightservice',
    'acmeair-customerservice',
    'acmeair-bookingservice'
]

SERVICE_CONFIG = [{"cpu": 500, "memory": 512, "replica": 1} for _ in range(len(SERVICE_TO_USE))]

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
        self.weight_cpu = 0.2
        self.weight_memory = 0.2
        self.weight_latency = 0.45
        self.weight_tps = 0.15
        self.weight_gc_time = 0.15
        self.weight_cost = 0.1
        self.metrics = metrics
        self.services = SERVICE_TO_USE

    def triggerAdaptation(self, current_status):
        cpu = current_status[0]
        memory = current_status[1]
        latency = current_status[2]
        tps = current_status[3]
        gc_time = current_status[4]
        current_time = datetime.now().strftime('%H:%M:%S')
        print(f"Time: {current_time}, CPU: {cpu:.2f}%, Memory: {memory:.2f}%, Latency: {latency:.2f}ms, TPS: {tps:.2f}, GC Time: {gc_time:.2f}ms")
        if cpu > 80 or memory > 80 or latency > 1e9 or gc_time > 500:
            return True
        elif cpu < 10 or memory < 10:
            return True
        return False

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


    def adjust_resources(self, current_status, current_config,
                     cpu_upper_threshold=80, cpu_lower_threshold=10, 
                     mem_upper_threshold=80, mem_lower_threshold=10, 
                     latency_threshold=100, tps_threshold=500, gc_time_threshold=30, 
                     max_replicas=4, min_replicas=1, 
                     min_cpu=100, min_memory=256):
        """
        Adjust resources based on CPU and memory utilization, ensuring that replicas do not exceed the maximum limit
        and do not go below the minimum limit.
        
        Parameters:
        - cpu_util: Current CPU utilization (0-1)
        - mem_util: Current memory utilization (0-1)
        - replicas: Current number of replicas
        - cpu_upper_threshold: Upper CPU utilization limit, if exceeded, CPU resources should be increased
        - cpu_lower_threshold: Lower CPU utilization limit, if under this value, CPU resources should be decreased
        - mem_upper_threshold: Upper memory utilization limit, if exceeded, memory resources should be increased
        - mem_lower_threshold: Lower memory utilization limit, if under this value, memory resources should be decreased
        - max_replicas: Maximum number of replicas
        - min_replicas: Minimum number of replicas
        
        Returns:
        - Adjusted CPU, memory, and replica count actions
        """
        # print (current_status)
        cpu_util = current_status[0]
        mem_util = current_status[1]
        latency = current_status[2]
        tps = current_status[3]
        gc_time = current_status[4]

        current_cpu = current_config["cpu"]
        current_memory = current_config["memory"]
        current_config["memory"] += 256
        
        # # Determine whether to adjust CPU resources
        # if cpu_util > cpu_upper_threshold:
        #     current_config["cpu"] += 100 # "increase_cpu"
        # elif cpu_util < cpu_lower_threshold and current_config["cpu"] > min_cpu:
        #     current_config["cpu"] -= 100 # "decrease_cpu"
        
        # # Determine whether to adjust memory resources
        # if mem_util > mem_upper_threshold:
        #     current_config["memory"] += 256 # "increase_memory"
        # elif mem_util < mem_lower_threshold and current_config["memory"] > min_memory:
        #     current_config["memory"] -= 256 # "decrease_memory"
        
        # # Determine whether to increase replicas
        # if cpu_util > cpu_upper_threshold and mem_util > mem_upper_threshold and current_config["replica"] < max_replicas:
        #     current_config["replica"] += 1 # "increase_replicas"
        #     current_cpu["cpu"] = current_cpu
        #     current_config["memory"] = current_memory
        # # Determine whether to decrease replicas
        # elif cpu_util < cpu_lower_threshold and mem_util < mem_lower_threshold and current_config["replica"] > min_replicas:
        #     current_config["replica"] -= 1 # "decrease_replicas"
        #     current_cpu["cpu"] = current_cpu
        #     current_config["memory"] = current_memory
        
        # if latency > latency_threshold:
        #     if cpu_util > cpu_upper_threshold:
        #         current_config["cpu"] += 100 # "increase_cpu"
        #     elif mem_util < mem_upper_threshold:
        #         current_config["memory"] += 256 # "increase_memory"
        
        # # Adjust for low TPS: increase replicas or CPU
        # if tps < tps_threshold:
        #     if cpu_util > cpu_upper_threshold:
        #         current_config["cpu"] += 100 # "increase_cpu"
        #     elif current_config["replica"] < max_replicas:
        #         current_config["replica"] += 1 # "increase_replicas"
        
        # # Adjust for high GC time: increase memory
        # if gc_time > gc_time_threshold and mem_util > mem_upper_threshold:
        #     current_config["memory"] += 256 # "increase_memory"

        return current_config


    def process_data(self, current_config):
        # print("Processing data...")  # Debugging line
        service_to_index = {service: idx for idx, service in enumerate(SERVICE_TO_USE)}
        current_status = [[0] * len(self.metrics) for _ in range(len(SERVICE_TO_USE))]
        adaptation_options = [None for _ in range(len(SERVICE_TO_USE))]

        for idx, (metric_id, aggregation) in enumerate(self.metrics):
            filename = "datasets/" + metric_id.replace('.', '_') + "_" + aggregation + "_metric.json"
            # print(f"Loading data from {filename}")  # Debugging line
            df = self.create_dataframe(filename)
            df_filtered = df[df['service'].isin(SERVICE_TO_USE)]
            aggregationData = df_filtered.groupby('service')
            avg_values = aggregationData['value'].mean()

            for service, avg_value in avg_values.items():
                # print(f"Service {service} has average {avg_value} for {metric_id}")  # Debugging line
                if service in service_to_index:
                    index = service_to_index[service]
                    current_status[index][idx] = avg_value

        for i in range(5):
            print ("##########################")
            print(f"Service: {SERVICE_TO_USE[i]}")  # Print the current service name
            adaptation = self.triggerAdaptation(current_status[i])
            if adaptation:
                print(f"{self.services[i]} requires adaptation")
                print("current config:", current_config[i])
                adaptation_options[i] = self.adjust_resources(current_status[i], current_config[i])
                print("adjust config:", current_config[i])
            else:
                print(f"No adaptation required for {self.services[i]}")

        # print(f"Data processing complete: {outputs}")  # Debugging line
        return adaptation_options

class Planner:
    def __init__(self, analyzer):
        self.analyzer = analyzer  # Store a reference to the Analyzer instance

    def generate_adaptation_plan(self, adaptation_options):
        # print(f"Length of adaptation_options: {len(adaptation_options)}")
        print(f"Adaptation options: {adaptation_options}")  # Debugging line

        optimal_plans = [None for _ in range(len(adaptation_options))]
        # print(f"Length of optimal_plans: {len(optimal_plans)}")  # Debugging line

        for idx, plans in enumerate(adaptation_options):
            print(f"Processing plans for index {idx}: {plans}")  # Debugging line
            
            if plans:  # Check if plans is not empty
                option = {'utility': -float('inf'), 'plan': None}
                
                if isinstance(plans, list) and len(plans) == 5:  # Check if it's a list and has 5 elements
                    # cpu, memory, latency, tps, gc_time = plans
                    
                    # Calculate utility using the Analyzer's method
                    # utility = self.analyzer.calculate_utility(cpu, memory, latency, tps, gc_time, cost=0)
                    # print(f"Calculated utility for plan {plans}: {utility}")  # Debugging line
                    
                    if utility > option['utility']:
                        print(f"New optimal plan for index {idx} with utility {utility}")
                        option = {'utility': utility, 'plan': plans}

                if option['utility'] > -float('inf'):
                    optimal_plans[idx] = option['plan']
                    
            print(f"Optimal plan selected for index {idx}: {optimal_plans[idx]}")  # Debugging line
        print(optimal_plans)
        print(option)
        return optimal_plans
    
    def translate_optimal_to_adaptation_plan(self, optimal_plans):
        adaptation_plans = {}  # Initialize an empty dictionary for adaptation plans
        
        for idx, plan in enumerate(optimal_plans):
            if plan:
                try:
                    # Unpack the optimal plan values
                    cpu, memory, latency, tps, gc_time = plan  # gc_time is unpacked but not used in adaptation

                    # Define thresholds based on the new scale
                    cpu_threshold = 2.0  # 2 CPU cores as threshold
                    memory_threshold = 60  # 60 GB of memory
                    latency_threshold = 1000000  # 1,000,000 µs (1 second)
                    tps_threshold = 2.0  # Transactions per second threshold

                    # Create the adaptation plan for this service
                    adaptation_plan = {
                        "cpu": cpu,
                        "memory": memory,
                        "replica": 1  # Default 1 pod
                    }

                    # Logic for increasing memory by 4GB if memory usage exceeds the threshold
                    if memory > memory_threshold:
                        adaptation_plan["memory"] = memory + 4  # Increase memory by 4GB
                        print(f"Increasing memory for service_{idx} by 4GB")

                    # Logic for increasing CPU if CPU usage exceeds the threshold
                    if cpu > cpu_threshold:
                        adaptation_plan["cpu"] = cpu + 0.5  # Increase CPU by 0.5 cores
                        print(f"Increasing CPU for service_{idx} by 0.5 cores")

                    # Logic for increasing the number of pods if latency exceeds the threshold
                    if latency > latency_threshold:
                        adaptation_plan["replica"] += 1  # Increase the number of replicas by 1
                        print(f"Increasing pods for service_{idx} due to high latency")

                    # Logic for increasing the number of pods if TPS exceeds the threshold
                    if tps > tps_threshold:
                        adaptation_plan["replica"] += 1  # Increase the number of replicas by 1
                        print(f"Increasing pods for service_{idx} due to high TPS")

                    # Add the adaptation plan to the dictionary with the service name as the key
                    adaptation_plans[f"service_{idx}"] = adaptation_plan
                
                except IndexError as e:
                    print(f"IndexError at service_{idx}: {e}, Plan: {plan}")
                    adaptation_plans[f"service_{idx}"] = None  # Add None to skip this service
                
                except Exception as e:
                    print(f"An unexpected error occurred at service_{idx}: {e}, Plan: {plan}")
                    adaptation_plans[f"service_{idx}"] = None  # Fallback to None if there's an error
            else:
                adaptation_plans[f"service_{idx}"] = None

        return adaptation_plans


class Executor:
    def __init__(self):
        pass

    # def execute(self, adaptation_plans, configurations):
    #     for idx, adaptation_plan in enumerate(adaptation_plans):
    #         if adaptation_plan:
    #             print(f"Executing plan {adaptation_plan} for service {adaptation_plan['service']}")  # Debugging line
    #             cpu = adaptation_plan["cpu"]
    #             memory = adaptation_plan["memory"]
    #             replica = adaptation_plan['replica']
    #             service = adaptation_plan['service']
    #             command = f"./config.sh cpu={cpu} memory={memory} replica={replica} service={service}"
    #             res = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    #             if res.returncode == 0:
    #                 configurations[idx] = adaptation_plan
    #                 print(f"Execution successful for {service}:\n{res.stdout}")  # Debugging line
    #             else:
    #                 print(f"Adaptation failed for {service} with error:\n{res.stderr}")  # Debugging line

    # def execute(self, adaptation_plans, configurations):
    #     for idx, adaptation_plan in enumerate(adaptation_plans):
    #         if adaptation_plan:
    #             print(f"Executing plan {adaptation_plan} for service {adaptation_plan[3]}")  # Assuming 'service' is at index 3
                
    #             cpu = adaptation_plan[0]      # Assuming CPU is at index 0
    #             memory = adaptation_plan[1]   # Assuming memory is at index 1
    #             replica = adaptation_plan[2]  # Assuming replica is at index 2
    #             service = adaptation_plan[3]  # Assuming service is at index 3
                
    #             command = f"./config.sh cpu={cpu} memory={memory} replica={replica} service={service}"
    #             res = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    #             if res.returncode == 0:
    #                 configurations[idx] = adaptation_plan
    #                 print(f"Execution successful for {service}:\n{res.stdout}")  # Debugging line
    #             else:
    #                 print(f"Adaptation failed for {service} with error:\n{res.stderr}")  # Debugging line

    def execute(self, configurations):
        for i in range(len(SERVICE_TO_USE)):
            print ("Service: ", SERVICE_TO_USE[i])
            print ("New config: ", configurations[i])

            cpu = configurations[i]["cpu"]
            memory = configurations[i]["memory"]
            replica = configurations[i]["replica"]
            print(f"CPU: {cpu}, Memory: {memory}, Replica: {replica}")
            command = f"config.sh cpu={cpu} memory={memory} replica={replica} service={SERVICE_TO_USE[i]}"
            print(f"Command to execute: {command}")
            res = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Print command output and error
            # print(f"Command output: {res.stdout}")
            # print(f"Command error: {res.stderr}")
            if res.returncode == 0:
            #     configurations[service_index] = plan  # Save the successful adaptation plan
                print(f"Execution successful for {SERVICE_TO_USE[i]}:\n{res.stdout}")
            else:
                print(f"Adaptation failed for {SERVICE_TO_USE[i]} with error:\n{res.stderr}")


        # for service_name, plan in adaptation_plans.items():  # Iterating over service_name and plan
        #     service_index = int(service_name.split('_')[1]) 
        #     print(f"Executing plan for {service_name}")
        #     print(f"Adaptation plan for {service_name}: {plan}")

        #     # Extracting parameters from the plan (inner dictionary)
        #     cpu = plan["cpu"]
        #     memory = plan["memory"]
        #     replica = plan["replica"]

        #     # Debugging output
        #     print(f"CPU: {cpu}, Memory: {memory}, Replica: {replica}")

        #     command = f"./config.sh cpu={cpu} memory={memory} replica={replica} service={service_name}"
        #     print(f"Command to execute: {command}")

        #     # # Execute the command
        #     res = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        #     # # Print command output and error
        #     # print(f"Command output: {res.stdout}")
        #     # print(f"Command error: {res.stderr}")

        #     # # Save the successful configuration, otherwise log an error
        #     if res.returncode == 0:
        #         configurations[service_index] = plan  # Save the successful adaptation plan
        #         print(f"Execution successful for {service_name}:\n{res.stdout}")
        #     else:
        #         print(f"Adaptation failed for {service_name} with error:\n{res.stderr}")

        
def main():
    URL = "https://ca-tor.monitoring.cloud.ibm.com"
    APIKEY = "E5wgqSh1yPF_s_0NSLPF94zSA3mK2fx1go3GUQqxbFde"
    GUID = "3fed93bc-00f4-4651-8ce2-e73ba4b9a918"

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
    # planner = Planner(analyzer)  # Pass analyzer instance
    executor = Executor()

    current_configurations = SERVICE_CONFIG

    while True:
        # Fetch data for average metrics
        for id in avg_metric_ids:
            monitor.fetch_data_from_ibm(id, "avg")

        # Fetch data for sum metrics
        for id in sum_metric_ids:
            monitor.fetch_data_from_ibm(id, "sum")

        # Fetch data for max metrics
        for id in max_metric_ids:
            monitor.fetch_data_from_ibm(id, "max")
        print(f"Pulling metrics from IBM Cloud")
        # Process the data
        adaptation_options = analyzer.process_data(current_configurations)
        # optimal_plans = planner.generate_adaptation_plan(adaptation_options)
        # adaptation_plans = planner.translate_optimal_to_adaptation_plan(optimal_plans)
        executor.execute(adaptation_options)
        current_configurations = adaptation_options

        time.sleep(SLEEP)  # Wait before the next cycle

if __name__ == "__main__":
    main()