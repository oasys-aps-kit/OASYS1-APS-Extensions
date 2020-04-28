import sys
from orangewidget import gui
from PyQt5.QtWidgets import QApplication

from orangecontrib.shadow.widgets.gui import ow_ellipsoid_element, ow_optical_element
from orangecontrib.shadow.util import ShadowOpticalElement

class BendableEllipsoidMirror(ow_ellipsoid_element.EllipsoidElement):

    name = "Bendable Ellipsoid Mirror"
    description = "Shadow OE: Bendable Ellipsoid Mirror"
    icon = "icons/bendable_ellipsoid_mirror.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 6
    category = "Optical Elements"
    keywords = ["data", "file", "load", "read"]

    def __init__(self):
        graphical_Options=ow_optical_element.GraphicalOptions(is_mirror=True)

        super().__init__(graphical_Options)


        gui.rubber(self.controlArea)

        gui.rubber(self.mainArea)

    ################################################################
    #
    #  SHADOW MANAGEMENT
    #
    ################################################################

    def completeOperations(self, shadow_oe):
        super().completeOperations(shadow_oe)

        print("ciao")

    def instantiateShadowOE(self):
        return ShadowOpticalElement.create_ellipsoid_mirror()

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = BendableEllipsoidMirror()
    ow.show()
    a.exec_()
    ow.saveSettings()
