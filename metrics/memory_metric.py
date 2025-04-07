from watcher_register import WatcherRegister, WatcherModuleType
from .base import Metric

@WatcherRegister.register(WatcherModuleType.METRIC)
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
        
    async def get_value_async(self, monitor):
        total_cmd = "free -m | grep 'Mem:' | awk '{print $2}'"
        used_cmd = "free -m | grep 'Mem:' | awk '{print $3}'"
        
        # Execute commands in parallel for better performance
        total_mem_task = monitor.execute_command_async(total_cmd)
        used_mem_task = monitor.execute_command_async(used_cmd)
        
        total_mem = await total_mem_task
        used_mem = await used_mem_task
        
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