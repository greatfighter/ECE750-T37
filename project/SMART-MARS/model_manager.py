from stable_baselines3 import SAC, PPO, DDPG, A2C
from RL_model_training.Agent import Environment_test as Environment

class ModelManager:
    def __init__(self, model_path):
        """
        Initialize the ModelManager class, load models dynamically, and initialize the environment.

        :param model_path: Base directory for model files (e.g., "RL_model_training/Agent").
        """
        self.base_model_path = model_path
        self.models = {}
        self.env = None

        # Initialize the environment
        self._initialize_environment()

        # Load the models
        self._load_models()

    def _initialize_environment(self):
        """
        Initialize the environment.
        """
        self.env = Environment.ServiceMeshEnv(action_type="discrete")
        print("Environment initialized successfully.")

    def _load_models(self):
        """
        Dynamically generate model paths and load models.
        """
        # Define model names and their corresponding classes
        model_map = {
            "sac": SAC,
            "ppo": PPO,
            "ddpg": DDPG,
            "a2c": A2C  # A3C uses A2C in Stable-Baselines3
        }

        for model_name, model_class in model_map.items():
            # Construct the full path dynamically
            model_path = f"{self.base_model_path}/{model_name}_service_mesh_model.zip"
            try:
                self.models[model_name] = model_class.load(model_path)
                print(f"{model_name} model loaded successfully from {model_path}.")
            except Exception as e:
                print(f"Failed to load {model_name} model from {model_path}: {e}")

    def get_model(self, model_name):
        """
        Retrieve a specific model instance.

        :param model_name: Name of the model (SAC, PPO, DDPG, A3C).
        :return: The specified model instance.
        """
        if model_name in self.models:
            return self.models[model_name]
        else:
            raise ValueError(f"Model {model_name} not found. Available models: {list(self.models.keys())}")

    def reset_environment(self):
        """
        Reset the environment.
        :return: Initial state and environment info.
        """
        return self.env.reset()

    def get_best_action(self, obs):
        """
        Iterate through all loaded models, evaluate their actions on the given observation,
        and return the action from the best-performing model.

        :param obs: The current observation from the environment.
        :return: A tuple of (best_action, best_model_name).
        """
        
        best_action = None
        best_model_name = None
        best_score = -np.inf  # Initialize the best score to negative infinity

        for model_name, model in self.models.items():
            try:
                # Predict the action for the given observation
                action, _states = model.predict(obs, deterministic=True)
                action = int(action)
                
                # Here, you can evaluate the "score" for the action. 
                # For demonstration, we'll use a placeholder "evaluate_action" function.
                target_state = np.zeros_like(obs)
                score = -np.sum((obs - target_state) ** 2)

                print(f"Model: {model_name}, Action: {action}, Score: {score}")

                # Update the best action if the current score is better
                if score > best_score:
                    best_score = score
                    best_action = action
                    best_model_name = model_name
            except Exception as e:
                print(f"Failed to predict using model {model_name}: {e}")

        print(f"Best Model: {best_model_name}, Best Action: {best_action}, Best Score: {best_score}")
        return best_action, best_model_name

# Example usage
if __name__ == "__main__":
    model_base_path = "RL_model_training/Agent"  # Base directory for model files
    manager = ModelManager(model_base_path)

    # Retrieve SAC model instance
    sac_model = manager.get_model("sac")
    
    # Reset environment and interact with it
    obs, info = manager.reset_environment()
    print("Initial observation:", obs)
