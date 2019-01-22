__author__ = 'labx'

import xraylib
from PyQt5 import QtWidgets
from oasys.menus.menu import OMenu

from orangecontrib.aps.shadow.widgets.extension.ow_power_plot_xy import PowerPlotXY

class APSShadowToolsMenu(OMenu):
    def __init__(self):
        super().__init__(name="APS Shadow Tools")

        self.openContainer()
        self.addContainer("Cumulative Plotting")
        self.addSubMenu("Enable all the Power Plot XY widgets")
        self.addSubMenu("Disable all the Power Plot XY widgets")
        self.addSeparator()
        self.addSubMenu("Select Plotting \"Yes\" in all the Power Plot XY widgets")
        self.addSubMenu("Select Plotting \"No\" in all the Power Plot XY widgets")
        self.addSeparator()
        self.addSubMenu("Clear all the cumulated plots in Power Plot XY widgets")
        self.closeContainer()

    def executeAction_1(self, action):
        try:
            for link in self.canvas_main_window.current_document().scheme().links:
                if not link.enabled:
                    widget = self.canvas_main_window.current_document().scheme().widget_for_node(link.sink_node)

                    if isinstance(widget, PowerPlotXY): link.set_enabled(True)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

    def executeAction_2(self, action):
        try:
            for link in self.canvas_main_window.current_document().scheme().links:
                if link.enabled:
                    widget = self.canvas_main_window.current_document().scheme().widget_for_node(link.sink_node)

                    if isinstance(widget, PowerPlotXY): link.set_enabled(False)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

    def executeAction_3(self, action):
        try:
            for node in self.canvas_main_window.current_document().scheme().nodes:
                widget = self.canvas_main_window.current_document().scheme().widget_for_node(node)

                if isinstance(widget, PowerPlotXY): widget.view_type = 1
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)

    def executeAction_4(self, action):
        try:
            for node in self.canvas_main_window.current_document().scheme().nodes:
                widget = self.canvas_main_window.current_document().scheme().widget_for_node(node)

                if isinstance(widget, PowerPlotXY): widget.view_type = 0
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)


    def executeAction_5(self, action):
        try:
            for node in self.canvas_main_window.current_document().scheme().nodes:
                widget = self.canvas_main_window.current_document().scheme().widget_for_node(node)

                if isinstance(widget, PowerPlotXY): widget.clearResults(interactive=False)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(None, "Error",
                exception.args[0],
                QtWidgets.QMessageBox.Ok)
