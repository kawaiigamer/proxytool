# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Union, List, Type

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QTextCursor, QColor
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import QMainWindow, QMessageBox, QPushButton

import proxylib.resources
import proxylib.checkers

from ui.Ui_main_window import Ui_MainWindow
from proxylib.utils import EventLoopThread, ProxiesContainer
from proxylib.types import ProxyResouse, ProxyChecker, Proxy, ProxyType, AnonymityLevel, ProxyStatus
from ui.ui_utils import get_module_subclasses


class MainWindow(QMainWindow, Ui_MainWindow):

    log_write_line_signal = QtCore.pyqtSignal(str, str)
    update_ui_signal = QtCore.pyqtSignal()

    version = "py_proxytool v0.2"
    colours = {"error": QColor(255, 0, 0), "success": QColor(0, 153, 0), "warn": QColor(0, 0, 255),
               "default": QColor(0, 0, 0)}
    log_time_format = "%Y-%m-%d %H:%M:%S"

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
        self.setFixedSize(self.size())
        self.setWindowIcon(QtGui.QIcon('arch_icon.png'))

        self.proxies_table_model = QtGui.QStandardItemModel()
        self.proxies_table.setModel(self.proxies_table_model)
        self.proxies_table_model.setHorizontalHeaderLabels(Proxy.__slots__)

        self.proxies_container = ProxiesContainer()
        self.background_thread = EventLoopThread()
        self.background_executing_tasks_count: int = 0
        self.resources: List[Type[ProxyResouse]] = get_module_subclasses(proxylib.resources, ProxyResouse)
        self.checkers: List[Type[ProxyChecker]] = get_module_subclasses(proxylib.checkers, ProxyChecker)

        self.log_write_line_signal.connect(self.log_write_line, QtCore.Qt.QueuedConnection)
        self.update_ui_signal.connect(self.update_ui, QtCore.Qt.QueuedConnection)

        for list_widget, checkboxes in zip(
                 (self.resourses_list, self.checkers_list),
                 ([resource.description() for resource in self.resources], [checker.description() for checker in self.checkers])):
            for checkbox in checkboxes:
                item = QtWidgets.QListWidgetItem()
                item.setText(checkbox)
                item.setFlags(QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
                item.setCheckState(QtCore.Qt.Checked)
                list_widget.addItem(item)

        self.update_ui()
        self.log_write_line("{0} started".format(self.version))

    @QtCore.pyqtSlot()
    def update_ui(self):
        self.setWindowTitle(self.proxies_container.get_status())
        self.proxies_table_model.removeRows(0, self.proxies_table_model.rowCount())
        row = 0
        for proxy in self.proxies_container.proxy_list:
            column = 0
            for value in proxy.json().values():
                self.proxies_table_model.setItem(row, column, QtGui.QStandardItem(value))
                column += 1
            row += 1

    # TODO: refactor more!

    def msg_box_with_buttons(self, buttons_list, title="", text=""):
        msg_box = QMessageBox()
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        for button in buttons_list:
            msg_box.addButton(QPushButton(button), QMessageBox.NoRole)
        return msg_box.exec_()

    @QtCore.pyqtSlot(str, str, str)
    def log_write_line(self, text: str, colour: str = "default", time_format: str = None):
        self.console.setTextColor(self.colours[colour])
        self.console.append(
            "[{0}] {1}".format(datetime.now().strftime(time_format if time_format else self.log_time_format), text))
        self.console.moveCursor(QTextCursor.End)

    def get_selected_list_widget_items(self, list_widget, target_enum):
        items_list = []
        for i in range(list_widget.count()):
            if list_widget.item(i).checkState() == Qt.Checked:
                items_list.append(target_enum(i))
        return items_list

    def synchronized_ui(method):
        def wrapper(self):
            if self.background_executing_tasks_count == 0:
                method(self)
            else:
                self.log_write_line("Another task already in queue", 'error')

        return wrapper

    def update_ui_after(method):
        def wrapper(self):
            if method(self) is not False:
                self.update_ui()

        return wrapper

    @pyqtSlot(QtWidgets.QListWidgetItem)
    def on_checkers_list_itemChanged(self, item):
        if item.checkState() == Qt.Checked:
            for i in range(self.checkers_list.count()):
                if self.checkers_list.item(i).text() != item.text():
                    self.checkers_list.item(i).setCheckState(Qt.Unchecked)

    @synchronized_ui
    @pyqtSlot()
    def on_pharse_button_pressed(self):
        selected_types = []
        if self.http_checkbox.isChecked():
            selected_types.append(ProxyType.HTTP)
        if self.https_checkbox.isChecked():
            selected_types.append(ProxyType.HTTPS)
        if self.socks4_checkbox.isChecked():
            selected_types.append(ProxyType.SOCKS4)
        if self.socks5_checkbox.isChecked():
            selected_types.append(ProxyType.SOCKS5)
        if len(selected_types) == 0:
            self.log_write_line("Proxy type not selected", 'error')
            return False

        def on_start():
            self.background_executing_tasks_count += 1

        def on_end(result: Union[Exception, List[Proxy]]):
            self.background_executing_tasks_count -= 1
            if type(result) is Exception:
                self.log_write_line_signal.emit("An exception was thrown: {}".format(result), 'error')
                return
            self.log_write_line_signal.emit("{} results".format(len(result)),
                                             'success' if len(result) > 0 else 'error')
            added_count = self.proxies_container.add_new_list(result)
            self.log_write_line_signal.emit("{} new proxies added".format(added_count),
                                             'success' if added_count > 0 else 'warn')
            self.update_ui_signal.emit()

        started_works = 0
        for i in range(self.resourses_list.count()):
            if self.resourses_list.item(i).checkState() == Qt.Checked:
                self.log_write_line("Parsing {}...".format(self.resourses_list.item(i).text()))
                self.background_thread.single_http_work(on_start, on_end, self.resources[i].parse,
                                                        max_count=self.max_count_spinbox.value(),
                                                        min_anonymity_level=AnonymityLevel(
                                                               self.anonymity_combobox.currentIndex()),
                                                        types=selected_types,
                                                        country=self.country_edit.text(),
                                                        timeout_s=self.timeout_spinbox.value()
                                                        )
                started_works += 1
        if not started_works:
            self.log_write_line("No sources selected", 'error')

    @pyqtSlot()
    def on_export_button_pressed(self):
        if len(self.proxies_container.proxy_list) == 0:
            self.log_write_line("Nothing to dump", 'error')
            return
        status_list = self.get_selected_list_widget_items(self.status_list, ProxyStatus)
        if len(status_list) == 0:
            self.log_write_line("Status not selected", 'error')
            return
        file_path = QtWidgets.QFileDialog.getSaveFileName(None, 'Save',
                                                          "proxylist_" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S"),
                                                          'json (*.json);;text (*.txt)')
        if file_path[0] == '':
            return
        try:
            with open(file_path[0], 'w+') as w:
                if file_path[0].endswith('.json'):
                    w.write(self.proxies_container.dump_all_with_status_json(status_list))
                else:
                    w.write(self.proxies_container.dump_all_with_status_txt(status_list))
                self.log_write_line("Successfully dumped", 'success')
        except Exception as e:
            self.log_write_line("An exception was thrown: {}".format(e), 'error')

    @update_ui_after
    @pyqtSlot()
    def on_clear_button_pressed(self):
        if len(self.proxies_container.proxy_list) == 0:
            self.log_write_line("Nothing to delete", 'error')
            return False
        status_list = self.get_selected_list_widget_items(self.status_list, ProxyStatus)
        if len(status_list) == 0:
            self.log_write_line("Status not selected", 'error')
            return False
        deleted_count = self.proxies_container.delete_all_with_status(status_list)
        self.log_write_line("{} proxies deleted".format(deleted_count), 'success' if deleted_count > 0 else 'warn')

    @update_ui_after
    @synchronized_ui
    @pyqtSlot()
    def on_import_button_pressed(self):
        file_path = QtWidgets.QFileDialog.getOpenFileName(None, 'Open')
        if file_path[0] == '':
            return False
        try:
            with open(file_path[0], 'r+') as r:
                if file_path[0].endswith('.json'):
                    added_count = self.proxies_container.add_from_json(r.read())
                else:
                    added_count = self.proxies_container.add_from_txt(r.read(), lambda: ProxyType(
                        self.msg_box_with_buttons([e.name for e in ProxyType], self.version,
                                                  "If type dont not specified use ")))
        except Exception as e:
            self.log_write_line("An exception was thrown: {}".format(e), 'error')
            return False
        self.log_write_line("{} proxies added".format(added_count), 'success' if added_count > 0 else 'warn')

    @synchronized_ui
    @pyqtSlot()
    def on_checking_start_button_pressed(self):
        check_list = self.proxies_container.get_all_with_status(self.get_selected_list_widget_items(self.status_list, ProxyStatus))
        if len(check_list) == 0:
            self.log_write_line("Nothing to check", 'error')
            return False
        threads = self.checking_threads_spinbox.value()
        checking_class = None
        for i in range(self.checkers_list.count()):
            if self.checkers_list.item(i).checkState() == Qt.Checked:
                checking_class = self.checkers[i]
        if checking_class is None:
            self.log_write_line("Checker not selected", 'error')
            return False

        def on_start():
            self.background_executing_tasks_count += 1
            self.log_write_line_signal.emit("Checking {} proxies with {} threads".format(len(check_list), threads),
                                             'default')

        def on_end(result):
            self.background_executing_tasks_count -= 1
            self.log_write_line_signal.emit("Successfully checked", 'default')
            self.update_ui_signal.emit()

        self.background_thread.multiple_http_works(on_start, on_end, check_list, threads, checking_class.check,
                                                   min_speed_s=self.checking_timeout_spinbox.value(),
                                                   max_retries=self.checking_retries_spinbox.value(),
                                                   url_override=self.checking_url_edit.text(),
                                                   pattern_override=self.checking_pattern_edit.text()
                                                   )
