import sys

from orangewidget.widget import OWAction
from oasys.widgets import widget
from oasys.widgets import gui as oasysgui
from oasys.widgets.gui import ConfirmDialog

from orangewidget import gui
from PyQt5 import QtGui
from orangewidget.settings import Setting

from oasys.util.oasys_util import TriggerIn, TriggerOut

class ScanLoopPoint(widget.OWWidget):

    name = "Scanning Variable Loop Point"
    description = "Tools: LoopPoint"
    icon = "icons/cycle.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 6
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Trigger", TriggerIn, "passTrigger")]

    outputs = [{"name":"Trigger",
                "type":TriggerOut,
                "doc":"Trigger",
                "id":"Trigger"}]
    want_main_area = 0

    number_of_new_objects = Setting(1)
    current_new_object = 0
    run_loop = True

    variable_name = Setting("<variable name>")
    variable_display_name = Setting("<variable display name>")
    variable_value_from = Setting(0.0)
    variable_value_to = Setting(0.0)
    variable_value_step = 0.0

    variable_um = Setting("<u.m.>")
    
    current_variable_value = None

    #################################
    process_last = True
    #################################

    def __init__(self):
        self.runaction = OWAction("Start Loop", self)
        self.runaction.triggered.connect(self.startLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Interrupt", self)
        self.runaction.triggered.connect(self.stopLoop)
        self.addAction(self.runaction)

        self.setFixedWidth(400)
        self.setFixedHeight(365)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        self.start_button = gui.button(button_box, self, "Start Loop", callback=self.startLoop)
        self.start_button.setFixedHeight(45)

        stop_button = gui.button(button_box, self, "Interrupt", callback=self.stopLoop)
        stop_button.setFixedHeight(45)
        font = QtGui.QFont(stop_button.font())
        font.setBold(True)
        stop_button.setFont(font)
        palette = QtGui.QPalette(stop_button.palette()) # make a copy of the palette
        palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor('red'))
        stop_button.setPalette(palette) # assign new palette

        left_box_1 = oasysgui.widgetBox(self.controlArea, "Loop Management", addSpace=True, orientation="vertical", width=380, height=280)

        oasysgui.lineEdit(left_box_1, self, "variable_name", "Variable Name", labelWidth=100, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "variable_display_name", "Variable Display Name", labelWidth=100, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "variable_um", "Variable Units", labelWidth=250, valueType=str, orientation="horizontal")

        oasysgui.lineEdit(left_box_1, self, "variable_value_from", "Value From", labelWidth=250, valueType=float, orientation="horizontal", callback=self.calculate_step)
        oasysgui.lineEdit(left_box_1, self, "variable_value_to", "Value to", labelWidth=250, valueType=float, orientation="horizontal", callback=self.calculate_step)
        oasysgui.lineEdit(left_box_1, self, "number_of_new_objects", "Number of Steps", labelWidth=250, valueType=int, orientation="horizontal", callback=self.calculate_step)


        self.le_variable_value_step = oasysgui.lineEdit(left_box_1, self, "variable_value_step", "Step Value", labelWidth=250, valueType=float, orientation="horizontal")
        self.le_variable_value_step.setReadOnly(True)
        font = QtGui.QFont(self.le_variable_value_step.font())
        font.setBold(True)
        self.le_variable_value_step.setFont(font)
        palette = QtGui.QPalette(self.le_variable_value_step.palette()) # make a copy of the palette
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor('dark blue'))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(243, 240, 160))
        self.le_variable_value_step.setPalette(palette)

        gui.separator(left_box_1)

        self.le_current_new_object = oasysgui.lineEdit(left_box_1, self, "current_new_object", "Current New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        self.le_current_new_object.setReadOnly(True)
        font = QtGui.QFont(self.le_current_new_object.font())
        font.setBold(True)
        self.le_current_new_object.setFont(font)
        palette = QtGui.QPalette(self.le_current_new_object.palette()) # make a copy of the palette
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor('dark blue'))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(243, 240, 160))
        self.le_current_new_object.setPalette(palette)

        self.le_current_new_object = oasysgui.lineEdit(left_box_1, self, "current_variable_value", "Current Variable Value", labelWidth=250, valueType=float, orientation="horizontal")
        self.le_current_new_object.setReadOnly(True)
        font = QtGui.QFont(self.le_current_new_object.font())
        font.setBold(True)
        self.le_current_new_object.setFont(font)
        palette = QtGui.QPalette(self.le_current_new_object.palette()) # make a copy of the palette
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor('dark blue'))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(243, 240, 160))
        self.le_current_new_object.setPalette(palette)

        gui.rubber(self.controlArea)

    def calculate_step(self):
        self.variable_value_step = round((self.variable_value_to - self.variable_value_from) / self.number_of_new_objects, 8)

    def startLoop(self):

        self.current_new_object = 1
        self.current_variable_value = round(self.variable_value_from, 8)
        self.calculate_step()
        self.start_button.setEnabled(False)

        self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.current_new_object) + " of " + str(self.number_of_new_objects))
        self.send("Trigger", TriggerOut(new_object=True, additional_parameters={"variable_name" : self.variable_name,
                                                                                "variable_display_name" : self.variable_display_name,
                                                                                "variable_value": self.current_variable_value,
                                                                                "variable_um": self.variable_um}))
    def stopLoop(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Interruption of the Loop?"):
            self.run_loop = False
            self.current_value = None
            self.setStatusMessage("Interrupted by user")

    def passTrigger(self, trigger):
        if self.run_loop:
            if trigger:
                if trigger.interrupt:
                    self.current_new_object = 0
                    self.current_variable_value = None
                    self.variable_value_step = 0.0
                    self.start_button.setEnabled(True)
                    self.setStatusMessage("")
                    self.send("Trigger", TriggerOut(new_object=False))
                elif trigger.new_object:
                    if self.current_new_object <= self.number_of_new_objects:
                        if self.current_variable_value is None:
                            self.current_new_object = 1
                            self.calculate_step()
                            self.current_variable_value = round(self.variable_value_from, 8)
                        else:
                            self.current_new_object += 1
                            self.current_variable_value = round(self.current_variable_value + self.variable_value_step, 8)

                        self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.current_new_object) + " of " + str(self.number_of_new_objects))
                        self.start_button.setEnabled(False)
                        self.send("Trigger", TriggerOut(new_object=True, additional_parameters={"variable_name" : self.variable_name,
                                                                                                "variable_display_name" : self.variable_display_name,
                                                                                                "variable_value": self.current_variable_value,
                                                                                                "variable_um": self.variable_um}))
                    else:
                        self.current_new_object = 0
                        self.current_variable_value = None
                        self.start_button.setEnabled(True)
                        self.setStatusMessage("")
                        self.send("Trigger", TriggerOut(new_object=False))
        else:
            self.current_new_object = 0
            self.current_variable_value = None
            self.start_button.setEnabled(True)
            self.send("Trigger", TriggerOut(new_object=False))
            self.setStatusMessage("")
            self.run_loop = True

    def get_object_name(self):
        return "Object"

if __name__ == "__main__":
    a = QtGui.QApplication(sys.argv)
    ow = ScanLoopPoint()
    ow.show()
    a.exec_()
    ow.saveSettings()
