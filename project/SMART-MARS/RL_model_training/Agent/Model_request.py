import time
from stable_baselines3 import PPO, DDPG  # Change this to the model you used
import Agent.Environment_train as Environment  # Import your environment

# Step 1: Load the trained model
MODEL_PATH = "ppo_service_mesh_model"  # Update with your saved model path
model = PPO.load(MODEL_PATH)

# MODEL_PATH = "ddpg_service_mesh_model"  # Update with your saved model path
# model = DDPG.load(MODEL_PATH)

# Step 2: Initialize the environment
env = Environment.ServiceMeshEnv(action_type="discrete")  # Match the environment used during training
obs, info = env.reset()  # Get initial state

# Function to simulate receiving latest data from the server
def get_latest_data_from_server():
    # Simulate fetching the latest data from the server
    # Replace this with actual data fetching code (e.g., API call, database query)
    latest_data = {
        "request_rate": 15,  # example metric: requests per second
        "cpu_utilization": 50,  # example metric: CPU utilization in percentage
        "memory_usage": 60,  # example metric: memory usage in percentage
        "latency": 200  # example metric: system latency in ms
    }
    return latest_data

# Step 3: Deploy in a live decision loop
try:
    print("Starting deployment...")
    while True:
        # Step 3.1: Fetch the latest data from the server
        latest_data = get_latest_data_from_server()

        # Update the environment with the latest data (you can modify the environment to accept this data)
        obs = env.update_state_with_data(latest_data)  # Assuming `update_state_with_data` is a method that updates the observation

        # Step 3.2: Predict the next action using the trained model
        action, _states = model.predict(obs, deterministic=True)

        # Step 3.3: Apply the action in the environment
        obs, reward, done, truncated, info = env.step(action)

        # Log the results
        print(f"Action taken: {action}, Reward received: {reward}, New state: {obs}")

        # Step 3.4: Handle episode reset if the environment is "done"
        if done:
            print("Episode finished. Resetting environment...")
            obs, info = env.reset()

        # Step 3.5: Wait for the next iteration (simulate real-time decision-making)
        time.sleep(10)  # Adjust sleep time based on system requirements

except KeyboardInterrupt:
    print("Deployment stopped manually.")

# Step 4: (Optional) Add monitoring or alert systems for live use
