from watcher_register import WatcherRegister, WatcherModuleType
from .base import Metric

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
            except:
                return None
        return None