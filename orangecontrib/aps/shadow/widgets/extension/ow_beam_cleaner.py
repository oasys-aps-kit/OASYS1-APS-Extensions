import sys, numpy, copy

from oasys.widgets import widget

from orangewidget import  gui

from PyQt5 import QtGui

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence

class BeamCleaner(widget.OWWidget):

    name = "Beam Cleaner"
    description = "Tools: Beam Cleaner"
    icon = "icons/clean.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "luca.rebuffi(@at@)elettra.eu"
    priority = 30
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    outputs = [{"name":"Beam",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam"}]

    want_main_area = 0
    want_control_area = 1

    def __init__(self):

         self.setFixedWidth(300)
         self.setFixedHeight(100)

         gui.separator(self.controlArea, height=20)
         gui.label(self.controlArea, self, "         LOST RAYS REMOVER", orientation="horizontal")
         gui.rubber(self.controlArea)

    def setBeam(self, beam):
        if ShadowCongruence.checkEmptyBeam(beam):

            good = numpy.where(beam._beam.rays[:, 9] == 1)
            beam._beam.rays = copy.deepcopy(beam._beam.rays[good])

            self.send("Beam", beam)

if __name__ == "__main__":
    a = QtGui.QApplication(sys.argv)
    ow = BeamCleaner()
    ow.show()
    a.exec_()
    ow.saveSettings()
