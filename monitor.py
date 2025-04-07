import asyncio
import logging
from datetime import datetime
import os
from watcher_register import WatcherRegister, WatcherModuleType
import asyncssh

# 获取应用logger
logger = logging.getLogger('server_watcher.monitor')

# 配置asyncssh日志级别 - 减少不必要的详细日志
asyncssh_logger = logging.getLogger('asyncssh')
asyncssh_logger.setLevel(logging.WARNING)  # 只显示警告和错误信息

class ServerMonitor:
    def __init__(self, server_id, hostname, username, password=None, key_filename=None, port=22):
        self.server_id = server_id
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.client = None
        self.conn = None  # asyncssh connection
        self.connected = False
        self.metrics = []

    def register_metric(self, metric):
        self.metrics.append(metric)

    async def connect_async(self):
        try:
            # Use asyncssh for async connections
            if self.key_filename:
                self.conn = await asyncssh.connect(
                    host=self.hostname,
                    username=self.username,
                    client_keys=[self.key_filename],
                    port=self.port,
                    known_hosts=None
                )
            else:
                self.conn = await asyncssh.connect(
                    host=self.hostname,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                    known_hosts=None
                )
            self.connected = True
            return True
        except Exception as e:
            logger.error(f"异步连接 {self.hostname} 失败: {e}")
            self.connected = False
            return False
    
    async def disconnect_async(self):
        if self.conn:
            self.conn.close()
            await self.conn.wait_closed()
            self.connected = False
    
    def disconnect(self):
        if self.client:
            self.client.close()
            self.connected = False
        # Also close asyncssh connection if exists
        if self.conn:
            self.conn.close()
            self.connected = False
    
    async def execute_command_async(self, command):
        if not self.connected:
            if not await self.connect_async():
                return None
        try:
            result = await self.conn.run(command, timeout=10)
            if result.stderr:
                logger.error(f"命令执行错误 ({self.hostname}): {result.stderr}")
                return None
            return result.stdout
        except Exception as e:
            logger.error(f"异步命令执行失败 ({self.hostname}): {e}")
            self.connected = False
            return None
    
    def execute_command(self, command):
        if not self.connected:
            if not self.connect():
                return None
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=10)
            result = stdout.read().decode('utf-8')
            error = stderr.read().decode('utf-8')
            if error:
                logger.error(f"命令执行错误 ({self.hostname}): {error}")
                return None
            return result
        except Exception as e:
            logger.error(f"命令执行失败 ({self.hostname}): {e}")
            self.connected = False
            return None
    
    async def get_metrics_data_async(self):
        data = {}
        for metric in self.metrics:
            # Check if the metric has an async version
            if hasattr(metric, 'get_value_async'):
                value = await metric.get_value_async(self)
            else:
                # Fall back to synchronous method
                value = metric.get_value(self)
            
            if value is not None:
                for sub_key, sub_value in value.items():
                    data[f"{metric.name}_{sub_key}"] = sub_value
        return data
    
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

async def async_monitor_server(server_config, interval, data_queue):
    server_id = server_config.get('id', server_config['hostname'])
    logger.info(f"异步进程 {server_id} 启动，PID: {os.getpid()}")
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
            logger.warning(f"未找到指定的监控指标类型: {metric_type}")

    if not await monitor.connect_async():
        data_queue.put({"server_id": server_id, "status": "error", "message": "连接失败"})
        return
    data_queue.put({"server_id": server_id, "status": "connected"})
    try:
        while True:
            timestamp = datetime.now()
            metrics_data = await monitor.get_metrics_data_async()
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
                await monitor.connect_async()
            await asyncio.sleep(interval)
    except Exception as e:
        logger.error(f"监控服务器 {server_id} 时出错: {e}")
        data_queue.put({"server_id": server_id, "status": "error", "message": str(e)})
    finally:
        await monitor.disconnect_async()

def monitor_server(server_config, interval, data_queue):
    """Legacy synchronous monitor_server function that wraps the async version"""
    server_id = server_config.get('id', server_config['hostname'])
    logger.info(f"进程 {server_id} 启动，PID: {os.getpid()}")
    
    # Use asyncio to run the async monitor function
    asyncio.run(async_monitor_server(server_config, interval, data_queue))