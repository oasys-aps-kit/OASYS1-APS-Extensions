import numpy, copy
from numpy import nan

from PyQt5.QtGui import QPalette, QColor, QFont
from PyQt5.QtWidgets import QMessageBox

from orangewidget import gui
from orangewidget import widget
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog
from oasys.util.oasys_util import TriggerIn, TriggerOut
import oasys.util.oasys_util as OU

from srxraylib.util.data_structures import ScaledMatrix

from scipy.interpolate import RectBivariateSpline

from wofrysrw.propagator.wavefront2D.srw_wavefront import SRWWavefront, PolarizationComponent, Polarization
from wofrysrw.beamline.optical_elements.other.srw_crl import SRWCRL
from wofry.propagator.propagator import PropagationManager
from wofrysrw.propagator.propagators2D.srw_fresnel_native import SRW_APPLICATION
from wofrysrw.propagator.propagators2D.srw_propagation_mode import SRWPropagationMode


from orangecontrib.srw.util.srw_objects import SRWData
from orangecontrib.srw.util.srw_util import SRWPlot
from orangecontrib.srw.widgets.gui.ow_srw_wavefront_viewer import SRWWavefrontViewer


class OWThicknessErrorPhaseShift(SRWWavefrontViewer):
    name = "Thickness Error Phase Shift"
    description = "Thickness Error Phase Shift"
    icon = "icons/thickness_phase_shifter.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "Display Data Tools"
    keywords = ["data", "file", "load", "read"]

    outputs = [{"name":"SRWData",
                "type":SRWData,
                "doc":"SRW Optical Element Data",
                "id":"data"},
               {"name":"Trigger",
                "type": TriggerIn,
                "doc":"Feedback signal to start a new beam simulation",
                "id":"Trigger"}]

    inputs = [("SRWData", SRWData, "set_input"),
              ("Error Profiles", list, "setErrorProfiles"),
              ("Trigger", TriggerOut, "propagate_new_wavefront")]

    crl_error_profiles = Setting([])
    crl_scaling_factor = Setting(1.0)

    TABS_AREA_HEIGHT = 555
    CONTROL_AREA_WIDTH = 405

    def __init__(self):
        super().__init__()

        self.runaction = widget.OWAction("Propagate Wavefront", self)
        self.runaction.triggered.connect(self.propagate_wavefront)
        self.addAction(self.runaction)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Propagate Wavefront", callback=self.propagate_wavefront)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Reset Fields", callback=self.callResetSettings)
        font = QFont(button.font())
        font.setItalic(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Red'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)
        button.setFixedWidth(150)

        gui.separator(self.controlArea)

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        self.tabs_setting = oasysgui.tabWidget(self.controlArea)
        self.tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        self.tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_thick = oasysgui.createTabPage(self.tabs_setting, "Thickness Error")

        input_box = oasysgui.widgetBox(tab_thick, "Thickness Error Files", addSpace=True, orientation="vertical", height=390, width=self.CONTROL_AREA_WIDTH-20)

        self.files_area = oasysgui.textArea(height=315)

        input_box.layout().addWidget(self.files_area)

        self.refresh_files_text_area()

        oasysgui.lineEdit(input_box, self, "crl_scaling_factor", "Thickness Error Scaling Factor", labelWidth=260, valueType=float, orientation="horizontal")

    def refresh_files_text_area(self):
        text = ""

        for file in self.crl_error_profiles:
            text += file + "\n"

        self.files_area.setText(text)

    def setErrorProfiles(self, error_profiles):
        try:
            if not error_profiles is None:
                self.crl_error_profiles = error_profiles

                self.refresh_files_text_area()
        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def set_input(self, srw_data):
        if not srw_data is None:
            self.input_srw_data = srw_data

            if self.is_automatic_run:
                self.propagate_wavefront()

    def set_srw_live_propagation_mode(self):
        if PropagationManager.Instance().get_propagation_mode(SRW_APPLICATION)==SRWPropagationMode.WHOLE_BEAMLINE:
            raise ValueError("Propagation Mode not supported, switch to Element by Element")
        else:
            super(OWThicknessErrorPhaseShift, self).set_srw_live_propagation_mode()

    def propagate_wavefront(self):
        try:
            self.progressBarInit()

            if self.input_srw_data is None: raise Exception("No Input Data")

            self.check_data()

            input_wavefront      = self.input_srw_data.get_srw_wavefront().duplicate()
            srw_beamline         = self.input_srw_data.get_srw_beamline().duplicate()
            optical_element      = srw_beamline.get_beamline_element_at(-1).get_optical_element()
            coordinates          = srw_beamline.get_beamline_element_at(-1).get_coordinates()

            if not isinstance(optical_element, SRWCRL):
                raise ValueError("Thickness Error Phase Shift should be connected to a CRL optical element")

            if coordinates.q() != 0.0:
                raise ValueError("Thickness Error Phase Shift should be applied on unpropagated wavefronts: put 'q' value to 0.0 in the previous optical element")

            crl_delta = optical_element.delta
            crl_w_mirr_2D_values = [OWThicknessErrorPhaseShift.h5_readsurface(thickness_error_file) for thickness_error_file in self.crl_error_profiles]

            # TO WOFRY
            generic_wavefront = input_wavefront.toGenericWavefront()

            for thickness_error_profile in crl_w_mirr_2D_values:
                phase_shift = OWThicknessErrorPhaseShift.get_crl_phase_shift(thickness_error_profile, crl_delta, generic_wavefront, self.crl_scaling_factor)

                generic_wavefront.add_phase_shift(phase_shift, Polarization.SIGMA)
                generic_wavefront.add_phase_shift(phase_shift, Polarization.PI)

            # TO SRW
            output_wavefront     = SRWWavefront.fromGenericWavefront(generic_wavefront)

            output_wavefront.Rx  = input_wavefront.Rx
            output_wavefront.Ry  = input_wavefront.Ry
            output_wavefront.dRx  = input_wavefront.dRx
            output_wavefront.dRy  = input_wavefront.dRy
            output_wavefront.xc  = input_wavefront.xc
            output_wavefront.yc = input_wavefront.yc
            output_wavefront.avgPhotEn  = input_wavefront.avgPhotEn
            output_wavefront.presCA = input_wavefront.presCA
            output_wavefront.presFT  = input_wavefront.presFT
            output_wavefront.unitElFld  = input_wavefront.unitElFld
            output_wavefront.arElecPropMatr  = copy.deepcopy(input_wavefront.arElecPropMatr)
            output_wavefront.arMomX  = copy.deepcopy(input_wavefront.arMomX)
            output_wavefront.arMomY  = copy.deepcopy(input_wavefront.arMomY)
            output_wavefront.arWfrAuxData  = copy.deepcopy(input_wavefront.arWfrAuxData)
            output_wavefront.partBeam = copy.deepcopy(input_wavefront.partBeam)

            output_wavefront.setScanningData(input_wavefront.scanned_variable_data)

            output_srw_data = SRWData(srw_beamline=srw_beamline, srw_wavefront=output_wavefront)

            self.progressBarSet(50)

            self.initializeTabs()

            tickets = []

            self.run_calculation_for_plots(output_wavefront=output_wavefront, tickets=tickets, progress_bar_value=50)

            self.plot_results(tickets, 80)

            self.progressBarFinished()
            self.setStatusMessage("")

            self.send("SRWData", output_srw_data)
            self.send("Trigger", TriggerIn(new_object=True))

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e.args[0]), QMessageBox.Ok)

            self.setStatusMessage("")
            self.progressBarFinished()

            if self.IS_DEVELOP: raise e

    def run_calculation_for_plots(self, output_wavefront, tickets, progress_bar_value):
        if self.view_type==2:
            e, h, v, i = output_wavefront.get_intensity(multi_electron=False, polarization_component_to_be_extracted=PolarizationComponent.LINEAR_HORIZONTAL)

            tickets.append(SRWPlot.get_ticket_2D(h*1000, v*1000, i[int(e.size/2)]))

            self.progressBarSet(progress_bar_value)

            e, h, v, i = output_wavefront.get_intensity(multi_electron=False, polarization_component_to_be_extracted=PolarizationComponent.LINEAR_VERTICAL)

            tickets.append(SRWPlot.get_ticket_2D(h*1000, v*1000, i[int(e.size/2)]))

            e, h, v, p = output_wavefront.get_phase(polarization_component_to_be_extracted=PolarizationComponent.LINEAR_HORIZONTAL)

            tickets.append(SRWPlot.get_ticket_2D(h*1000, v*1000, p[int(e.size/2)]))

            self.progressBarSet(progress_bar_value + 10)

            e, h, v, p = output_wavefront.get_phase(polarization_component_to_be_extracted=PolarizationComponent.LINEAR_VERTICAL)

            tickets.append(SRWPlot.get_ticket_2D(h*1000, v*1000, p[int(e.size/2)]))

        elif self.view_type==1:
            e, h, v, i = output_wavefront.get_intensity(multi_electron=False)

            tickets.append(SRWPlot.get_ticket_2D(h*1000, v*1000, i[int(e.size/2)]))

            self.progressBarSet(progress_bar_value)

            e, h, v, p = output_wavefront.get_phase()

            tickets.append(SRWPlot.get_ticket_2D(h*1000, v*1000, p[int(e.size/2)]))

        self.progressBarSet(progress_bar_value + 10)

    def propagate_new_wavefront(self, trigger):
        try:
            if trigger and trigger.new_object == True:
                if trigger.has_additional_parameter("variable_name"):
                    if self.input_srw_data is None: raise Exception("No Input Data")

                    variable_name = trigger.get_additional_parameter("variable_name").strip()
                    variable_display_name = trigger.get_additional_parameter("variable_display_name").strip()
                    variable_value = trigger.get_additional_parameter("variable_value")
                    variable_um = trigger.get_additional_parameter("variable_um")

                    if "," in variable_name:
                        variable_names = variable_name.split(",")

                        for variable_name in variable_names:
                            setattr(self, variable_name.strip(), variable_value)
                    else:
                        setattr(self, variable_name, variable_value)

                    self.input_srw_data.get_srw_wavefront().setScanningData(SRWWavefront.ScanningData(variable_name, variable_value, variable_display_name, variable_um))
                    self.propagate_wavefront()

        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def check_data(self):
        if len(self.crl_error_profiles) == 0: raise ValueError("No Thickness error profile specified")
        congruence.checkPositiveNumber(self.crl_scaling_factor, "Thickness Error Scaling Factor")

    @classmethod
    def h5_readsurface(cls, filename):
        x_coords, y_coords, z_values = OU.read_surface_file(filename)

        return ScaledMatrix(x_coords, y_coords, z_values.T)

    @classmethod
    def get_crl_phase_shift(cls, thickness_error_profile, crl_delta, wavefront, crl_scaling_factor=1.0):
        coord_x = thickness_error_profile.x_coord
        coord_y = thickness_error_profile.y_coord
        thickness_error = thickness_error_profile.z_values

        interpolator = RectBivariateSpline(coord_x, coord_y, thickness_error, bbox=[None, None, None, None], kx=1, ky=1, s=0)

        wavelength = wavefront.get_wavelength()
        wavefront_coord_x = wavefront.get_coordinate_x()
        wavefront_coord_y = wavefront.get_coordinate_y()

        thickness_error = interpolator(wavefront_coord_x, wavefront_coord_y)
        thickness_error[numpy.where(thickness_error==numpy.nan)] = 0.0
        thickness_error *= crl_scaling_factor

        return -2*numpy.pi*crl_delta*thickness_error/wavelength

    def getVariablesToPlot(self):
        if self.view_type == 2:
            return [[1, 2], [1, 2], [1, 2], [1, 2]]
        else:
            return [[1, 2], [1, 2]]

    def getWeightedPlots(self):
        if self.view_type == 2:
            return [False, False, True, True]
        else:
            return [False, True]

    def getWeightTickets(self):
        if self.view_type == 2:
            return [nan, nan, 0, 1]
        else:
            return [nan, 0]

    def getTitles(self, with_um=False):
        if self.view_type == 2:
            if with_um: return ["Intensity SE \u03c0 [ph/s/.1%bw/mm\u00b2]",
                                "Intensity SE \u03c3 [ph/s/.1%bw/mm\u00b2]",
                                "Phase SE \u03c0 [rad]",
                                "Phase SE \u03c0 [rad]"]
            else: return ["Intensity SE \u03c0",
                          "Intensity SE \u03c3",
                          "Phase SE \u03c0",
                          "Phase SE \u03c3"]
        else:
            if with_um: return ["Intensity SE [ph/s/.1%bw/mm\u00b2]",
                                "Phase SE [rad]"]
            else: return ["Intensity SE",
                          "Phase SE"]

    def getXTitles(self):
        if self.view_type == 2:
            return ["X [\u03bcm]", "X [\u03bcm]", "X [\u03bcm]", "X [\u03bcm]"]
        else:
            return ["X [\u03bcm]", "X [\u03bcm]"]

    def getYTitles(self):
        if self.view_type == 2:
            return ["Y [\u03bcm]", "Y [\u03bcm]", "Y [\u03bcm]", "Y [\u03bcm]"]
        else:
            return ["Y [\u03bcm]", "Y [\u03bcm]"]

    def getXUM(self):
        if self.view_type == 2:
            return ["X [\u03bcm]", "X [\u03bcm]", "X [\u03bcm]", "X [\u03bcm]"]
        else:
            return ["X [\u03bcm]", "X [\u03bcm]"]

    def getYUM(self):
        if self.view_type == 2:
            return ["Y [\u03bcm]", "Y [\u03bcm]", "Y [\u03bcm]", "Y [\u03bcm]"]
        else:
            return ["Y [\u03bcm]", "Y [\u03bcm]"]

    def callResetSettings(self):
        if ConfirmDialog.confirmed(parent=self, message="Confirm Reset of the Fields?"):
            try:
                self.resetSettings()
            except:
                pass
