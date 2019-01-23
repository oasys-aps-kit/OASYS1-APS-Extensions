import sys

from PyQt5.QtGui import QImage, QPixmap,  QPalette, QFont, QColor, QTextCursor
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QMessageBox, QFileDialog

from orangewidget import gui
from orangewidget.widget import OWAction
from orangewidget.settings import Setting

from oasys.widgets import widget
from oasys.widgets import gui as oasysgui
from oasys.widgets.gui import ConfirmDialog

from oasys.util.oasys_util import TriggerIn, TriggerOut

class ScanLoopPoint(widget.OWWidget):

    name = "Scanning File Loop Point"
    description = "Tools: LoopPoint"
    icon = "icons/cycle.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 6
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Trigger", TriggerIn, "passTrigger"),
              ("Files", list, "setFiles")]

    outputs = [{"name":"Trigger",
                "type":TriggerOut,
                "doc":"Trigger",
                "id":"Trigger"}]
    want_main_area = 0

    number_of_new_objects = Setting(1)
    current_new_object = 0
    run_loop = True
    suspend_loop = False

    files_area = None

    variable_name         = Setting("<variable name>")
    variable_display_name = Setting("<variable display name>")
    variable_files         = Setting([""])

    current_variable_value = None

    #################################
    process_last = True
    #################################

    def __init__(self):
        self.runaction = OWAction("Start", self)
        self.runaction.triggered.connect(self.startLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Stop", self)
        self.runaction.triggered.connect(self.stopLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Suspend", self)
        self.runaction.triggered.connect(self.suspendLoop)
        self.addAction(self.runaction)

        self.runaction = OWAction("Restart", self)
        self.runaction.triggered.connect(self.restartLoop)
        self.addAction(self.runaction)

        self.setFixedWidth(400)
        self.setFixedHeight(500)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        self.start_button = gui.button(button_box, self, "Start", callback=self.startLoop)
        self.start_button.setFixedHeight(35)

        stop_button = gui.button(button_box, self, "Stop", callback=self.stopLoop)
        stop_button.setFixedHeight(35)
        font = QFont(stop_button.font())
        font.setBold(True)
        stop_button.setFont(font)
        palette = QPalette(stop_button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('red'))
        stop_button.setPalette(palette) # assign new palette

        self.stop_button = stop_button

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=True, orientation="horizontal")

        suspend_button = gui.button(button_box, self, "Suspend", callback=self.suspendLoop)
        suspend_button.setFixedHeight(35)
        font = QFont(suspend_button.font())
        font.setBold(True)
        suspend_button.setFont(font)
        palette = QPalette(suspend_button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('orange'))
        suspend_button.setPalette(palette) # assign new palette

        self.re_start_button = gui.button(button_box, self, "Restart", callback=self.restartLoop)
        self.re_start_button.setFixedHeight(35)
        self.re_start_button.setEnabled(False)

        left_box_1 = oasysgui.widgetBox(self.controlArea, "Loop Management", addSpace=True, orientation="vertical", width=380, height=380)

        oasysgui.lineEdit(left_box_1, self, "variable_name", "Variable Name", labelWidth=100, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "variable_display_name", "Variable Display Name", labelWidth=100, valueType=str, orientation="horizontal")

        box_files = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=170)

        gui.button(box_files, self, "Select Height Error Profile Data Files", callback=self.select_files)

        self.files_area = oasysgui.textArea(height=120, width=360)

        self.refresh_files_text_area()

        box_files.layout().addWidget(self.files_area)

        gui.separator(left_box_1)

        self.le_current_new_object = oasysgui.lineEdit(left_box_1, self, "current_new_object", "Current New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        self.le_current_new_object.setReadOnly(True)
        font = QFont(self.le_current_new_object.font())
        font.setBold(True)
        self.le_current_new_object.setFont(font)
        palette = QPalette(self.le_current_new_object.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_current_new_object.setPalette(palette)

        self.le_current_new_object = oasysgui.lineEdit(left_box_1, self, "current_variable_value", "Current Variable Value", labelWidth=250, valueType=str, orientation="horizontal")
        self.le_current_new_object.setReadOnly(True)
        font = QFont(self.le_current_new_object.font())
        font.setBold(True)
        self.le_current_new_object.setFont(font)
        palette = QPalette(self.le_current_new_object.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_current_new_object.setPalette(palette)

        gui.rubber(self.controlArea)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "Select Height Error Profiles", "", "Data Files (*.dat)",
                                                options=QFileDialog.Options())
        if files:
            self.variable_files = files

            self.refresh_files_text_area()

    def setFiles(self, files_data):
        if not files_data is None:
            if isinstance(files_data, str):
                self.variable_files.append(files_data)
            elif isinstance(files_data, list):
                self.variable_files = files_data
            else:
                raise ValueError("Error Profile Data File: format not recognized")

            self.refresh_files_text_area()

    def refresh_files_text_area(self):
        text = ""
        for file in self.variable_files:
            text += file + "\n"
        self.files_area.setText(text)

        self.number_of_new_objects = len(self.variable_files)

    def startLoop(self):
        self.current_new_object = 1
        self.current_variable_value = self.variable_files[0]
        self.number_of_new_objects = len(self.variable_files)

        self.start_button.setEnabled(False)

        self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.current_new_object) + " of " + str(self.number_of_new_objects))
        self.send("Trigger", TriggerOut(new_object=True, additional_parameters={"variable_name" : self.variable_name,
                                                                                "variable_display_name" : self.variable_display_name,
                                                                                "variable_value": self.current_variable_value,
                                                                                "variable_um": ""}))
    def stopLoop(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Interruption of the Loop?"):
            self.run_loop = False
            self.current_variable_value = None
            self.setStatusMessage("Interrupted by user")

    def suspendLoop(self):
        try:
            if ConfirmDialog.confirmed(parent=self, message="Confirm Suspension of the Loop?"):
                self.run_loop = False
                self.suspend_loop = True
                self.stop_button.setEnabled(False)
                self.re_start_button.setEnabled(True)
                self.setStatusMessage("Suspended by user")
        except:
            pass

    def restartLoop(self):
        try:
            self.run_loop = True
            self.suspend_loop = False
            self.stop_button.setEnabled(True)
            self.re_start_button.setEnabled(False)
            self.passTrigger(TriggerIn(new_object=True))
        except:
            pass

    def passTrigger(self, trigger):
        if self.run_loop:
            if trigger:
                if trigger.interrupt:
                    self.current_new_object = 0
                    self.current_variable_value = None
                    self.start_button.setEnabled(True)
                    self.setStatusMessage("")
                    self.send("Trigger", TriggerOut(new_object=False))
                elif trigger.new_object:
                    if self.current_new_object < self.number_of_new_objects:
                        if self.current_variable_value is None:
                            self.current_new_object = 1
                        else:
                            self.current_new_object += 1

                        self.current_variable_value = self.variable_files[self.current_new_object-1]

                        self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.current_new_object) + " of " + str(self.number_of_new_objects))
                        self.start_button.setEnabled(False)
                        self.send("Trigger", TriggerOut(new_object=True, additional_parameters={"variable_name" : self.variable_name,
                                                                                                "variable_display_name" : self.variable_display_name,
                                                                                                "variable_value": self.current_variable_value,
                                                                                                "variable_um": ""}))
                    else:
                        self.current_new_object = 0
                        self.current_variable_value = None
                        self.start_button.setEnabled(True)
                        self.setStatusMessage("")
                        self.send("Trigger", TriggerOut(new_object=False))
        else:
            if not self.suspend_loop:
                self.current_new_object = 0
                self.current_variable_value = None
                self.start_button.setEnabled(True)

            self.send("Trigger", TriggerOut(new_object=False))
            self.setStatusMessage("")
            self.run_loop = True
            self.suspend_loop = False
            
    def get_object_name(self):
        return "File"

from PyQt5.QtWidgets import QApplication

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = ScanLoopPoint()
    ow.show()
    a.exec_()
    ow.saveSettings()
