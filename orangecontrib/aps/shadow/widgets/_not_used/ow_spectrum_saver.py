import sys, numpy, copy

from PyQt5.QtWidgets import QApplication, QMessageBox
from oasys.widgets import widget

from orangewidget import  gui

from oasys.widgets.exchange import DataExchangeObject

class SpectrumSaver(widget.OWWidget):

    name = "Spectrum Saver"
    description = "Tools: Spectrum Saver"
    icon = "icons/beam_file_writer.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("ExchangeData", DataExchangeObject, "acceptExchangeData")]

    want_main_area = 0
    want_control_area = 1

    def __init__(self):

         self.setFixedWidth(300)
         self.setFixedHeight(100)

         gui.separator(self.controlArea, height=20)
         gui.label(self.controlArea, self, "         Spectrum Saver", orientation="horizontal")
         gui.rubber(self.controlArea)

    def acceptExchangeData(self, exchange_data):
        if not exchange_data is None:
            try:
                try:
                    data = exchange_data.get_content("srw_data")
                except:
                    data = exchange_data.get_content("xoppy_data")

                energies = data[:, 0]
                fluxes = data[:, 1]

                file = open("autobinning.dat", "w")
                file.write("Energy Flux")

                for energy, flux in zip(energies, fluxes):
                    file.write("\n" + str(energy) + " " + str(flux))

                file.flush()
                file.close()

                QMessageBox.information(self, "Info", "File autobinning.dat written on working directory", QMessageBox.Ok)
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e), QMessageBox.Ok)

                if self.IS_DEVELOP: raise e

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = SpectrumSaver()
    ow.show()
    a.exec_()
    ow.saveSettings()
