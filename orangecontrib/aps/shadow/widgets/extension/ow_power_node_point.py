import sys, numpy

from PyQt5.QtGui import QPalette, QFont, QColor
from PyQt5.QtWidgets import QApplication, QMessageBox

from orangewidget.widget import OWAction
from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import widget
from oasys.widgets import gui as oasysgui
from oasys.widgets.gui import ConfirmDialog
from oasys.widgets import congruence

from oasys.util.oasys_util import TriggerIn, TriggerOut
from oasys.widgets.exchange import DataExchangeObject

import scipy.constants as codata

class EnergyBinning(object):
    def __init__(self,
                 energy_value_from = 0.0,
                 energy_value_to   = 0.0,
                 energy_value_step = 0.0):
        self.energy_value_from = energy_value_from
        self.energy_value_to   = energy_value_to
        self.energy_value_step = energy_value_step

    def __str__(self):
        return str(self.energy_value_from) + ", " + str(self.energy_value_to) + ", " + str(self.energy_value_step) + ", " + str(self.power_step)

class PowerLoopPoint(widget.OWWidget):

    name = "Power Density Loop Point"
    description = "Tools: LoopPoint"
    icon = "icons/cycle.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Trigger", TriggerIn, "passTrigger"),
              ("ExchangeData", DataExchangeObject, "acceptExchangeData" )]

    outputs = [{"name":"Trigger",
                "type":TriggerOut,
                "doc":"Trigger",
                "id":"Trigger"}]
    want_main_area = 0

    current_new_object = 0
    number_of_new_objects = 0
    
    total_current_new_object = 0
    total_new_objects = Setting(0)

    run_loop = True
    suspend_loop = False

    energies = Setting("")

    seed_increment=Setting(1)

    auto_n_step = Setting(1001)
    auto_perc_total_power = Setting(99)

    current_energy_binning = 0
    current_energy_value = None
    current_energy_step = None

    power_step = None

    energy_binnings = None

    test_mode = False

    external_binning = False

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
        self.setFixedHeight(680)

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

        self.test_button = gui.button(button_box, self, "Test", callback=self.test_loop)
        self.test_button.setFixedHeight(35)

        left_box_1 = oasysgui.widgetBox(self.controlArea, "Loop Management", addSpace=True, orientation="vertical", width=385, height=520)

        oasysgui.lineEdit(left_box_1, self, "seed_increment", "Source Montecarlo Seed Increment", labelWidth=250, valueType=int, orientation="horizontal")

        oasysgui.lineEdit(left_box_1, self, "auto_n_step", "(Auto) Number of Steps", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "auto_perc_total_power", "(Auto) % Total Power", labelWidth=250, valueType=float, orientation="horizontal")

        gui.separator(left_box_1)

        oasysgui.widgetLabel(left_box_1, "Energy From, Energy To, Energy Step [eV]")

        def write_text():
            self.energies = self.text_area.toPlainText()

        self.text_area = oasysgui.textArea(height=210, width=360, readOnly=False)
        self.text_area.setText(self.energies)
        self.text_area.setStyleSheet("background-color: white; font-family: Courier, monospace;")
        self.text_area.textChanged.connect(write_text)

        left_box_1.layout().addWidget(self.text_area)

        gui.separator(left_box_1)

        gui.button(left_box_1, self, "Show Loop", callback=self.show_test_loop)

        self.le_number_of_new_objects = oasysgui.lineEdit(left_box_1, self, "total_new_objects", "Total Energy Values", labelWidth=250, valueType=int, orientation="horizontal")
        self.le_number_of_new_objects.setReadOnly(True)
        font = QFont(self.le_number_of_new_objects.font())
        font.setBold(True)
        self.le_number_of_new_objects.setFont(font)
        palette = QPalette(self.le_number_of_new_objects.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_number_of_new_objects.setPalette(palette)

        self.le_number_of_new_objects = oasysgui.lineEdit(left_box_1, self, "number_of_new_objects", "Current Binning Energy Values", labelWidth=250, valueType=int, orientation="horizontal")
        self.le_number_of_new_objects.setReadOnly(True)
        font = QFont(self.le_number_of_new_objects.font())
        font.setBold(True)
        self.le_number_of_new_objects.setFont(font)
        palette = QPalette(self.le_number_of_new_objects.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        self.le_number_of_new_objects.setPalette(palette)

        gui.separator(left_box_1)

        le_current_value = oasysgui.lineEdit(left_box_1, self, "total_current_new_object", "Total New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        le_current_value.setReadOnly(True)
        font = QFont(le_current_value.font())
        font.setBold(True)
        le_current_value.setFont(font)
        palette = QPalette(le_current_value.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_current_value.setPalette(palette)

        le_current_value = oasysgui.lineEdit(left_box_1, self, "current_new_object", "Current Binning New " + self.get_object_name(), labelWidth=250, valueType=int, orientation="horizontal")
        le_current_value.setReadOnly(True)
        font = QFont(le_current_value.font())
        font.setBold(True)
        le_current_value.setFont(font)
        palette = QPalette(le_current_value.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_current_value.setPalette(palette)

        le_current_value = oasysgui.lineEdit(left_box_1, self, "current_energy_value", "Current Energy Value", labelWidth=250, valueType=float, orientation="horizontal")
        le_current_value.setReadOnly(True)
        font = QFont(le_current_value.font())
        font.setBold(True)
        le_current_value.setFont(font)
        palette = QPalette(le_current_value.palette()) # make a copy of the palette
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_current_value.setPalette(palette)

        gui.rubber(self.controlArea)

    def acceptExchangeData(self, exchange_data):
        if not exchange_data is None:
            try:
                data = exchange_data.get_content("srw_data")

                congruence.checkStrictlyPositiveNumber(self.auto_n_step, "(Auto) % Number of Steps")
                congruence.checkStrictlyPositiveNumber(self.auto_perc_total_power, "(Auto) % Total Power")

                energies = data[:, 0]
                flux     = data[:, 1]

                energy_step = energies[1]-energies[0]

                power = flux * (1e3 * energy_step * codata.e)
                cumulated_power = numpy.cumsum(power)

                total_power = cumulated_power[-1]

                good = numpy.where(cumulated_power < self.auto_perc_total_power*0.01*total_power)

                energies        = energies[good]
                cumulated_power = cumulated_power[good]

                power_values = numpy.linspace(start=0, stop=numpy.max(cumulated_power), num=self.auto_n_step)
                power_values = power_values[1:]

                self.power_step = power_values[1]-power_values[0]

                interpolated_upper_energies = numpy.interp(power_values, cumulated_power, energies)
                interpolated_upper_energies = numpy.insert(interpolated_upper_energies, 0, energies[0])

                energy_bins = numpy.diff(interpolated_upper_energies)

                power_values -= 0.5*self.power_step

                interpolated_central_energies = numpy.interp(power_values, cumulated_power, energies)

                self.energy_binnings = []
                self.total_new_objects = 0

                text = "Binner Ouput\nCentral Energy, Energy Bin\n-------------------------"
                for energy, energy_bin in zip(interpolated_central_energies, energy_bins):
                    energy_binning = EnergyBinning(energy, -1, energy_bin)
                    text += "\n" + str(round(energy, 2)) + ", " + str(round(energy_bin, 2))
                    self.energy_binnings.append(energy_binning)
                    self.total_new_objects += 1

                self.text_area.setText(text)
                self.text_area.setEnabled(False)

                self.external_binning = True
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)
        else:
            self.energy_binnings = None
            self.total_new_objects = 0
            self.power_step = None
            self.external_binning = False
            self.text_area.setText("")
            self.text_area.setEnabled(True)

    def calculate_energy_binnings(self):
        if not self.external_binning:
            self.total_new_objects = 0
            self.power_step = None

            rows = self.energies.split("\n")
            for row in rows:
                data = row.split(",")
                if len(data) == 3:
                    if self.energy_binnings is None: self.energy_binnings = []

                    energy_binning = EnergyBinning(float(data[0].strip()), float(data[1].strip()), float(data[2].strip()))
                    self.energy_binnings.append(energy_binning)
                    self.total_new_objects += int((energy_binning.energy_value_to - energy_binning.energy_value_from) / energy_binning.energy_value_step)

    def calculate_number_of_new_objects(self):
        if len(self.energy_binnings) > 0:
            if self.external_binning:
                self.number_of_new_objects = 1
            else:
                energy_binning = self.energy_binnings[self.current_energy_binning]

                self.number_of_new_objects = int((energy_binning.energy_value_to - energy_binning.energy_value_from) / energy_binning.energy_value_step)
        else:
            self.number_of_new_objects = 0

    def reset_values(self):
        self.current_new_object = 0
        self.total_current_new_object = 0
        self.current_energy_value = None
        self.current_energy_step = None
        self.current_energy_binning = 0
        self.current_power_step = None

        if not self.external_binning: self.energy_binnings = None

        self.test_mode = False

    def startLoop(self):
        try:
            self.calculate_energy_binnings()

            self.current_new_object = 1
            self.total_current_new_object = 1
            self.current_energy_binning = 0
            self.current_energy_value = round(self.energy_binnings[0].energy_value_from, 8)
            self.current_energy_step = round(self.energy_binnings[0].energy_value_step, 8)

            self.calculate_number_of_new_objects()

            self.start_button.setEnabled(False)
            self.test_button.setEnabled(False)
            self.text_area.setEnabled(False)
            self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.total_current_new_object) + " of " + str(self.total_new_objects))
            self.send("Trigger", TriggerOut(new_object=True,
                                            additional_parameters={"energy_value" : self.current_energy_value,
                                                                   "energy_step" : self.current_energy_step,
                                                                   "power_step" : -1 if self.power_step is None else self.power_step,
                                                                   "seed_increment" : self.seed_increment}))
        except:
            pass

    def stopLoop(self):
        try:
            if ConfirmDialog.confirmed(parent=self, message="Confirm Interruption of the Loop?"):
                self.run_loop = False
                self.reset_values()
                self.setStatusMessage("Interrupted by user")
        except:
            pass

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

    def get_object_name(self):
        return "Beam"

    def test_loop(self):
        self.test_mode = True
        self.setStatusMessage("Testing Loop")
        self.startLoop()

    def passTrigger(self, trigger):
        if self.run_loop:
            if trigger:
                if trigger.interrupt:
                    self.reset_values()
                    self.start_button.setEnabled(True)
                    self.test_button.setEnabled(True)
                    self.text_area.setEnabled(True)
                    self.setStatusMessage("")
                    self.send("Trigger", TriggerOut(new_object=False))
                elif trigger.new_object:
                    if self.energy_binnings is None: self.calculate_energy_binnings()

                    if self.current_energy_binning < len(self.energy_binnings):
                        energy_binning = self.energy_binnings[self.current_energy_binning]

                        self.total_current_new_object += 1

                        if self.current_new_object < self.number_of_new_objects:
                            if self.current_energy_value is None:
                                self.current_new_object = 1
                                self.calculate_number_of_new_objects()
                                self.current_energy_value = round(energy_binning.energy_value_from, 8)

                            else:
                                self.current_new_object += 1
                                self.current_energy_value = round(self.current_energy_value + energy_binning.energy_value_step, 8)

                            self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.total_current_new_object) + " of " + str(self.total_new_objects))
                            self.start_button.setEnabled(False)
                            self.test_button.setEnabled(False)
                            self.text_area.setEnabled(False)
                            self.send("Trigger", TriggerOut(new_object=True,
                                                            additional_parameters={"energy_value" : self.current_energy_value,
                                                                                   "energy_step" : energy_binning.energy_value_step,
                                                                                   "power_step" : -1 if self.power_step is None else self.power_step,
                                                                                   "seed_increment" : self.seed_increment,
                                                                                   "test_mode" : self.test_mode}))
                        else:
                            self.current_energy_binning += 1

                            if self.current_energy_binning < len(self.energy_binnings):
                                energy_binning = self.energy_binnings[self.current_energy_binning]

                                self.current_new_object = 1
                                self.calculate_number_of_new_objects()
                                self.current_energy_value = round(energy_binning.energy_value_from, 8)

                                self.setStatusMessage("Running " + self.get_object_name() + " " + str(self.total_current_new_object) + " of " + str(self.total_new_objects))
                                self.start_button.setEnabled(False)
                                self.test_button.setEnabled(False)
                                self.text_area.setEnabled(False)
                                self.send("Trigger", TriggerOut(new_object=True,
                                                                additional_parameters={"energy_value" : self.current_energy_value,
                                                                                       "energy_step" : energy_binning.energy_value_step,
                                                                                       "power_step" : -1 if self.power_step is None else self.power_step,
                                                                                       "seed_increment" : self.seed_increment,
                                                                                       "test_mode" : self.test_mode}))
                            else:
                                self.reset_values()
                                self.start_button.setEnabled(True)
                                self.test_button.setEnabled(True)
                                self.text_area.setEnabled(True)
                                self.setStatusMessage("")
                                self.send("Trigger", TriggerOut(new_object=False))
                    else:
                        self.reset_values()
                        self.start_button.setEnabled(True)
                        self.test_button.setEnabled(True)
                        self.text_area.setEnabled(True)
                        self.setStatusMessage("")
                        self.send("Trigger", TriggerOut(new_object=False))
        else:
            if not self.suspend_loop:
                self.reset_values()
                self.start_button.setEnabled(True)
                self.test_button.setEnabled(True)
                self.text_area.setEnabled(True)

            self.send("Trigger", TriggerOut(new_object=False))
            self.setStatusMessage("")
            self.suspend_loop = False
            self.run_loop = True

    def show_test_loop(self):
        self.calculate_energy_binnings()

        self.current_new_object = 1
        self.total_current_new_object = 1
        self.current_energy_binning = 0
        self.current_energy_value = round(self.energy_binnings[0].energy_value_from, 8)
        self.current_energy_step = round(self.energy_binnings[0].energy_value_step, 8)

        self.calculate_number_of_new_objects()
        self.start_button.setEnabled(False)
        self.test_button.setEnabled(False)
        self.text_area.setEnabled(False)
        self.run_loop = True

        self.setStatusMessage("Testing Loop")

        try:
            text = []

            triggerOut, textOut = self.passTestTrigger(TriggerIn(new_object=True))

            text.append(textOut)

            while(triggerOut and triggerOut.new_object):
                triggerOut, textOut = self.passTestTrigger(TriggerIn(new_object=True))
                text.append(textOut)

            from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout, QLabel
            class ScrollMessageBox(QMessageBox):
               def __init__(self, text_array, title, *args, **kwargs):
                  QMessageBox.__init__(self, *args, **kwargs)
                  self.setWindowTitle(title)
                  scroll = QScrollArea(self)
                  scroll.setWidgetResizable(True)
                  scroll.setStyleSheet("background-color: white; font-family: Courier, monospace;")
                  self.content = QWidget()
                  scroll.setWidget(self.content)
                  lay = QVBoxLayout(self.content)
                  for item in text_array: lay.addWidget(QLabel(item, self))
                  self.layout().addWidget(scroll, 0, 0, 1, self.layout().columnCount())
                  self.setStyleSheet("QScrollArea{min-width:300 px; min-height: 400px;}")

            ScrollMessageBox(text, "Test Loop").exec_()
        except:
            pass

        self.start_button.setEnabled(True)
        self.test_button.setEnabled(True)
        self.text_area.setEnabled(True)
        self.setStatusMessage("")

    def passTestTrigger(self, trigger):

        text = ""
        triggerOut = None

        if self.run_loop:
           if trigger.new_object:
                if self.energy_binnings is None: self.calculate_energy_binnings()

                if self.current_energy_binning < len(self.energy_binnings):
                    energy_binning = self.energy_binnings[self.current_energy_binning]

                    self.total_current_new_object += 1

                    if self.current_new_object < self.number_of_new_objects:
                        if self.current_energy_value is None:
                            self.current_new_object = 1
                            self.calculate_number_of_new_objects()
                            self.current_energy_value = round(energy_binning.energy_value_from, 8)
                        else:
                            self.current_new_object += 1
                            self.current_energy_value = round(self.current_energy_value + energy_binning.energy_value_step, 8)

                        text = str(self.current_energy_value) + ", " + str(energy_binning.energy_value_step)

                        triggerOut = TriggerOut(new_object=True,
                                                additional_parameters={"energy_value" : self.current_energy_value,
                                                                       "energy_step" : energy_binning.energy_value_step,
                                                                       "power_step" : -1 if self.power_step is None else self.power_step,
                                                                       "seed_increment" : self.seed_increment,
                                                                       "test_mode": True})
                    else:
                        self.current_energy_binning += 1

                        if self.current_energy_binning < len(self.energy_binnings):
                            energy_binning = self.energy_binnings[self.current_energy_binning]

                            self.current_new_object = 1
                            self.calculate_number_of_new_objects()
                            self.current_energy_value = round(energy_binning.energy_value_from, 8)

                            text = str(self.current_energy_value) + ", " + str(energy_binning.energy_value_step)

                            triggerOut = TriggerOut(new_object=True,
                                                    additional_parameters={"energy_value" : self.current_energy_value,
                                                                           "energy_step" : energy_binning.energy_value_step,
                                                                           "power_step" : -1 if self.power_step is None else self.power_step,
                                                                           "seed_increment" : self.seed_increment,
                                                                           "test_mode": True})
                        else:
                            self.current_new_object = 0
                            self.total_current_new_object = 0
                            self.reset_values()
                            triggerOut = TriggerOut(new_object=False)
                else:
                    self.current_new_object = 0
                    self.total_current_new_object = 0
                    self.reset_values()
                    triggerOut =  TriggerOut(new_object=False)
        else:
            if not self.suspend_loop:
                self.current_new_object = 0
                self.total_current_new_object = 0
                self.current_energy_value = None

            self.run_loop = True
            self.suspend_loop = False

            triggerOut =  TriggerOut(new_object=False)

        return triggerOut, text

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = PowerLoopPoint()
    ow.show()
    a.exec_()
    ow.saveSettings()
