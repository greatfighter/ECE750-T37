import json
import matplotlib.pyplot as plt
from matplotlib.dates import date2num
import datetime

# Load JSON data
def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Process and plot data
def plot_graph(data):
    # Extract time and values
    times = []
    metrics = {}

    for entry in data['data']:
        timestamp = datetime.datetime.fromtimestamp(entry['t'])
        time_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        
        if time_str not in metrics:
            metrics[time_str] = {}
        
        service_name = entry['d'][0] if entry['d'][0] else 'Unknown'
        value = entry['d'][1]
        
        if service_name not in metrics[time_str]:
            metrics[time_str][service_name] = 0
        
        metrics[time_str][service_name] += value
    
    # Plot
    plt.figure(figsize=(14, 8))

    for service in set(service for subdict in metrics.values() for service in subdict):
        service_data = [metrics[time].get(service, 0) for time in sorted(metrics)]
        plt.plot(sorted(metrics), service_data, label=service)
    
    plt.xlabel('Time')
    plt.ylabel('Value')
    plt.title('Service Metrics Over Time')
    plt.xticks(rotation=45)
    plt.legend()
    plt.tight_layout()

    plt.show()

# Main function
def main():
    file_path = '/Users/spencer/Desktop/Waterloo/class materials/ECE750-T37/A1/Drivers/datasets/cpu_used_percent_avg_metric.json'  
    data = load_data(file_path)
    plot_graph(data)

if __name__ == '__main__':
    main()