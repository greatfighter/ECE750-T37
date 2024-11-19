# import json
# import subprocess
# import time

# PROMETHEUS_POD = "prometheus-779c8f99d8-5t67m"
# NAMESPACE = "istio-system"

# # Prometheus 查询模板
# QUERIES = {
#     "cpu_usage": 'rate(container_cpu_usage_seconds_total{{pod="{pod_name}"}}[1m])',
#     "memory_usage": 'container_memory_usage_bytes{{pod="{pod_name}"}}',
#     "network_receive": 'sum(rate(container_network_receive_bytes_total{{pod="{pod_name}"}}[1m]))',
#     "network_transmit": 'sum(rate(container_network_transmit_bytes_total{{pod="{pod_name}"}}[1m]))',
#     "rps": 'rate(istio_requests_total{{destination_service=~"{service_name}"}}[1m])'
# }

# # 定义需要监控的服务
# SERVICES = [
#     {"pod_name": "orders-78dc47b8d8-vjzt8", "service_name": "orders"},
#     {"pod_name": "payments-589544f4dd-dpwqv", "service_name": "payments"},
#     {"pod_name": "recommendations-food-5d99cdc545-rx22w", "service_name": "recommendations-food"},
# ]

# # Prometheus API 查询函数
# def query_prometheus(query):
#     # 构造 oc exec 命令
#     command = [
#         "oc",
#         "exec",
#         "-it",
#         PROMETHEUS_POD,
#         "-n",
#         NAMESPACE,
#         "-c",
#         "prometheus-proxy",  # 确保使用正确的容器
#         "--",
#         "curl",
#         "-s",
#         "-k",
#         f"http://localhost:9090/api/v1/query?query={query}"
#     ]
    
#     try:
#         # 执行命令
#         result = subprocess.run(command, text=True, capture_output=True, check=True)
#         return json.loads(result.stdout)  # 转换为 JSON
#     except subprocess.CalledProcessError as e:
#         print("Error occurred while querying Prometheus!")
#         print("Return Code:", e.returncode)
#         print("Error Output:", e.stderr)
#         return None

# # 解析 Prometheus 返回数据
# def parse_prometheus_response(response, pod_name):
#     """
#     从 Prometheus 返回的 JSON 数据中过滤与 pod_name 匹配的结果。
#     """
#     if not response or response.get("status") != "success":
#         return None

#     results = response.get("data", {}).get("result", [])
#     for result in results:
#         metric = result.get("metric", {})
#         if metric.get("kubernetes_pod_name") == pod_name:
#             value = result.get("value", [None, None])[1]
#             return value  # 返回匹配的值

#     return None  # 如果没有匹配结果，返回 None

# # 监控每个服务
# def monitor_services():
#     for service in SERVICES:
#         pod_name = service["pod_name"]
#         service_name = service["service_name"]
#         print(f"Monitoring service: {service_name} (Pod: {pod_name})")
        
#         for metric_name, query_template in QUERIES.items():
#             # 替换查询中的占位符
#             query = query_template.format(
#                 pod_name=pod_name,
#                 service_name=service_name
#             )
            
#             # 查询 Prometheus
#             response = query_prometheus(query)
#             value = parse_prometheus_response(response, pod_name)
#             print (response, value)
#             if value is not None:
#                 print(f"  {metric_name}: {value}")
#             else:
#                 print(f"  Failed to retrieve {metric_name}")

# # 主函数
# if __name__ == "__main__":
#     while True:
#         print(f"Running monitoring loop... {time.strftime('%Y-%m-%d %H:%M:%S')}")
#         monitor_services()
#         print("Waiting for 60 seconds before next query...\n")
#         time.sleep(60)  # 每分钟运行一次

import requests
import time

# Prometheus 配置
PROMETHEUS_URL = "prometheus-779c8f99d8-5t67m:9090/api/v1/query"
QUERY_INTERVAL = 60  # 查询间隔时间（秒）

# 查询 Prometheus 数据的函数
def query_prometheus(query):
    try:
        response = requests.get(PROMETHEUS_URL, params={"query": query})
        response.raise_for_status()
        result = response.json()
        if result["status"] == "success":
            return result["data"]["result"]
        else:
            print(f"Error querying Prometheus: {result}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error connecting to Prometheus: {e}")
        return None

# 查询 CPU 和内存使用率
def monitor_pods():
    cpu_query = "sum(rate(container_cpu_usage_seconds_total{namespace='default'}[5m])) by (pod)"
    memory_query = "sum(container_memory_usage_bytes{namespace='default'}) by (pod)"
    
    print("Monitoring Pods... Press Ctrl+C to stop.")
    while True:
        print(f"\n--- Fetching data at {time.ctime()} ---")
        cpu_usage = query_prometheus(cpu_query)
        memory_usage = query_prometheus(memory_query)
        
        if cpu_usage:
            print("Pod CPU Usage:")
            for item in cpu_usage:
                pod_name = item["metric"]["pod"]
                value = item["value"][1]
                print(f"  Pod: {pod_name}, CPU Usage: {value} cores")
        
        if memory_usage:
            print("Pod Memory Usage:")
            for item in memory_usage:
                pod_name = item["metric"]["pod"]
                value = item["value"][1]
                print(f"  Pod: {pod_name}, Memory Usage: {value} bytes")
        
        time.sleep(QUERY_INTERVAL)

if __name__ == "__main__":
    try:
        monitor_pods()
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")