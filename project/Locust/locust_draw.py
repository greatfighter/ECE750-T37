import pandas as pd
import matplotlib.pyplot as plt

# Set global font size for all plots
plt.rc('font', size=16)  # Set default font size
plt.rc('axes', titlesize=18)  # Set title font size
plt.rc('axes', labelsize=16)  # Set axis label font size
plt.rc('xtick', labelsize=14)  # Set x-tick label font size
plt.rc('ytick', labelsize=14)  # Set y-tick label font size
plt.rc('legend', fontsize=14)  # Set legend font size

# Load the data from the CSV file
file_path = "sinusoidal_test_results_stats_history.csv"  # Replace with your actual file path
data = pd.read_csv(file_path)

# Convert the Timestamp to readable format if needed
data['Timestamp'] = pd.to_datetime(data['Timestamp'], unit='s')

# Filter data to include only the first 5 minutes
start_time = data['Timestamp'].min()
end_time = start_time + pd.Timedelta(minutes=5)
data = data[(data['Timestamp'] >= start_time) & (data['Timestamp'] <= end_time)]

# Plot Requests/s and Failures/s in one graph
plt.figure(figsize=(14, 6))
plt.plot(data['Timestamp'], data['Requests/s'], label='Requests/s', color='green')
plt.plot(data['Timestamp'], data['Failures/s'], label='Failures/s', color='red')
plt.title("Requests and Failures per Second Over Time (First 5 Minutes)")
plt.xlabel("Timestamp")
plt.ylabel("Requests/Failures per Second")
plt.grid(True)
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot User Count over Time
plt.figure(figsize=(14, 6))
plt.plot(data['Timestamp'], data['User Count'], label='User Count', color='blue')
plt.title("User Count Over Time (First 5 Minutes)")
plt.xlabel("Timestamp")
plt.ylabel("User Count")
plt.grid(True)
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Plot Response Time Percentiles over Time
percentiles = ['50%', '95%']
plt.figure(figsize=(14, 8))

for percentile in percentiles:
    plt.plot(data['Timestamp'], data[percentile], label=f'{percentile} Response Time')

plt.title("Response Time Percentiles Over Time (First 5 Minutes)")
plt.xlabel("Timestamp")
plt.ylabel("Response Time (ms)")
plt.grid(True)
plt.legend()
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
