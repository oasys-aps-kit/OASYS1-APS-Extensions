__author__ = 'labx'

import os, sys, numpy
import orangecanvas.resources as resources
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from orangewidget import gui, widget
from orangewidget.settings import Setting
from oasys.util.oasys_util import EmittingStream, TriggerIn

from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot
from orangecontrib.shadow.util.shadow_objects import ShadowBeam

from PyQt5.QtGui import QImage, QPixmap,  QPalette, QFont, QColor, QTextCursor
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QMessageBox

from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.shadow.widgets.special_elements import hybrid_control

from silx.gui.plot.ImageView import ImageView

from orangecontrib.shadow.widgets.special_elements.ow_hybrid_screen import AbstractHybridScreen

class APSHybridScreen(AbstractHybridScreen):

    inputs = [("Input Beam", ShadowBeam, "setBeam"),
              ("Error Profiles", list, "setErrorProfiles")]

    outputs = [{"name":"Output Beam (Far Field)",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam_ff"},
               {"name":"Output Beam (Near Field)",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam_nf"},
               {"name":"Trigger",
                "type": TriggerIn,
                "doc":"Feedback signal to start a new beam simulation",
                "id":"Trigger"}]

    name = "APS Hybrid Screen"
    description = "Shadow HYBRID: Hybrid Screen"
    icon = "icons/hybrid_screen.png"
    maintainer = "Luca Rebuffi and Xianbo Shi"
    maintainer_email = "lrebuffi(@at@)anl.gov, xshi(@at@)aps.anl.gov"
    priority = 40
    category = "HYBRID"
    keywords = ["data", "file", "load", "read"]

    error_profiles = Setting([""])

    def __init__(self):
        super(APSHybridScreen, self).__init__()

    def setErrorProfiles(self, error_profiles):
        if not error_profiles is None:
            self.error_profiles = error_profiles

    def get_calculation_type_items(self):
        return ["Diffraction by Simple Aperture",
                "Diffraction by Mirror or Grating Size",
                "Diffraction by Mirror Size + Figure Errors",
                "Diffraction by Grating Size + Figure Errors",
                "Diffraction by Lens/C.R.L./Transf. Size",
                "Diffraction by Lens/C.R.L./Transf. Size + Thickness Errors"]
