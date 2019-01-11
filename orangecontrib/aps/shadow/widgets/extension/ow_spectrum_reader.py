import sys, numpy, copy

from PyQt5.QtWidgets import QApplication, QMessageBox

from oasys.widgets import widget
from oasys.widgets.exchange import DataExchangeObject

from orangewidget import  gui

class SpectrumReader(widget.OWWidget):

    name = "Spectrum Reader"
    description = "Tools: Spectrum Reader"
    icon = "icons/beam_file_reader.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    outputs = [{"name":"ExchangeData",
                "type":DataExchangeObject,
                "doc":"ExchangeData",
                "id":"beam"}]

    want_main_area = 0
    want_control_area = 1

    def __init__(self):

         self.setFixedWidth(300)
         self.setFixedHeight(100)

         gui.separator(self.controlArea, height=40)
         gui.button(self.controlArea, self, "Read Spectrum File (autobinning.dat)", callback=self.read_spectrum_file)
         gui.rubber(self.controlArea)

    def read_spectrum_file(self):
        try:
            data = numpy.loadtxt("autobinning.dat", skiprows=1)

            calculated_data = DataExchangeObject(program_name="SRW", widget_name="UNDULATOR_SPECTRUM")
            calculated_data.add_content("srw_data", data)

            self.send("ExchangeData", calculated_data)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

            if self.IS_DEVELOP: raise e

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = SpectrumReader()
    ow.show()
    a.exec_()
    ow.saveSettings()
