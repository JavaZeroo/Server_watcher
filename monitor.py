# monitor.py
import paramiko
import time
from datetime import datetime
import multiprocessing
import os

class Metric:
    def __init__(self, name, sub_metrics):
        self.name = name
        self.sub_metrics = sub_metrics

    def get_value(self, monitor):
        raise NotImplementedError("Subclasses must implement get_value method")

    def get_sub_metrics(self):
        return self.sub_metrics

class CpuMetric(Metric):
    def __init__(self):
        sub_metrics = [("usage", "CPU使用率")]
        super().__init__("cpu", sub_metrics)

    def get_value(self, monitor):
        result = monitor.execute_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        if result:
            try:
                return {"usage": float(result.strip())}
            except:
                return None
        return None

class MemoryMetric(Metric):
    def __init__(self):
        sub_metrics = [
            ("percentage", "内存使用率"),
            ("used", "已用内存"),
            ("total", "总内存")
        ]
        super().__init__("memory", sub_metrics)

    def get_value(self, monitor):
        total_cmd = "free -m | grep 'Mem:' | awk '{print $2}'"
        used_cmd = "free -m | grep 'Mem:' | awk '{print $3}'"
        
        total_mem = monitor.execute_command(total_cmd)
        used_mem = monitor.execute_command(used_cmd)
        
        if total_mem and used_mem:
            try:
                total = float(total_mem.strip())
                used = float(used_mem.strip())
                percentage = (used / total) * 100
                return {
                    "percentage": percentage,
                    "used": used,
                    "total": total
                }
            except:
                return None
        return None

class DiskMetric(Metric):
    def __init__(self):
        sub_metrics = [("usage", "磁盘使用率")]
        super().__init__("disk", sub_metrics)

    def get_value(self, monitor):
        disk_cmd = "df -h / | grep -v Filesystem | awk '{print $5}'"
        disk_usage = monitor.execute_command(disk_cmd)
        
        if disk_usage:
            try:
                percentage = float(disk_usage.strip().replace('%', ''))
                return {"usage": percentage}
            except:
                return None
        return None

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
    
    monitor.register_metric(CpuMetric())
    monitor.register_metric(MemoryMetric())
    monitor.register_metric(DiskMetric())
    
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