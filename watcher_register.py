from enum import Enum

class WatcherModuleType(Enum):
    METRIC = "metric"

class WatcherRegister:
    _registry = {
        WatcherModuleType.METRIC: {}
    }

    @classmethod
    def register(cls, module_type):
        def decorator(watcher_class):
            if module_type not in cls._registry:
                cls._registry[module_type] = {}
            cls._registry[module_type][watcher_class.__name__] = watcher_class
            return watcher_class
        return decorator

    @classmethod
    def get_registered(cls, module_type, name):
        return cls._registry.get(module_type, {}).get(name)

    @classmethod
    def get_all_registered(cls, module_type):
        return cls._registry.get(module_type, {}).values()