import sys

from PyQt5.QtWidgets import QApplication, QMessageBox
from oasys.widgets import widget

from orangewidget import  gui

from orangecontrib.shadow.util.shadow_objects import ShadowPreProcessorData

class PreprocessorAdapter(widget.OWWidget):

    name = "Preprocessor Data Adapter"
    description = "Tools: Preprocessor Data Adapter"
    icon = "icons/simulator_adapter.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 4
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("PreProcessorData", ShadowPreProcessorData, "acceptPreProcessorData")]

    outputs = [{"name":"Files",
                "type":object,
                "doc":"Files",
                "id":"Files"}]

    want_main_area = 0
    want_control_area = 1

    def __init__(self):

         self.setFixedWidth(300)
         self.setFixedHeight(100)

         gui.separator(self.controlArea, height=20)
         gui.label(self.controlArea, self, "     Preprocessor Data Adapter", orientation="horizontal")
         gui.rubber(self.controlArea)

    def acceptPreProcessorData(self, data):
        try:
            if data is not None:
                if data.error_profile_data_file != ShadowPreProcessorData.NONE:
                    if isinstance(data.error_profile_data_file, str):
                        self.send("Files", data.error_profile_data_file)
                    elif isinstance(data.error_profile_data_file, list):
                        self.send("Files", data.error_profile_data_file)
                    else:
                        raise ValueError("Error Profile Data File: format not recognized")
        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = PreprocessorAdapter()
    ow.show()
    a.exec_()
    ow.saveSettings()
