import inspect

from typing import List, Type, Any
from types import ModuleType
from enum import Enum

from PyQt5.QtWidgets import QMessageBox, QPushButton, QListWidget
from PyQt5.QtCore import Qt


def get_module_subclasses(module: ModuleType, base_class: Type) -> List[Type[Any]]:
    classes_names = [m[0] for m in inspect.getmembers(module, inspect.isclass) if
                     m[1].__module__ == module.__name__]
    all_classes = [getattr(module, class_name) for class_name in classes_names]
    return [class_ for class_ in all_classes if issubclass(class_, base_class)]


def display_messagebox_with_buttons(buttons: List[str], title: str = "", text: str = "") -> int:
    msg_box = QMessageBox()
    msg_box.setWindowTitle(title)
    msg_box.setText(text)
    for button in buttons:
        msg_box.addButton(QPushButton(button), QMessageBox.NoRole)
    return msg_box.exec_()


def get_selected_list_widget_items_for_enum(list_widget: QListWidget, enum: Type[Enum]) -> List[Enum]:
    return [enum(i) for i in range(list_widget.count()) if list_widget.item(i).checkState() == Qt.Checked]
