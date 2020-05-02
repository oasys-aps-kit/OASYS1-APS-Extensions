__author__ = 'labx'

from PyQt5.QtWidgets import QMessageBox

import os

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import congruence
from oasys.widgets import gui as oasysgui
from oasys.util.oasys_util import TriggerIn

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.widgets.special_elements.ow_hybrid_screen import AbstractHybridScreen

import oasys.util.oasys_util as OU

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
    crl_material_data = Setting(0)
    crl_material = Setting("Be")
    crl_delta = Setting(1e-6)
    crl_scaling_factor = Setting(1.0)

    def __init__(self):
        super(APSHybridScreen, self).__init__()

    def setErrorProfiles(self, error_profiles):
        try:
            if not error_profiles is None:
                self.convert_thickness_files(error_profiles)

                if self.ghy_calcType==5: self.refresh_files_text_area()
        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception


    def convert_thickness_files(self, error_profiles):
        self.crl_error_profiles = []

        for thickness_error_file in error_profiles:
            xx, yy, zz = OU.read_surface_file(thickness_error_file)

            xx /= self.workspace_units_to_m
            yy /= self.workspace_units_to_m
            zz /= self.workspace_units_to_m

            filename, _ = os.path.splitext(os.path.basename(thickness_error_file))

            thickness_error_file = filename + "_hybrid.h5"

            OU.write_surface_file(zz, xx, yy, thickness_error_file)

            self.crl_error_profiles.append(thickness_error_file)

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

        input_box = oasysgui.widgetBox(tab_thick, "Thickness Error Files", addSpace=True, orientation="vertical", height=390, width=self.CONTROL_AREA_WIDTH-20)

        gui.comboBox(input_box, self, "crl_material_data", label="Material Properties from", labelWidth=180,
                             items=["Chemical Formula", "Absorption Parameters"],
                             callback=self.set_CrlMaterialData,
                             sendSelectedValue=False, orientation="horizontal")

        self.input_box_1 = oasysgui.widgetBox(input_box, "", addSpace=False, orientation="vertical", width=self.CONTROL_AREA_WIDTH-40)
        self.input_box_2 = oasysgui.widgetBox(input_box, "", addSpace=False, orientation="vertical", width=self.CONTROL_AREA_WIDTH-40)

        oasysgui.lineEdit(self.input_box_1, self, "crl_material", "Chemical Formula", labelWidth=260, valueType=str, orientation="horizontal")
        oasysgui.lineEdit(self.input_box_2, self, "crl_delta", "Refractive Index (\u03b4)", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_CrlMaterialData()

        self.files_area = oasysgui.textArea(height=265)

        input_box.layout().addWidget(self.files_area)

        self.refresh_files_text_area()

        oasysgui.lineEdit(input_box, self, "crl_scaling_factor", "Thickness Error Scaling Factor", labelWidth=260, valueType=float, orientation="horizontal")

    def set_CrlMaterialData(self):
        self.input_box_1.setVisible(self.crl_material_data==0)
        self.input_box_2.setVisible(self.crl_material_data==1)

    def add_input_parameters_aux(self, input_parameters):
        input_parameters.absorber_material = None
        input_parameters.absorber_delta = None
        input_parameters.absorber_error_profiles = None

        if self.ghy_calcType==5:
            self.check_fields_aux()

            input_parameters.absorber_error_profiles = self.crl_error_profiles

            if self.crl_material_data==0: input_parameters.absorber_material = self.crl_material
            else: input_parameters.absorber_delta = self.crl_delta

            input_parameters.crl_scaling_factor = self.crl_scaling_factor

    def check_fields_aux(self):
        if len(self.crl_error_profiles) == 0: raise ValueError("No Thickness error profile specified")
        if self.crl_material_data==0: self.crl_material = congruence.checkEmptyString(self.crl_material, "Chemical Formula")
        else: congruence.checkStrictlyPositiveNumber(self.crl_delta, "Refractive Index (\u03b4)")
        congruence.checkPositiveNumber(self.crl_scaling_factor, "Thickness Error Scaling Factor")
