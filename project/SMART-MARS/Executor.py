import json
import os
import subprocess


class Executor:
    def __init__(self, file_path):
        """
        Initialize the Executor class with the path to the virtual service JSON file.

        :param file_path: Path to the virtual service JSON file.
        """
        self.file_path = file_path
        self.virtual_service = None

        # Load the JSON file during initialization
        self._load_virtual_service()

    def _load_virtual_service(self):
        """
        Load the virtual service JSON file into memory.
        """
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(f"File not found: {self.file_path}")

        with open(self.file_path, 'r') as f:
            self.virtual_service = json.load(f)
        print(f"Loaded virtual service configuration from {self.file_path}.")

    def update_weights(self, actions):
        """
        Update the weight values in the virtual service configuration.

        :param actions: A list of two numbers representing the weights to set.
        """
        if not self.virtual_service or "spec" not in self.virtual_service or "http" not in self.virtual_service["spec"]:
            raise ValueError("Invalid virtual service configuration format.")

        routes = self.virtual_service["spec"]["http"][0]["route"]

        if len(actions) != 2 or len(routes) != 2:
            raise ValueError("Actions must contain exactly two numbers, and there must be exactly two routes.")

        # Update the weights based on the actions list
        routes[0]["weight"] = actions[0]
        routes[1]["weight"] = actions[1]

        print(f"Updated weights to {actions} in the virtual service configuration.")

    def save_and_apply(self):
        """
        Save the updated virtual service configuration and apply it using `oc apply`.
        """
        # Save the updated configuration back to the file
        with open(self.file_path, 'w') as f:
            json.dump(self.virtual_service, f, indent=4)
        print(f"Saved updated virtual service configuration to {self.file_path}.")

        # Apply the updated configuration using `oc apply`
        command = ["oc", "apply", "-f", self.file_path]
        try:
            subprocess.run(command, check=True)
            print(f"Successfully applied the updated configuration using: {' '.join(command)}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to apply the configuration: {e}")
            raise