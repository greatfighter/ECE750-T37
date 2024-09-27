import json
import matplotlib.pyplot as plt
import datetime

# Load JSON data
def load_data(file_path):
    with open(file_path, 'r') as file:
        return json.load(file)

# Process and plot data
def plot_graph(data, ax, title):
    # Extract time and values
    metrics = {}

    # Define the services to plot
    services_to_plot = [
        'acmeair-mainservice',
        'acmeair-authservice',
        'acmeair-flightservice',
        'acmeair-customerservice',
        'acmeair-bookingservice'
    ]

    for entry in data['data']:
        timestamp = datetime.datetime.fromtimestamp(entry['t'])
        time_str = timestamp.strftime('%H:%M:%S')
        
        if time_str not in metrics:
            metrics[time_str] = {}
        
        service_name = entry['d'][0] if entry['d'][0] else 'Unknown'
        value = entry['d'][1]
        
        if service_name in services_to_plot:
            if service_name not in metrics[time_str]:
                metrics[time_str][service_name] = 0
            metrics[time_str][service_name] += value
    
    sorted_times = sorted(metrics)

    for service in services_to_plot:
        service_data = [metrics[time].get(service, 0) for time in sorted_times]
        ax.plot(sorted(metrics), service_data, label=service)
    
    ax.set_xlabel('Time')
    ax.set_ylabel('Value')
    ax.set_title(title)
    ax.set_xticks(range(0, len(sorted_times), 3))
    ax.set_xticklabels([sorted_times[i] for i in range(0, len(sorted_times), 3)], rotation=45, fontsize=8)
    ax.legend()

# Main function to generate the combined graph
def main():
    file_paths = [
        'datasets/memory_limit_used_percent_avg_metric.json',
        'datasets/cpu_quota_used_percent_avg_metric.json',
        'datasets/jvm_gc_global_time_avg_metric.json',
        'datasets/net_http_request_time_max_metric.json',
        'datasets/net_request_count_in_sum_metric.json'
    ]

    titles = [
        'Memory Limit Used Percent',
        'CPU Quota Used Percent',
        'JVM GC Global Time',
        'Net HTTP Request Time Max',
        'Net Request Count In Sum'
    ]

    # Create a figure with 2 rows and 3 columns (6 subplots)
    fig, axes = plt.subplots(nrows=3, ncols=2, figsize=(12, 18))

    # Flatten the axes array for easy iteration
    axes = axes.flatten()

    # Loop over file paths, load data, and plot in each subplot
    for i, file_path in enumerate(file_paths):
        data = load_data(file_path)
        plot_graph(data, axes[i], titles[i])

    # Hide the last subplot since we only have 5 datasets
    axes[-1].axis('off')

    # Adjust layout to prevent overlap and save the figure
    plt.tight_layout()
    plt.savefig('combined_metrics_graph.png')
    plt.show()

if __name__ == '__main__':
    main()