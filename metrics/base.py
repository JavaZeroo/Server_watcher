class Metric:
    def __init__(self, name, sub_metrics):
        self.name = name
        self.sub_metrics = sub_metrics

    def get_value(self, monitor):
        raise NotImplementedError("Subclasses must implement get_value method")

    def get_sub_metrics(self):
        return self.sub_metrics