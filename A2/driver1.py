import os
import sys
import json
import subprocess
import time
import pandas as pd
from sdcclient import IbmAuthHelper, SdMonitorClient

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
            # Debug: print the fetched data for verification
            # print(f"Data fetched for {id} with aggregation {aggregation}: {data}")
        else:
            print(f"Error fetching data: {res}")
            sys.exit(1)
        
        # Save data to JSON file
        if not os.path.exists('datasets'):
            os.mkdir('datasets')
            print("The 'datasets' directory is created.")

        filename = "datasets/" + id.replace(".", "_") + "_" + aggregation + "_metric.json"
        with open(filename, "w") as outfile: 
            json.dump(data, outfile)

        # return data  # Make sure to return the data

class Analyzer:
    def __init__(self, core_metrics):
        self.core_metrics = core_metrics

    def process_data(self):
        all_data = []
        for metric_id, aggregation in self.core_metrics:
            filename = f"datasets/{metric_id.replace('.', '_')}_{aggregation}_metric.json"
            
            # Load the data from the saved JSON file
            if os.path.exists(filename):
                with open(filename) as f:
                    data = json.load(f)
                print(f"Loaded data for {metric_id}: {data}")  # Debugging info
            else:
                print(f"Error: File {filename} does not exist!")
                continue  # Skip to the next metric

            # Make sure data is valid
            if data is None or 'data' not in data:
                print(f"Error: Invalid data for {metric_id}.")
                continue  # Skip to the next metric
            
            df = pd.DataFrame(data['data'])
            
            if df.empty:
                print(f"Error: No data available for {metric_id}.")
                continue

            # Group by service name, assuming 'service' is the correct column
            try:
                aggregation_data = df.groupby('service').mean()
                all_data.append(aggregation_data)
            except KeyError as e:
                print(f"KeyError: {e} for {metric_id}. Check your data structure.")
                continue
        
        return all_data

