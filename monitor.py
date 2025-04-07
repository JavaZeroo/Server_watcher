# monitor.py
import paramiko
import time
from datetime import datetime
import multiprocessing
import os
from watcher_register import WatcherRegister, WatcherModuleType

class ServerMonitor:
    def __init__(self, server_id, hostname, username, password=None, key_filename=None, port=22):
        self.server_id = server_id
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.client = None
        self.connected = False
        self.metrics = []

    def register_metric(self, metric):
        self.metrics.append(metric)

    def connect(self):
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if self.key_filename:
                self.client.connect(
                    hostname=self.hostname, 
                    username=self.username, 
                    key_filename=self.key_filename,
                    port=self.port
                )
            else:
                self.client.connect(
                    hostname=self.hostname, 
                    username=self.username, 
                    password=self.password,
                    port=self.port
                )
            self.connected = True
            return True
        except Exception as e:
            print(f"连接 {self.hostname} 失败: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        if self.client:
            self.client.close()
            self.connected = False
    
    def execute_command(self, command):
        if not self.connected:
            if not self.connect():
                return None
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=10)
            result = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            if error:
                print(f"命令执行错误 ({self.hostname}): {error}")
                return None
            return result
        except Exception as e:
            print(f"命令执行失败 ({self.hostname}): {e}")
            self.connected = False
            return None
    
    def get_metrics_data(self):
        data = {}
        for metric in self.metrics:
            value = metric.get_value(self)
            if value is not None:
                for sub_key, sub_value in value.items():
                    data[f"{metric.name}_{sub_key}"] = sub_value
        return data
    
    def get_metric_labels(self):
        labels = {}
        for metric in self.metrics:
            for key, label in metric.get_sub_metrics():
                labels[f"{metric.name}_{key}"] = label
        return labels

def monitor_server(server_config, interval, data_queue):
    server_id = server_config.get('id', server_config['hostname'])
    print(f"进程 {server_id} 启动，PID: {os.getpid()}")
    monitor = ServerMonitor(
        server_id=server_id,
        hostname=server_config['hostname'],
        username=server_config['username'],
        password=server_config.get('password'),
        key_filename=server_config.get('key_filename'),
        port=server_config.get('port', 22)
    )

    # Dynamically register metrics based on configuration
    for metric_config in server_config.get('metrics', []):
        metric_type = metric_config.get('type')
        metric_class = WatcherRegister.get_registered(WatcherModuleType.METRIC, metric_type)
        if metric_class:
            monitor.register_metric(metric_class())
        else:
            print(f"未找到指定的监控指标类型: {metric_type}")

    if not monitor.connect():
        data_queue.put({"server_id": server_id, "status": "error", "message": "连接失败"})
        return
    data_queue.put({"server_id": server_id, "status": "connected"})
    try:
        while True:
            timestamp = datetime.now()
            metrics_data = monitor.get_metrics_data()
            if metrics_data:
                data = {
                    "server_id": server_id,
                    "status": "data",
                    "timestamp": timestamp,
                    **metrics_data
                }
                data_queue.put(data)
            else:
                data_queue.put({"server_id": server_id, "status": "error", "message": "获取数据失败"})
                monitor.connect()
            time.sleep(interval)
    except Exception as e:
        data_queue.put({"server_id": server_id, "status": "error", "message": str(e)})
    finally:
        monitor.disconnect()