from watcher_register import WatcherRegister, WatcherModuleType
import logging
from .base import Metric

# 获取logger
logger = logging.getLogger('server_watcher.metrics.cpu')

@WatcherRegister.register(WatcherModuleType.METRIC)
class CpuMetric(Metric):
    def __init__(self):
        sub_metrics = [("usage", "CPU使用率")]
        super().__init__("cpu", sub_metrics)

    def get_value(self, monitor):
        result = monitor.execute_command("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        if result:
            try:
                return {"usage": float(result.strip())}
            except Exception as e:
                logger.error(f"解析CPU使用率失败: {e}")
                return None
        return None
        
    async def get_value_async(self, monitor):
        result = await monitor.execute_command_async("top -bn1 | grep 'Cpu(s)' | awk '{print $2 + $4}'")
        if result:
            try:
                return {"usage": float(result.strip())}
            except Exception as e:
                logger.error(f"异步解析CPU使用率失败: {e}")
                return None
        return None