class Analyzer:
    def __init__(self, metrics):
        self.weight_cpu = 0.2
        self.weight_memory = 0.2
        self.weight_latency = 0.45
        self.weight_cost = 0.15
        self.metrics = metrics
        self.memory_lower_bound = 512
        self.memory_upper_bound = 1024
        self.replica_lower_bound = 1
        self.replica_upper_bound = 3
        self.configuration_data = self.load_configuration_data()
        self.loads = ["low", "medium", "high"]
        self.services = ['acmeair-bookingservice', 'acmeair-customerservice', 'acmeair-flightservice']

    def load_configuration_data(self):
        with open("configuration.json", "r") as file:
            return json.load(file)

    def triggerAdaptation(self, cpu, memory, latency):
        print(f"CPU: {cpu:.2f}, memory: {memory:.2f}, latency: {latency:.2f}")
        if cpu > 75 or memory > 75 or latency > 2e7:
            return (True, True)
        elif cpu < 25 or memory < 25:
            return (True, False)
        return (False, False)
    
    def utility_preference_cpu(self, cpu):
        if cpu < 25:
            return 1
        elif cpu < 75:
            return 0.5
        else:
            return 0

    def utility_preference_memory(self, memory):
        if memory < 25:
            return 1
        elif memory < 75:
            return 0.5
        else:
            return 0
    
    def utility_preference_latency(self, latency):
        if latency < 1e7:
            return 1
        elif latency < 2e7:
            return 0.5
        else:
            return 0
    
    def utility_preference_cost(self, cost):
        return 1 if cost == "memory" else 0.5

    def calculate_utility(self, cpu_usage, memory_usage, latency, cost):
        cpu_utility = self.weight_cpu * self.utility_preference_cpu(cpu_usage)
        memory_utility = self.weight_memory * self.utility_preference_memory(memory_usage)
        latency_utility = self.weight_latency * self.utility_preference_latency(latency)
        cost_utility = self.weight_cost * self.utility_preference_cost(cost)
        return cpu_utility + memory_utility + latency_utility + cost_utility

    def determine_request_load(self, service):
        filename = "datasets/net_request_count_in_sum_metric.json"
        df = self.create_dataframe(filename)
        aggregationData = df.groupby('service')
        avg_values = aggregationData['value'].mean()
        load = "low"
        if avg_values.loc[service] > 2000:
            load = self.loads[2]
        elif avg_values.loc[service] > 1000:
            load = self.loads[1]
        print(f"request number for {service} is {avg_values.loc[service]}, {load} traffic")
        return load

    # def create_dataframe(self, filename):
    #     with open(filename, 'r') as file:
    #         data = json.load(file)
    #     new_data = []
    #     # Ensure that 'service' exists in the data
    #     for entry in data["data"]:
    #         try:
    #             new_data.append({
    #                 "timestamp": entry['t'],
    #                 "service": entry['d'][0],  # Ensure entry['d'][0] contains the service name
    #                 "value": entry['d'][1]
    #             })
    #         except KeyError as e:
    #             print(f"KeyError: {e} - Check the structure of your JSON data.")
    #             print(f"Problematic entry: {entry}")
    #             continue

    #     # If 'service' doesn't exist, adjust accordingly
    #     if not new_data:
    #         raise ValueError(f"No valid 'service' entries found in {filename}. Check the structure.")

    def create_dataframe(self, filename):
        # Load the data from the JSON file into a DataFrame
        try:
            with open(filename) as f:
                data = json.load(f)
            if 'data' in data:
                df = pd.DataFrame(data['data'])  # Create DataFrame from 'data' key
                if 'd' in df.columns:
                    # Split the 'd' column into 'service' and 'value'
                    df[['service', 'value']] = pd.DataFrame(df['d'].tolist(), index=df.index)
                    return df[['service', 'value']]  # Return DataFrame with only 'service' and 'value' columns
                else:
                    print(f"Error: 'd' column not found in {filename}")
                    return pd.DataFrame()  # Return empty DataFrame if 'd' column is missing
            else:
                print(f"Error: 'data' key not found in {filename}")
                return pd.DataFrame()  # Return an empty DataFrame if 'data' key is missing
        except FileNotFoundError:
            print(f"Error: File {filename} not found.")
            return pd.DataFrame()  # Return an empty DataFrame if file not found
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading or processing file {filename}: {e}")
            return pd.DataFrame()  # Return empty DataFrame if there's an issue


    # def process_data(self, current_configurations):
    #     adaptation_options = [None for _ in range(3)]
    #     outputs = [[0]*len(self.metrics) for _ in range(3)]
    #     for idx, (metric_id, aggregation) in enumerate(self.metrics):
    #         filename = "datasets/" + metric_id.replace(".", "_") + "_" + aggregation + "_metric.json"
    #         df = self.create_dataframe(filename)
    #         aggregationData = df.groupby('service')
    #         avg_values = aggregationData['value'].mean()
    #         for i in range(3):
    #             outputs[i][idx] = avg_values.loc[self.services[i]]

    #     for i in range(3):
    #         cpu = outputs[i][0]
    #         memory = outputs[i][1]
    #         latency = outputs[i][2]
    #         adaptation, busy = self.triggerAdaptation(cpu, memory, latency)
    #         if adaptation:
    #             print(f"{self.services[i]} requires adaptation")
    #             adaptation_options[i] = self.generate_adaptation_options(current_configurations[i], self.services[i], busy)
    #         else:
    #             print(f"No adaptation required for {self.services[i]}")
    #     return adaptation_options

    def process_data(self, current_configurations):
        adaptation_options = [None for _ in range(3)]
        outputs = [[0]*len(self.metrics) for _ in range(3)]

        for idx, (metric_id, aggregation) in enumerate(self.metrics):
            filename = "datasets/" + metric_id.replace(".", "_") + "_" + aggregation + "_metric.json"
            df = self.create_dataframe(filename)

            # Debugging: Print the DataFrame structure
            print(f"DataFrame for {metric_id}:")
            print(df.head())  # Print the first few rows of the DataFrame

            # Check if 'service' and 'value' columns exist in the DataFrame
            if 'service' not in df.columns or 'value' not in df.columns:
                print(f"Error: Missing 'service' or 'value' columns in data for {metric_id}.")
                continue

            # Group by 'service'
            aggregationData = df.groupby('service')
            avg_values = aggregationData['value'].mean()

            # Debugging: Print the computed average values
            print(f"Average values for {metric_id}:")
            print(avg_values)

            # Ensure that the services exist in the aggregated data
            for i in range(3):
                if self.services[i] in avg_values.index:
                    outputs[i][idx] = avg_values.loc[self.services[i]]
                else:
                    print(f"Error: Service {self.services[i]} not found in data for {metric_id}.")
                    outputs[i][idx] = 0  # Handle missing service data

        for i in range(3):
            cpu = outputs[i][0]
            memory = outputs[i][1]
            latency = outputs[i][2]
            adaptation, busy = self.triggerAdaptation(cpu, memory, latency)
            if adaptation:
                print(f"{self.services[i]} requires adaptation")
                adaptation_options[i] = self.generate_adaptation_options(current_configurations[i], self.services[i], busy)
            else:
                print(f"No adaptation required for {self.services[i]}")
        return adaptation_options
    
    def fetch_configuration_data(self, option):
        valid = self.check_validity(option)
        print(f"Validity of option: {valid}")
        
        if valid:
            # Construct the key according to the format used in self.configuration_data
            key = f"{option['service']}_{option['replica']}_{option['memory']}_{option['load']}"
            print(f"Constructed key for fetching data: {key}")
            
            # Check if the key exists in self.configuration_data
            if key in self.configuration_data:
                fetched_data = self.configuration_data[key]
                print(f"Fetched configuration data: {fetched_data} for key: {key}")
                return fetched_data
            else:
                print(f"Key not found in configuration data: {key}")
        print("Invalid option provided.")
        return None

    def check_validity(self, option):
        # return (self.memory_lower_bound <= option['memory'] <= self.memory_upper_bound) and \
        #        (self.replica_lower_bound <= option['replica'] <= self.replica_upper_bound)
        return True

    def generate_adaptation_option(self, cpu, memory, replica, cost, service, busy, load):
        option = {
            "cpu": cpu,
            "memory": memory,
            "replica": replica,
            "service": service,
            "load": load
        }
        
        print(f"Generating adaptation option with parameters: {option}")
        
        # Make sure the keys in option match expected values
        print(f"Option details - CPU: {cpu}, Memory: {memory}, Replica: {replica}, Service: {service}, Load: {load}")
        
        data = self.fetch_configuration_data(option)
        
        if data:
            option["utility"] = self.calculate_utility(data['cpu_percent'], data['memory_percent'], data['response_time'], cost)
            
            # Adaptation strategy prints
            if busy and cost == "memory":
                print(f"Adaptation Strategy: increase memory to {memory} for {service}")
            elif busy and cost == "replica":
                print(f"Adaptation Strategy: increase replica to {replica} for {service}")
            elif not busy and cost == "memory":
                print(f"Adaptation Strategy: decrease memory to {memory} for {service}")
            else:
                print(f"Adaptation Strategy: decrease replica to {replica} for {service}")
            
            return option
        else:
            print(f"Error: Failed to fetch configuration data for option {option}")
        return None

    def generate_adaptation_options(self, configuration, service, busy):
        adaptation_options = [0, 0]
        cpu = configuration["cpu"]
        memory = configuration["memory"]
        replica = configuration["replica"]
        load = self.determine_request_load(service)

        if busy:
            adaptation_options[0] = self.generate_adaptation_option(cpu, memory + 256, replica, "memory", service, busy, load)
        
            # Ensure replica does not become zero
            if replica + 1 > 0:
                adaptation_options[1] = self.generate_adaptation_option(cpu, memory, replica + 1, "replica", service, busy, load)
        else:
        # Ensure memory does not go below 256 (or another minimum threshold)
            if memory - 256 >= 256:
                adaptation_options[0] = self.generate_adaptation_option(cpu, memory - 256, replica, "memory", service, busy, load)
            else:
                adaptation_options[0] = self.generate_adaptation_option(cpu, 256, replica, "memory", service, busy, load)  # Minimum memory threshold
        
        # Ensure replica does not become zero
        if replica - 1 > 0:
            adaptation_options[1] = self.generate_adaptation_option(cpu, memory, replica - 1, "replica", service, busy, load)

        return adaptation_options

