from watcher_register import WatcherRegister, WatcherModuleType
import logging
from .base import Metric

# Get the logger
logger = logging.getLogger('server_watcher.metrics.disk')

@WatcherRegister.register(WatcherModuleType.METRIC)
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
            except Exception as e:
                logger.error(f"解析磁盘使用率失败: {e}")
                return None
        return None
        
    async def get_value_async(self, monitor):
        disk_cmd = "df -h / | grep -v Filesystem | awk '{print $5}'"
        disk_usage = await monitor.execute_command_async(disk_cmd)
        
        if disk_usage:
            try:
                percentage = float(disk_usage.strip().replace('%', ''))
                return {"usage": percentage}
            except Exception as e:
                logger.error(f"异步解析磁盘使用率失败: {e}")
                return None
        return None