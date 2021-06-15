import inspect

from typing import List, Type, Any
from types import ModuleType


def get_module_subclasses(module: ModuleType, base_class: Type) -> List[Type[Any]]:
    classes_names = [m[0] for m in inspect.getmembers(module, inspect.isclass) if
                     m[1].__module__ == module.__name__]
    all_classes = [getattr(module, class_name) for class_name in classes_names]
    return [class_ for class_ in all_classes if issubclass(class_, base_class)]

