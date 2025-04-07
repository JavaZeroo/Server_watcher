class Metric:
    def __init__(self, name, sub_metrics):
        self.name = name
        self.sub_metrics = sub_metrics

    def get_value(self, monitor):
        raise NotImplementedError("Subclasses must implement get_value method")
    
    async def get_value_async(self, monitor):
        """Async version of get_value. By default falls back to synchronous version.
        Subclasses should override this for improved performance."""
        return self.get_value(monitor)

    def get_sub_metrics(self):
        return self.sub_metrics