from stable_baselines3 import PPO, SAC, DDPG, A2C
import Environment

# Define models and environments
models = {
    "PPO": (PPO("MlpPolicy", Environment.ServiceMeshEnv(action_type="discrete"), verbose=1), "ppo_service_mesh_model"),
    "A2C": (A2C("MlpPolicy", Environment.ServiceMeshEnv(action_type="discrete"), verbose=1), "a2c_service_mesh_model"),
    "DDPG": (DDPG("MlpPolicy", Environment.ServiceMeshEnv(action_type="continuous"), verbose=1), "ddpg_service_mesh_model"),
    "SAC": (SAC("MlpPolicy", Environment.ServiceMeshEnv(action_type="continuous"), verbose=1), "sac_service_mesh_model")
}

# Train and test each model
for model_name, (model, model_path) in models.items():
    print(f"Training {model_name} model...")
    model.learn(total_timesteps=10000)
    model.save(model_path)
    print(f"Model {model_name} saved as {model_path}")

    # Test the model with matching environment
    test_env = Environment.ServiceMeshEnv(action_type="discrete" if model_name in ["PPO", "A2C"] else "continuous")
    obs, info = test_env.reset()  # Initialize the test environment
    for _ in range(1000):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, done, info, [] = test_env.step(action)

        # Uncomment to render if available
        # if hasattr(test_env, 'render'):
        #     test_env.render()

        # Reset environment if done
        if done:
            obs, info = test_env.reset()

print("Training and testing completed for all models.")
