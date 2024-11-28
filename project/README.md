# simple-service-mesh-demo

This project is originated by the simple-service-mesh-demo project from the Red Hat Developer website.

The project has the configuration file and source code for working with an instance of OpenShift Service Mesh.

The folders in the project are as follows.

## K8S

The folder [K8S](./k8s/) has the YAML configuration files and setup script for getting the demonstration application's K8S resources running in an OpenShift/Kubernetes cluster.

## Service-Mesh

The folder [service-mesh](./service-mesh/) has the YAML configuration files for the Gateway, Virtual Services and Destination Rules needed to run the demonstration application under an OpenShift Service Mesh.

## src

The folder [src](./src/) contains the source code and buildah file for pushing the microservices written in Node.js as container image that are stored on quay.io located [TO BE PROVIDED].

## Locust
The folder **Locust** contains scripts for simulating workload scenarios and stress testing the deployed microservices. The workload simulation includes:
- Generating traffic to test routing policies defined in the Service Mesh.
- Measuring system performance under varying loads.
- Customizable scenarios to simulate real-world application usage.

**Locust Setup and Usage**:
1. Install Locust using `pip install locust`.
2. Navigate to the `Locust` folder.
3. Run the workload tests with the command:

## SMART-MARS
The folder **SMART-MARS** includes the self-adaptive management system built using the **MAPE-K loop** (Monitoring, Analysis, Planning, Execution, and Knowledge) and **reinforcement learning (RL)** techniques.

**Key Features**:
- **Monitoring**: Collects real-time metrics (e.g., response times, throughput) from the Service Mesh.
- **Analysis**: Evaluates system behavior and detects performance bottlenecks or anomalies.
- **Planning**: Uses RL models to plan optimal actions (e.g., traffic shifting, scaling).
- **Execution**: Applies decisions dynamically to the Service Mesh using `oc` commands or Service Mesh APIs.
- **Knowledge Base**: Maintains a historical database of metrics and actions to improve decision-making over time.

**SMART-MARS Structure**:
- **Environment**: A simulation environment for RL, integrating metrics from Locust and Service Mesh configurations.
- **Agent**: Reinforcement learning agents (e.g., SAC, PPO) for optimizing service routing and resource allocation.
- **MAPE-K Framework**: Implements the MAPE-K loop to enable dynamic adaptation of the Service Mesh.

**How to Use SMART-MARS**:
python main.py
