import paramiko
import time
from datetime import datetime
import multiprocessing
import os

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
    
    def get_cpu_usage(self):
        result = self.execute_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        if result:
            try:
                return float(result.strip())
            except:
                return None
        return None
    
    def get_memory_usage(self):
        total_cmd = "free -m | grep 'Mem:' | awk '{print $2}'"
        used_cmd = "free -m | grep 'Mem:' | awk '{print $3}'"
        
        total_mem = self.execute_command(total_cmd)
        used_mem = self.execute_command(used_cmd)
        
        if total_mem and used_mem:
            try:
                total = float(total_mem.strip())
                used = float(used_mem.strip())
                percentage = (used / total) * 100
                return percentage, used, total
            except:
                return None, None, None
        return None, None, None

    def get_disk_usage(self):
        disk_cmd = "df -h / | grep -v Filesystem | awk '{print $5}'"
        disk_usage = self.execute_command(disk_cmd)
        
        if disk_usage:
            try:
                percentage = float(disk_usage.strip().replace('%', ''))
                return percentage
            except:
                return None
        return None

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
    if not monitor.connect():
        data_queue.put({"server_id": server_id, "status": "error", "message": "连接失败"})
        return
    data_queue.put({"server_id": server_id, "status": "connected"})
    try:
        while True:
            timestamp = datetime.now()
            cpu_usage = monitor.get_cpu_usage()
            memory_usage, mem_used, mem_total = monitor.get_memory_usage()
            disk_usage = monitor.get_disk_usage()
            if cpu_usage is not None and memory_usage is not None:
                data = {
                    "server_id": server_id,
                    "status": "data",
                    "timestamp": timestamp,
                    "cpu": cpu_usage,
                    "memory": memory_usage,
                    "memory_used": mem_used,
                    "memory_total": mem_total,
                    "disk": disk_usage
                }
                data_queue.put(data)
            else:
                data_queue.put({"server_id": server_id, "status": "error", "message": "获取数据失败"})
                monitor.connect()  # 尝试重新连接
            time.sleep(interval)
    except Exception as e:
        data_queue.put({"server_id": server_id, "status": "error", "message": str(e)})
    finally:
        monitor.disconnect()