class Planner:
    def __init__(self):
        pass
    
    def generate_adaptation_plan(self, adaptation_options):
        optimal_plans = [None for _ in range(3)] 
        for idx, plans in enumerate(adaptation_options):
            if plans:
                option = {'utility': 0}
                for plan in plans:
                    if plan and option['utility'] < plan['utility']:
                        option = plan
                if option['utility'] > 0:
                    optimal_plans[idx] = option
        return optimal_plans

class Executor:
    def __init__(self):
        pass

    def execute(self, adaptation_plans, configurations):
        for idx, adaptation_plan in enumerate(adaptation_plans):
            if adaptation_plan:
                cpu = adaptation_plan["cpu"]
                memory = adaptation_plan["memory"]
                replica = adaptation_plan['replica']
                service = adaptation_plan['service']
                command = f"./config.sh cpu={cpu} memory={memory} replica={replica} service={service}"
                print(f"Executing command: {command}")
                subprocess.run(command, shell=True)
                print("Completed adaptation for service:", service)

def main():
    URL = "https://ca-tor.monitoring.cloud.ibm.com"
    APIKEY = "E5wgqSh1yPF_s_0NSLPF94zSA3mK2fx1go3GUQqxbFde"
    GUID = "3fed93bc-00f4-4651-8ce2-e73ba4b9a918"
    SLEEP = 300  # Define SLEEP interval (in seconds)

    avg_metric_ids = [
        "cpu.quota.used.percent",          
        "memory.limit.used.percent",       
        "net.http.request.time",
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
        ("net.http.request.time", "avg"),
        ("net.request.count.in", "sum"),
        ("jvm.gc.global.time", "avg")
    ]

    # Instantiate the Monitor, Analyzer, Planner, and Executor
    monitor = Monitor(URL, APIKEY, GUID)
    analyzer = Analyzer(core_metrics)
    planner = Planner()  # Pass analyzer instance
    executor = Executor()

    current_configurations = [{"cpu": 500, "memory": 512, "replica": 1} for _ in range(5)]

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
            adaptation_options = analyzer.process_data(current_configurations)
            optimal_plans = planner.generate_adaptation_plan(adaptation_options)
            # adaptation_plans = planner.translate_optimal_to_adaptation_plan(optimal_plans)
            executor.execute(optimal_plans, current_configurations)

        except Exception as e:
            print(f"An error occurred: {e}")  # Basic error handling

        time.sleep(SLEEP)  # Wait before the next cycle

if __name__ == "__main__":
    main()