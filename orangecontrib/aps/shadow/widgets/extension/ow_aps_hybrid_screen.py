__author__ = 'labx'

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets import gui as oasysgui
from oasys.util.oasys_util import TriggerIn

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
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

    crl_error_profiles = Setting([])
    crl_material = Setting("Be")

    def __init__(self):
        super(APSHybridScreen, self).__init__()

    def setErrorProfiles(self, error_profiles):
        if not error_profiles is None:
            self.crl_error_profiles = [error_profile[1] for error_profile in error_profiles] # h5 file only
            if self.ghy_calcType==5: self.refresh_files_text_area()

    def get_calculation_type_items(self):
        return ["Diffraction by Simple Aperture",
                "Diffraction by Mirror or Grating Size",
                "Diffraction by Mirror Size + Figure Errors",
                "Diffraction by Grating Size + Figure Errors",
                "Diffraction by Lens/C.R.L./Transf. Size",
                "Diffraction by Lens/C.R.L./Transf. Size + Thickness Errors"]

    def refresh_files_text_area(self):
        text = ""

        for file in self.crl_error_profiles:
            text += file + "\n"

        self.files_area.setText(text)

    def remove_files(self):
        self.crl_error_profiles = []
        self.files_area.setText("")

    def set_CalculationType_Aux(self):
        self.cb_ghy_diff_plane.setEnabled(True)

        if self.tabs_setting.count()==3:
            self.tabs_setting.removeTab(2)

        if self.ghy_calcType == 5:
            self.createTabThickness()
            self.ghy_diff_plane = 2
            self.set_DiffPlane()
            self.cb_ghy_diff_plane.setEnabled(False)



    def createTabThickness(self):
        tab_thick = oasysgui.createTabPage(self.tabs_setting, "Thickness Error")

        input_box = oasysgui.widgetBox(tab_thick, "Thickness Error Files", addSpace=True, orientation="vertical", height=350, width=self.CONTROL_AREA_WIDTH-20)

        oasysgui.lineEdit(input_box, self, "crl_material", "CRLs material", labelWidth=260, valueType=str, orientation="horizontal")

        gui.button(input_box, self, "Remove Thickness Error Profile Data Files", callback=self.remove_files)

        self.files_area = oasysgui.textArea(height=250)

        input_box.layout().addWidget(self.files_area)

        self.refresh_files_text_area()

    def add_input_parameters_aux(self, input_parameters):
        if self.ghy_calcType==5 and len(self.crl_error_profiles) > 0:
            input_parameters.crl_error_profiles = self.crl_error_profiles
            input_parameters.crl_material = self.crl_material
        else:
            input_parameters.crl_error_profiles = None
            input_parameters.crl_material = None
