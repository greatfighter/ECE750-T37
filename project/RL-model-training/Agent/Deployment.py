import time
from stable_baselines3 import PPO, DDPG, A2C, SAC  # Change this to the model you used
import Environment_test as Environment  # Import your environment

# Step 1: Load the trained model
MODEL_PATH = "ppo_service_mesh_model"  # Update with your saved model path
model = PPO.load(MODEL_PATH)

# MODEL_PATH = "ddpg_service_mesh_model"  # Update with your saved model path
# model = DDPG.load(MODEL_PATH)

# Step 2: Initialize the environment
env = Environment.ServiceMeshEnv(action_type="discrete")  # Match the environment used during training
obs, info = env.reset()  # Get initial state

# Step 3: Deploy in a live decision loop
try:
    print("Starting deployment...")
    while True:
        # Step 3.1: Predict the next action using the trained model
        action, _states = model.predict(obs, deterministic=True)

        # Step 3.2: Apply the action in the environment
        obs, reward, done, truncated, info = env.step(action)

        # Log the results
        print(f"Action taken: {action}, Reward received: {reward}, New state: {obs}")

        # Step 3.3: Handle episode reset if the environment is "done"
        if done:
            print("Episode finished. Resetting environment...")
            obs, info = env.reset()

        # Step 3.4: Wait for the next iteration (simulate real-time decision-making)
        time.sleep(10)  # Adjust sleep time based on system requirements

except KeyboardInterrupt:
    print("Deployment stopped manually.")

# Step 4: (Optional) Add monitoring or alert systems for live use
