import time
import logging
import matplotlib.pyplot as plt
import numpy as np
from stable_baselines3 import PPO, DDPG, A2C  # Change this to the model you used
import Environment_test as Environment  # Import your environment

# Step 1: Load the trained model
MODEL_PATH = "ppo_service_mesh_model"  # Update with your saved model path
model = PPO.load(MODEL_PATH)

# MODEL_PATH = "ddpg_service_mesh_model"  # Update with your saved model path
# model = DDPG.load(MODEL_PATH)

# Step 2: Initialize the environment
env = Environment.ServiceMeshEnv(action_type="discrete")  # Match the environment used during training
obs, info = env.reset()  # Get initial state

# Step 3: Initialize logging for performance metrics
logging.basicConfig(filename="performance_log.txt", level=logging.INFO)
logging.info("Starting deployment...")

# Performance counters
total_reward = 0
total_steps = 0
episode_count = 0
action_distribution = {i: 0 for i in range(env.action_space.n)}  # Track action distribution

# For plotting
reward_history = []
action_history = []

# Step 4: Deploy in a live decision loop
try:
    while True:
        # Step 4.1: Predict the next action using the trained model
        action, _states = model.predict(obs, deterministic=True)

        # Step 4.2: Ensure action is an integer (just in case it's not)
        if isinstance(action, np.ndarray):
            if action.size == 1:
                action = action.item()  # Extract the scalar value from the array
            else:
                action = action[0]  # Extract the first element if it's a multi-dimensional array

        # If action is a scalar, no need to convert, it's already an integer
        action = int(action)  # Convert to integer (if not already)

        # Step 4.3: Apply the action in the environment
        obs, reward, done, truncated, info = env.step(action)

        # Step 4.4: Log the action, reward, and new state
        logging.info(f"Step {total_steps}: Action taken: {action}, Reward received: {reward}, New state: {obs}")
        
        # Accumulate total reward and update action distribution
        total_reward += reward
        action_distribution[action] += 1
        total_steps += 1

        # Add data for plotting
        reward_history.append(total_reward)
        action_history.append(action)

        # Step 4.5: Handle episode reset if the environment is "done"
        if done:
            episode_count += 1
            logging.info(f"Episode {episode_count} finished. Total reward: {total_reward}. Resetting environment...")
            obs, info = env.reset()  # Reset environment for the next episode

        # Step 4.6: Optional: Monitor and check performance (e.g., system load)
        if total_steps % 100 == 0:  # Every 100 steps, log the current stats
            logging.info(f"Performance Stats (Step {total_steps}):")
            logging.info(f"  Total reward: {total_reward}")
            logging.info(f"  Action distribution: {action_distribution}")

        # Step 4.7: Wait for the next iteration (simulate real-time decision-making)
        # time.sleep(0)  # Adjust sleep time based on system requirements, may need to be reduced for real-time testing

except KeyboardInterrupt:
    print("Deployment stopped manually.")

# Step 5: (Optional) Plot the performance data
plt.figure(figsize=(12, 8))

# Reward over time
plt.subplot(3, 1, 1)
plt.plot(reward_history, label='Total Reward', color='blue')
plt.title('Total Reward Over Time')
plt.xlabel('Time (steps)')
plt.ylabel('Total Reward')

# Action distribution
unique_actions = np.unique(action_history)
action_counts = [action_history.count(a) for a in unique_actions]

plt.subplot(3, 1, 2)
plt.bar(unique_actions, action_counts, color='green')
plt.title('Action Distribution')
plt.xlabel('Action')
plt.ylabel('Frequency')

# Show plots
plt.tight_layout()
plt.show()

# Step 6: (Optional) Save the performance data
plt.savefig('performance_graphs.png')
