import numpy
from numpy.matlib import repmat
from scipy import stats
from scipy.signal import convolve2d

from PyQt5 import QtGui, QtWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QPalette, QColor, QFont
from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from orangewidget import widget
from oasys.util.oasys_util import TriggerOut

from orangecontrib.shadow.util.shadow_objects import ShadowBeam, ShadowSource
from orangecontrib.shadow.widgets.gui.ow_generic_element import GenericElement

import scipy.constants as codata

m2ev = codata.c * codata.h / codata.e

from srwlib import *

class Distribution:
    POSITION = 0
    DIVERGENCE = 1

class APSUndulator(GenericElement):

    TABS_AREA_HEIGHT = 620

    name = "APS Undulator"
    description = "Shadow Source: APS Undulator"
    icon = "icons/undulator.png"
    priority = 1
    maintainer = "Luca Rebuffi"
    maintainer_email = "luca.rebuffi(@at@)elettra.eu"
    category = "Sources"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Trigger", TriggerOut, "sendNewBeam")]

    outputs = [{"name":"Beam",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam"}]


    distribution_source = Setting(0)

    # SRW INPUT

    number_of_periods = Setting(184) # Number of ID Periods (without counting for terminations
    undulator_period =  Setting(0.025) # Period Length [m]
    Kv =  Setting(0.857)
    Kh =  Setting(0)

    electron_energy_in_GeV = Setting(6.0)
    electron_energy_spread = Setting(1.35e-3)
    ring_current = Setting(0.2)
    electron_beam_size_h = Setting(1.45e-05)
    electron_beam_size_v = Setting(2.8e-06)
    electron_beam_divergence_h = Setting(2.9e-06)
    electron_beam_divergence_v = Setting(1.5e-06)

    source_dimension_wf_h_slit_gap = Setting(0.0015)
    source_dimension_wf_v_slit_gap = Setting(0.0015)
    source_dimension_wf_h_slit_points=Setting(301)
    source_dimension_wf_v_slit_points=Setting(301)
    source_dimension_wf_distance = Setting(28.0)

    angular_distribution_wf_h_slit_gap = Setting(0.008)
    angular_distribution_wf_v_slit_gap = Setting(0.008)
    angular_distribution_wf_h_slit_points=Setting(601)
    angular_distribution_wf_v_slit_points=Setting(601)
    angular_distribution_wf_distance = Setting(100.0)

    save_srw_result = Setting(1)

    # SRW FILE INPUT

    source_dimension_srw_file     = Setting("intensity_source_dimension.dat")
    angular_distribution_srw_file = Setting("intensity_angular_distribution.dat")

    # ASCII FILE INPUT

    x_positions_file = Setting("x_positions.txt")
    z_positions_file = Setting("z_positions.txt")
    x_positions_factor = Setting(0.01)
    z_positions_factor = Setting(0.01)
    x_divergences_file = Setting("x_divergences.txt")
    z_divergences_file = Setting("z_divergences.txt")
    x_divergences_factor = Setting(1.0)
    z_divergences_factor = Setting(1.0)

    combine_strategy = Setting(0)

    # SHADOW SETTINGS

    number_of_rays=Setting(5000)
    seed=Setting(6775431)

    use_harmonic = Setting(0)
    harmonic_number = Setting(1)
    energy=Setting(10000.0)

    polarization = Setting(1)
    coherent_beam = Setting(0)
    phase_diff = Setting(0.0)
    polarization_degree = Setting(1.0)

    optimize_source=Setting(0)
    optimize_file_name = Setting("NONESPECIFIED")
    max_number_of_rejected_rays = Setting(10000000)

    file_to_write_out = Setting(0)

    def __init__(self, show_automatic_box=False):
        super().__init__(show_automatic_box=show_automatic_box)

        self.runaction = widget.OWAction("Run Shadow/Source", self)
        self.runaction.triggered.connect(self.runShadowSource)
        self.addAction(self.runaction)

        self.general_options_box.setVisible(False)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Run Shadow/Source", callback=self.runShadowSource)
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

        ######################################

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_shadow = oasysgui.createTabPage(tabs_setting, "Shadow Setting")
        tab_spdiv = oasysgui.createTabPage(tabs_setting, "Position/Divergence Setting")

        gui.comboBox(tab_spdiv, self, "distribution_source", label="Distribution Source", labelWidth=310,
                     items=["SRW Calculation", "SRW Files", "ASCII Files"], orientation="horizontal", callback=self.set_DistributionSource)

        self.srw_box = oasysgui.widgetBox(tab_spdiv, "SRW Setting", addSpace=False, orientation="vertical", height=540)
        self.srw_files_box = oasysgui.widgetBox(tab_spdiv, "SRW Files Load Setting", addSpace=False, orientation="vertical", height=540)
        self.ascii_box = oasysgui.widgetBox(tab_spdiv, "ASCII Files Load Setting", addSpace=False, orientation="vertical", height=540)

        self.set_DistributionSource()

        ####################################################################################
        # SHADOW

        left_box_1 = oasysgui.widgetBox(tab_shadow, "Monte Carlo and Energy Spectrum", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "number_of_rays", "Number of Rays", tooltip="Number of Rays", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "seed", "Seed", tooltip="Seed (0=clock)", labelWidth=250, valueType=int, orientation="horizontal")

        gui.comboBox(left_box_1, self, "use_harmonic", label="Photon Energy Setting",
                     items=["Harmonic", "Other"], labelWidth=260,
                     callback=self.set_WFUseHarmonic, sendSelectedValue=False, orientation="horizontal")

        self.use_harmonic_box_1 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=30)
        oasysgui.lineEdit(self.use_harmonic_box_1, self, "harmonic_number", "Harmonic #", labelWidth=260, valueType=int, orientation="horizontal")

        self.use_harmonic_box_2 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=30)
        oasysgui.lineEdit(self.use_harmonic_box_2, self, "energy", "Photon Energy [eV]", labelWidth=260, valueType=float, orientation="horizontal")

        self.set_WFUseHarmonic()


        polarization_box = oasysgui.widgetBox(tab_shadow, "Polarization", addSpace=False, orientation="vertical", height=140)

        gui.comboBox(polarization_box, self, "polarization", label="Polarization", labelWidth=310,
                     items=["No", "Yes"], orientation="horizontal", callback=self.set_Polarization)

        self.ewp_box_8 = oasysgui.widgetBox(polarization_box, "", addSpace=False, orientation="vertical")

        gui.comboBox(self.ewp_box_8, self, "coherent_beam", label="Coherent Beam", labelWidth=310,
                     items=["No", "Yes"], orientation="horizontal")

        oasysgui.lineEdit(self.ewp_box_8, self, "phase_diff", "Phase Difference [deg,0=linear,+90=ell/right]", labelWidth=310, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ewp_box_8, self, "polarization_degree", "Polarization Degree [cos_s/(cos_s+sin_s)]", labelWidth=310, valueType=float, orientation="horizontal")

        self.set_Polarization()

        ##############################

        left_box_4 = oasysgui.widgetBox(tab_shadow, "Reject Rays", addSpace=False, orientation="vertical", height=140)

        gui.comboBox(left_box_4, self, "optimize_source", label="Optimize Source", items=["No", "Using file with phase/space volume)", "Using file with slit/acceptance"],
                     labelWidth=120, callback=self.set_OptimizeSource, orientation="horizontal")
        self.optimize_file_name_box       = oasysgui.widgetBox(left_box_4, "", addSpace=False, orientation="vertical", height=80)

        file_box = oasysgui.widgetBox(self.optimize_file_name_box, "", addSpace=True, orientation="horizontal", height=25)

        self.le_optimize_file_name = oasysgui.lineEdit(file_box, self, "optimize_file_name", "File Name", labelWidth=100,  valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.selectOptimizeFile)

        oasysgui.lineEdit(self.optimize_file_name_box, self, "max_number_of_rejected_rays", "Max number of rejected rays (set 0 for infinity)", labelWidth=280,  valueType=int, orientation="horizontal")

        self.set_OptimizeSource()

        adv_other_box = oasysgui.widgetBox(tab_shadow, "Optional file output", addSpace=False, orientation="vertical")

        gui.comboBox(adv_other_box, self, "file_to_write_out", label="Files to write out", labelWidth=120,
                     items=["None", "Begin.dat", "Debug (begin.dat + start.xx/end.xx)"],
                     sendSelectedValue=False, orientation="horizontal")

        ####################################################################################
        # SRW

        tabs_srw = oasysgui.tabWidget(self.srw_box)

        gui.comboBox(self.srw_box, self, "save_srw_result", label="Save SRW results", labelWidth=310,
                     items=["No", "Yes"], orientation="horizontal", callback=self.set_SaveFileSRW)

        self.save_file_box = oasysgui.widgetBox(self.srw_box, "", addSpace=False, orientation="vertical")
        self.save_file_box_empty = oasysgui.widgetBox(self.srw_box, "", addSpace=False, orientation="vertical", height=55)

        file_box = oasysgui.widgetBox(self.save_file_box, "", addSpace=False, orientation="horizontal", height=25)

        self.le_source_dimension_srw_file = oasysgui.lineEdit(file_box, self, "source_dimension_srw_file", "Source Dimension File", labelWidth=140,  valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.selectSourceDimensionFile)

        file_box = oasysgui.widgetBox(self.save_file_box, "", addSpace=False, orientation="horizontal", height=25)

        self.le_angular_distribution_srw_file = oasysgui.lineEdit(file_box, self, "angular_distribution_srw_file", "Angular Distribution File", labelWidth=140,  valueType=str, orientation="horizontal")

        gui.button(file_box, self, "...", callback=self.selectAngularDistributionFile)

        self.set_SaveFileSRW()

        tab_ls = oasysgui.createTabPage(tabs_srw, "Undulator Setting")
        tab_wf = oasysgui.createTabPage(tabs_srw, "Wavefront Setting")

        left_box_1 = oasysgui.widgetBox(tab_ls, "Undulator Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "number_of_periods", "Number of Periods", labelWidth=260,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "undulator_period", "Undulator Period [m]", labelWidth=260,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "Kv", "K Vertical", labelWidth=260,  valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "Kh", "K Horizontal", labelWidth=260,  valueType=float, orientation="horizontal")

        left_box_2 = oasysgui.widgetBox(tab_ls, "Machine Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_2, self, "electron_energy_in_GeV", "Energy [GeV]", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_2, self, "electron_energy_spread", "Energy Spread", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_2, self, "ring_current", "Ring Current [A]", labelWidth=260, valueType=float, orientation="horizontal")
        
        #gui.separator(left_box_2)
        
        oasysgui.lineEdit(left_box_2, self, "electron_beam_size_h",       "Horizontal Beam Size [m]", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_2, self, "electron_beam_size_v",       "Vertical Beam Size [m]",  labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_2, self, "electron_beam_divergence_h", "Horizontal Beam Divergence [rad]", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_2, self, "electron_beam_divergence_v", "Vertical Beam Divergence [rad]", labelWidth=230, valueType=float, orientation="horizontal")

        left_box_3 = oasysgui.widgetBox(tab_wf, "Wavefront Propagation Parameters", addSpace=False, orientation="vertical")

        left_box_3_1 = oasysgui.widgetBox(left_box_3, "Source Dimension", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_3_1, self, "source_dimension_wf_h_slit_gap", "H Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_1, self, "source_dimension_wf_v_slit_gap", "V Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_1, self, "source_dimension_wf_h_slit_points", "H Slit Points", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_1, self, "source_dimension_wf_v_slit_points", "V Slit Points", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_1, self, "source_dimension_wf_distance", "Propagation Distance [m]", labelWidth=250, valueType=float, orientation="horizontal")

        left_box_3_2 = oasysgui.widgetBox(left_box_3, "Angular Distribution", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_3_2, self, "angular_distribution_wf_h_slit_gap", "H Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_2, self, "angular_distribution_wf_v_slit_gap", "V Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_2, self, "angular_distribution_wf_h_slit_points", "H Slit Points", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_2, self, "angular_distribution_wf_v_slit_points", "V Slit Points", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_3_2, self, "angular_distribution_wf_distance", "Propagation Distance [m]", labelWidth=250, valueType=float, orientation="horizontal")

        ####################################################################################
        # SRW FILES

        file_box = oasysgui.widgetBox(self.srw_files_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_source_dimension_srw_file = oasysgui.lineEdit(file_box, self, "source_dimension_srw_file", "Source Dimension File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectSourceDimensionFile)

        file_box = oasysgui.widgetBox(self.srw_files_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_angular_distribution_srw_file = oasysgui.lineEdit(file_box, self, "angular_distribution_srw_file", "Angular Distribution File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectAngularDistributionFile)


        ####################################################################################
        # ASCII FILES

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_x_positions_file = oasysgui.lineEdit(file_box, self, "x_positions_file", "X Positions File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectXPositionsFile)

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_z_positions_file = oasysgui.lineEdit(file_box, self, "z_positions_file", "Z Positions File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectZPositionsFile)

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_x_divergences_file = oasysgui.lineEdit(file_box, self, "x_divergences_file", "X Divergences File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectXDivergencesFile)

        file_box = oasysgui.widgetBox(self.ascii_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_z_divergences_file = oasysgui.lineEdit(file_box, self, "z_divergences_file", "Z Divergences File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectZDivergencesFile)

        gui.separator(self.ascii_box)

        oasysgui.lineEdit(self.ascii_box, self, "x_positions_factor",   "X Positions UM to Workspace UM", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ascii_box, self, "z_positions_factor",   "Z Positions UM to Workspace UM",  labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ascii_box, self, "x_divergences_factor", "X Divergences UM to rad", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.ascii_box, self, "z_divergences_factor", "X Divergences UM to rad", labelWidth=230, valueType=float, orientation="horizontal")

        gui.separator(self.ascii_box)

        gui.comboBox(self.ascii_box, self, "combine_strategy", label="2D Distribution Creation Strategy", labelWidth=310,
                     items=["Sqrt(Product)", "Sqrt(Quadratic Sum)", "Convolution", "Average"], orientation="horizontal", callback=self.set_SaveFileSRW)

        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)

    ####################################################################################
    # GRAPHICS
    ####################################################################################

    def after_change_workspace_units(self):
        pass

    def get_write_file_options(self):
        write_begin_file = 0
        write_start_file = 0
        write_end_file = 0

        if self.file_to_write_out == 1:
            write_begin_file = 1
        if self.file_to_write_out == 2:
            write_begin_file = 1

            if sys.platform == 'linux':
                QtWidgets.QMessageBox.warning(self, "Warning", "Debug Mode is not yet available for sources in Linux platforms", QtWidgets.QMessageBox.Ok)
            else:
                write_start_file = 1
                write_end_file = 1

        return write_begin_file, write_start_file, write_end_file

    def set_WFUseHarmonic(self):
        self.use_harmonic_box_1.setVisible(self.use_harmonic==0)
        self.use_harmonic_box_2.setVisible(self.use_harmonic==1)

    def set_DistributionSource(self):
        self.srw_box.setVisible(self.distribution_source == 0)
        self.srw_files_box.setVisible(self.distribution_source == 1)
        self.ascii_box.setVisible(self.distribution_source == 2)

    def set_Polarization(self):
        self.ewp_box_8.setVisible(self.polarization==1)

    def set_OptimizeSource(self):
        self.optimize_file_name_box.setVisible(self.optimize_source != 0)

    def set_SaveFileSRW(self):
        self.save_file_box.setVisible(self.save_srw_result == 1)
        self.save_file_box_empty.setVisible(self.save_srw_result == 0)

    def selectOptimizeFile(self):
        self.le_optimize_file_name.setText(oasysgui.selectFileFromDialog(self, self.optimize_file_name, "Open Optimize Source Parameters File"))

    def selectSourceDimensionFile(self):
        self.le_source_dimension_srw_file.setText(oasysgui.selectFileFromDialog(self, self.source_dimension_srw_file, "Open Source Dimension File"))

    def selectAngularDistributionFile(self):
        self.le_angular_distribution_srw_file.setText(oasysgui.selectFileFromDialog(self, self.angular_distribution_srw_file, "Open Angular Distribution File"))

    def selectXPositionsFile(self):
        self.le_x_positions_file.setText(oasysgui.selectFileFromDialog(self, self.x_positions_file, "Open X Positions File", file_extension_filter="*.dat, *.txt"))

    def selectZPositionsFile(self):
        self.le_z_positions_file.setText(oasysgui.selectFileFromDialog(self, self.z_positions_file, "Open Z Positions File", file_extension_filter="*.dat, *.txt"))

    def selectXDivergencesFile(self):
        self.le_x_divergences_file.setText(oasysgui.selectFileFromDialog(self, self.x_divergences_file, "Open X Divergences File", file_extension_filter="*.dat, *.txt"))

    def selectZDivergencesFile(self):
        self.le_z_divergences_file.setText(oasysgui.selectFileFromDialog(self, self.z_divergences_file, "Open Z Divergences File", file_extension_filter="*.dat, *.txt"))



    ####################################################################################
    # PROCEDURES
    ####################################################################################

    def runShadowSource(self):
        self.setStatusMessage("")
        self.progressBarInit()

        try:
            self.checkFields()

            ###########################################
            # TODO: TO BE ADDED JUST IN CASE OF BROKEN
            #       ENVIRONMENT: MUST BE FOUND A PROPER WAY
            #       TO TEST SHADOW
            self.fixWeirdShadowBug()
            ###########################################

            shadow_src = ShadowSource.create_src()

            self.populateFields(shadow_src)

            self.progressBarSet(10)

            self.setStatusMessage("Running SHADOW")

            write_begin_file, write_start_file, write_end_file = self.get_write_file_options()

            beam_out = ShadowBeam.traceFromSource(shadow_src,
                                                  write_begin_file=write_begin_file,
                                                  write_start_file=write_start_file,
                                                  write_end_file=write_end_file)

            self.fix_Intensity(beam_out)

            self.progressBarSet(20)

            if self.distribution_source == 0:
                self.setStatusMessage("Running SRW")

                x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution = self.runSRWCalculation()
            elif self.distribution_source == 1:
                self.setStatusMessage("Loading SRW files")

                x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution = self.loadSRWFiles()
            elif self.distribution_source == 2: # ASCII FILES
                self.setStatusMessage("Loading Ascii files")

                x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution = self.loadASCIIFiles()

            self.progressBarSet(50)

            self.setStatusMessage("Applying new Spatial/Angular Distribution")

            self.progressBarSet(60)

            self.generate_user_defined_distribution_from_srw(beam_out=beam_out,
                                                             coord_x=x,
                                                             coord_y=z,
                                                             intensity=intensity_source_dimension,
                                                             distribution_type=Distribution.POSITION,
                                                             seed=0 if self.seed==0 else self.seed+1)

            self.progressBarSet(70)

            self.generate_user_defined_distribution_from_srw(beam_out=beam_out,
                                                             coord_x=x_first,
                                                             coord_y=z_first,
                                                             intensity=intensity_angular_distribution,
                                                             distribution_type=Distribution.DIVERGENCE,
                                                             seed=0 if self.seed==0 else self.seed+2)



            self.setStatusMessage("Plotting Results")

            self.progressBarSet(80)
            self.plot_results(beam_out)

            self.setStatusMessage("")

            self.send("Beam", beam_out)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       str(exception),
                QtWidgets.QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

        self.progressBarFinished()

    def sendNewBeam(self, trigger):
        if trigger and trigger.new_object == True:
            self.runShadowSource()

    def checkFields(self):
        self.number_of_rays = congruence.checkPositiveNumber(self.number_of_rays, "Number of rays")
        self.seed = congruence.checkPositiveNumber(self.seed, "Seed")

        if self.use_harmonic == 0:
            self.harmonic_number = congruence.checkStrictlyPositiveNumber(self.harmonic_number, "Harmonic Number")
        else:
            self.energy = congruence.checkPositiveNumber(self.energy, "Photon Energy")

        if self.optimize_source > 0:
            self.max_number_of_rejected_rays = congruence.checkPositiveNumber(self.max_number_of_rejected_rays,
                                                                             "Max number of rejected rays")
            congruence.checkFile(self.optimize_file_name)

    def populateFields(self, shadow_src):
        shadow_src.src.NPOINT = self.number_of_rays
        shadow_src.src.ISTAR1 = self.seed
        shadow_src.src.F_OPD = 1
        shadow_src.src.F_SR_TYPE = 0

        shadow_src.src.FGRID = 0
        shadow_src.src.IDO_VX = 0
        shadow_src.src.IDO_VZ = 0
        shadow_src.src.IDO_X_S = 0
        shadow_src.src.IDO_Y_S = 0
        shadow_src.src.IDO_Z_S = 0

        shadow_src.src.FSOUR = 0 # spatial_type (point)
        shadow_src.src.FDISTR = 1 # angular_distribution (flat)

        shadow_src.src.HDIV1 = -1.0e-6
        shadow_src.src.HDIV2 = 1.0e-6
        shadow_src.src.VDIV1 = -1.0e-6
        shadow_src.src.VDIV2 = 1.0e-6

        shadow_src.src.FSOURCE_DEPTH = 1 # OFF

        shadow_src.src.F_COLOR = 1 # single value
        shadow_src.src.F_PHOT = 0 # eV , 1 Angstrom

        shadow_src.src.PH1 = self.energy

        shadow_src.src.F_POLAR = self.polarization

        if self.polarization == 1:
            shadow_src.src.F_COHER = self.coherent_beam
            shadow_src.src.POL_ANGLE = self.phase_diff
            shadow_src.src.POL_DEG = self.polarization_degree

        shadow_src.src.F_OPD = 1
        shadow_src.src.F_BOUND_SOUR = self.optimize_source
        if self.optimize_source > 0:
            shadow_src.src.FILE_BOUND = bytes(congruence.checkFileName(self.optimize_file_name), 'utf-8')
        shadow_src.src.NTOTALPOINT = self.max_number_of_rejected_rays

    # WEIRD MEMORY INITIALIZATION BY FORTRAN. JUST A FIX.
    def fix_Intensity(self, beam_out):
        if self.polarization == 0:
            for index in range(0, len(beam_out._beam.rays)):
                beam_out._beam.rays[index, 15] = 0
                beam_out._beam.rays[index, 16] = 0
                beam_out._beam.rays[index, 17] = 0

    ####################################################################################
    # SRW CALCULATION
    ####################################################################################

    def checkSRWFields(self):

        congruence.checkPositiveNumber(self.Kh, "Horizontal K")
        congruence.checkPositiveNumber(self.Kv, "Vertical K")
        congruence.checkStrictlyPositiveNumber(self.undulator_period, "Period Length")
        congruence.checkStrictlyPositiveNumber(self.number_of_periods, "Number of Periods")

        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV, "Energy")
        congruence.checkPositiveNumber(self.electron_energy_spread, "Energy Spread")
        congruence.checkStrictlyPositiveNumber(self.ring_current, "Ring Current")

        congruence.checkPositiveNumber(self.electron_beam_size_h       , "Horizontal Beam Size")
        congruence.checkPositiveNumber(self.electron_beam_divergence_h , "Vertical Beam Size")
        congruence.checkPositiveNumber(self.electron_beam_size_v       , "Horizontal Beam Divergence")
        congruence.checkPositiveNumber(self.electron_beam_divergence_v , "Vertical Beam Divergence")


        congruence.checkStrictlyPositiveNumber(self.source_dimension_wf_h_slit_gap, "Wavefront Propagation H Slit Gap")
        congruence.checkStrictlyPositiveNumber(self.source_dimension_wf_v_slit_gap, "Wavefront Propagation V Slit Gap")
        congruence.checkStrictlyPositiveNumber(self.source_dimension_wf_h_slit_points, "Wavefront Propagation H Slit Points")
        congruence.checkStrictlyPositiveNumber(self.source_dimension_wf_v_slit_points, "Wavefront Propagation V Slit Points")
        congruence.checkGreaterOrEqualThan(self.source_dimension_wf_distance, self.get_minimum_propagation_distance(),
                                           "Wavefront Propagation Distance", "Minimum Distance out of the Source: " + str(self.get_minimum_propagation_distance()))

        congruence.checkStrictlyPositiveNumber(self.angular_distribution_wf_h_slit_gap, "Wavefront Propagation H Slit Gap")
        congruence.checkStrictlyPositiveNumber(self.angular_distribution_wf_v_slit_gap, "Wavefront Propagation V Slit Gap")
        congruence.checkStrictlyPositiveNumber(self.angular_distribution_wf_h_slit_points, "Wavefront Propagation H Slit Points")
        congruence.checkStrictlyPositiveNumber(self.angular_distribution_wf_v_slit_points, "Wavefront Propagation V Slit Points")
        congruence.checkGreaterOrEqualThan(self.angular_distribution_wf_distance, self.get_minimum_propagation_distance(),
                                           "Wavefront Propagation Distance", "Minimum Distance out of the Source: " + str(self.get_minimum_propagation_distance()))

        if self.save_srw_result == 1:
            congruence.checkDir(self.source_dimension_srw_file)
            congruence.checkDir(self.angular_distribution_srw_file)

    def get_minimum_propagation_distance(self):
        return round(self.get_source_length()*1.01, 6)

    def get_source_length(self):
        return self.undulator_period*self.number_of_periods

    def magnetic_field_from_K(self):
        Bv = self.Kv * 2 * pi * codata.m_e * codata.c / (codata.e * self.undulator_period)
        Bh = self.Kh * 2 * pi * codata.m_e * codata.c / (codata.e * self.undulator_period)

        return Bv, Bh

    def createUndulator(self):
        #***********Undulator
        By, Bx = self.magnetic_field_from_K() #Peak Vertical field [T]
        print("By calculated: " + str(By) + " T")
        Bx = 0.0 #Peak Vertical field [T]

        phBy = 0 #Initial Phase of the Vertical field component
        sBy = -1 #Symmetry of the Vertical field component vs Longitudinal position
        xcID = 0 #Transverse Coordinates of Undulator Center [m]
        ycID = 0
        zcID = 0 #Longitudinal Coordinate of Undulator Center [m]

        und = SRWLMagFldU([SRWLMagFldH(1, 'h', Bx, phBy, sBy, 1), SRWLMagFldH(1, 'v', By, phBy, sBy, 1)], self.undulator_period, self.number_of_periods) #Planar Undulator
        magFldCnt = SRWLMagFldC([und], array('d', [xcID]), array('d', [ycID]), array('d', [zcID])) #Container of all Field Elements

        return magFldCnt

    def createElectronBeam(self):
        #***********Electron Beam
        elecBeam = SRWLPartBeam()

        elecBeam.partStatMom1.x = 0. #Initial Transverse Coordinates (initial Longitudinal Coordinate will be defined later on) [m]
        elecBeam.partStatMom1.y = 0. #-0.00025
        # Roughly ! check!
        elecBeam.partStatMom1.z = -0.5*self.undulator_period*(self.number_of_periods + 8) #Initial Longitudinal Coordinate (set before the ID)
        elecBeam.partStatMom1.xp = 0. #Initial Relative Transverse Velocities
        elecBeam.partStatMom1.yp = 0.
        elecBeam.partStatMom1.gamma = self.gamma()

        elecBeam.Iavg = self.ring_current #Average Current [A]

        #2nd order statistical moments
        elecBeam.arStatMom2[0] = (self.electron_beam_size_h)**2 #<(x-x0)^2>
        elecBeam.arStatMom2[1] = 0
        elecBeam.arStatMom2[2] = (self.electron_beam_divergence_h)**2 #<(x'-x'0)^2>
        elecBeam.arStatMom2[3] = (self.electron_beam_size_v)**2 #<(y-y0)^2>
        elecBeam.arStatMom2[4] = 0
        elecBeam.arStatMom2[5] = (self.electron_beam_divergence_v)**2 #<(y'-y'0)^2>
        # energy spread
        elecBeam.arStatMom2[10] = (self.electron_energy_spread)**2 #<(E-E0)^2>/E0^2

        return elecBeam

    def createInitialWavefrontMeshSourceDimension(self, elecBeam):
        #****************** Initial Wavefront
        wfr = SRWLWfr() #For intensity distribution at fixed photon energy
        wfr.allocate(1, self.source_dimension_wf_h_slit_points, self.source_dimension_wf_v_slit_points) #Numbers of points vs Photon Energy, Horizontal and Vertical Positions
        wfr.mesh.zStart = self.source_dimension_wf_distance #Longitudinal Position [m] from Center of Straight Section at which SR has to be calculated
        wfr.mesh.eStart = self.energy if self.use_harmonic==1 else self.resonance_energy(harmonic=self.harmonic_number)  #Initial Photon Energy [eV]
        wfr.mesh.eFin = wfr.mesh.eStart #Final Photon Energy [eV]

        wfr.mesh.xStart = -0.5*self.source_dimension_wf_h_slit_gap #Initial Horizontal Position [m]
        wfr.mesh.xFin = -1 * wfr.mesh.xStart #0.00015 #Final Horizontal Position [m]
        wfr.mesh.yStart = -0.5*self.source_dimension_wf_v_slit_gap #Initial Vertical Position [m]
        wfr.mesh.yFin = -1 * wfr.mesh.yStart#0.00015 #Final Vertical Position [m]

        wfr.partBeam = elecBeam

        return wfr

    def createInitialWavefrontMeshAngularDistribution(self, elecBeam):
        #****************** Initial Wavefront
        wfr = SRWLWfr() #For intensity distribution at fixed photon energy
        wfr.allocate(1, self.angular_distribution_wf_h_slit_points, self.angular_distribution_wf_v_slit_points) #Numbers of points vs Photon Energy, Horizontal and Vertical Positions
        wfr.mesh.zStart = self.angular_distribution_wf_distance #Longitudinal Position [m] from Center of Straight Section at which SR has to be calculated
        wfr.mesh.eStart =  self.energy if self.use_harmonic==1 else self.resonance_energy(harmonic=self.harmonic_number) #Initial Photon Energy [eV]
        wfr.mesh.eFin = wfr.mesh.eStart #Final Photon Energy [eV]

        wfr.mesh.xStart = -0.5*self.angular_distribution_wf_h_slit_gap #Initial Horizontal Position [m]
        wfr.mesh.xFin = -1 * wfr.mesh.xStart #0.00015 #Final Horizontal Position [m]
        wfr.mesh.yStart = -0.5*self.angular_distribution_wf_v_slit_gap #Initial Vertical Position [m]
        wfr.mesh.yFin = -1 * wfr.mesh.yStart#0.00015 #Final Vertical Position [m]

        wfr.partBeam = elecBeam

        return wfr

    def createCalculationPrecisionSettings(self):
        #***********Precision Parameters for SR calculation
        meth = 1 #SR calculation method: 0- "manual", 1- "auto-undulator", 2- "auto-wiggler"
        relPrec = 0.01 #relative precision
        zStartInteg = 0 #longitudinal position to start integration (effective if < zEndInteg)
        zEndInteg = 0 #longitudinal position to finish integration (effective if > zStartInteg)
        npTraj = 100000 #Number of points for trajectory calculation
        useTermin = 1 #Use "terminating terms" (i.e. asymptotic expansions at zStartInteg and zEndInteg) or not (1 or 0 respectively)
        arPrecParSpec = [meth, relPrec, zStartInteg, zEndInteg, npTraj, useTermin, 0]

        return arPrecParSpec

    def createBeamlineSourceDimension(self, wfr):
        #***************** Optical Elements and Propagation Parameters

        opDrift = SRWLOptD(-wfr.mesh.zStart)
        ppDrift = [0, 0, 1., 1, 0, 0.5, 5.0, 0.5, 5.0, 0, 0, 0]

        return SRWLOptC([opDrift],[ppDrift])

    def transform_srw_array(self, arI, mesh):
        dim_x = mesh.nx
        dim_y = mesh.ny

        x_coordinates = numpy.linspace(mesh.xStart, mesh.xFin, dim_x)
        y_coordinates = numpy.linspace(mesh.yStart, mesh.yFin, dim_y)

        data = numpy.squeeze(arI)
        np_array = data.reshape((dim_y, dim_x))
        np_array = np_array.transpose()

        return x_coordinates, y_coordinates, np_array


    def runSRWCalculation(self):

        self.checkSRWFields()

        magFldCnt = self.createUndulator()
        elecBeam = self.createElectronBeam()
        wfrAngDist = self.createInitialWavefrontMeshAngularDistribution(elecBeam)
        wfrSouDim = self.createInitialWavefrontMeshSourceDimension(elecBeam)
        optBLSouDim = self.createBeamlineSourceDimension(wfrSouDim)

        arPrecParSpec = self.createCalculationPrecisionSettings()

        # This is the convergence parameter. Higher is more accurate but slower!!
        # 0.2 is used in the original example. But I think it should be higher. The calculation may then however need too much memory.
        sampFactNxNyForProp = 0.0 #0.6 #sampling factor for adjusting nx, ny (effective if > 0)

        # 1 calculate intensity distribution ME convoluted for dimension size

        print('   Performing Initial Single-E Electric Field calculation ... ', end='')
        arPrecParSpec[6] = sampFactNxNyForProp #sampling factor for adjusting nx, ny (effective if > 0)
        srwl.CalcElecFieldSR(wfrSouDim, 0, magFldCnt, arPrecParSpec)
        print('done')

        print('   Simulating Electric Field Wavefront Propagation for Source Dimension ... ', end='')
        srwl.PropagElecField(wfrSouDim, optBLSouDim)
        print('done')

        print('   Extracting Intensity from the Propagated Electric Field for Dim Nat ... ', end='')
        arI = array('f', [0]*wfrSouDim.mesh.nx*wfrSouDim.mesh.ny) #"flat" 2D array to take intensity data
        srwl.CalcIntFromElecField(arI, wfrSouDim, 6, 1, 3, wfrSouDim.mesh.eStart, 0, 0)

        if self.save_srw_result == 1: srwl_uti_save_intens_ascii(arI, wfrSouDim.mesh, self.source_dimension_srw_file)
        print('done')

        x, z, intensity_source_dimension = self.transform_srw_array(arI, wfrSouDim.mesh)

        # SWITCH FROM SRW METERS TO SHADOWOUI U.M.
        x = x/self.workspace_units_to_m
        z = z/self.workspace_units_to_m

        # 2 calculate intensity distribution ME convoluted at far field to express it in angular coordinates

        print('   Performing Initial Single-E Electric Field calculation ... ', end='')
        arPrecParSpec[6] = sampFactNxNyForProp #sampling factor for adjusting nx, ny (effective if > 0)
        srwl.CalcElecFieldSR(wfrAngDist, 0, magFldCnt, arPrecParSpec)
        print('done')

        print('   Extracting Intensity ME Conv from the Calculated Initial Electric Field ... ', end='')
        arI = array('f', [0]*wfrAngDist.mesh.nx*wfrAngDist.mesh.ny) #"flat" array to take 2D intensity data
        srwl.CalcIntFromElecField(arI, wfrAngDist, 6, 1, 3, wfrAngDist.mesh.eStart, 0, 0)
        print('done')
        print('   Saving the Initial Wavefront Intensity into a file ... ', end='')

        distance = wfrAngDist.mesh.zStart + 0.5*(self.number_of_periods*self.undulator_period)

        wfrAngDist.mesh.xStart /= distance
        wfrAngDist.mesh.xFin /= distance
        wfrAngDist.mesh.yStart /= distance
        wfrAngDist.mesh.yFin /= distance

        if self.save_srw_result == 1: srwl_uti_save_intens_ascii(arI, wfrAngDist.mesh, self.angular_distribution_srw_file)
        print('done')

        x_first, z_first, intensity_angular_distribution = self.transform_srw_array(arI, wfrAngDist.mesh)

        return x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution

    def generate_user_defined_distribution_from_srw(self,
                                                    beam_out,
                                                    coord_x,
                                                    coord_y,
                                                    intensity,
                                                    distribution_type=Distribution.POSITION,
                                                    seed=0):


        pdf = numpy.abs(intensity/numpy.max(intensity))
        pdf /= pdf.sum()

        distribution = CustomDistribution(pdf, seed=seed)

        sampled = distribution(len(beam_out._beam.rays))

        min_value_x = numpy.min(coord_x)
        step_x = numpy.abs(coord_x[1]-coord_x[0])
        min_value_y = numpy.min(coord_y)
        step_y = numpy.abs(coord_y[1]-coord_y[0])

        if distribution_type == Distribution.POSITION:
            beam_out._beam.rays[:, 0] = min_value_x + sampled[0, :]*step_x
            beam_out._beam.rays[:, 2] = min_value_y + sampled[1, :]*step_y

        elif distribution_type == Distribution.DIVERGENCE:
            alpha_x = min_value_x + sampled[0, :]*step_x
            alpha_z = min_value_y + sampled[1, :]*step_y

            beam_out._beam.rays[:, 3] =  numpy.cos(alpha_z)*numpy.sin(alpha_x)
            beam_out._beam.rays[:, 4] =  numpy.cos(alpha_z)*numpy.cos(alpha_x)
            beam_out._beam.rays[:, 5] =  numpy.sin(alpha_z)

    def gamma(self):
        return 1e9*self.electron_energy_in_GeV / (codata.m_e *  codata.c**2 / codata.e)

    def resonance_energy(self, theta_x=0.0, theta_z=0.0, harmonic=1):
        gamma = self.gamma()

        wavelength = (self.undulator_period / (2.0*gamma **2)) * \
                     (1 + self.Kv**2 / 2.0 + self.Kh**2 / 2.0 + \
                      gamma**2 * (theta_x**2 + theta_z ** 2))

        wavelength /= harmonic

        return m2ev/wavelength

    ####################################################################################
    # SRW FILES
    ####################################################################################

    def checkSRWFilesFields(self):
        congruence.checkFile(self.source_dimension_srw_file)
        congruence.checkFile(self.angular_distribution_srw_file)

    def loadSRWFiles(self):

        self.checkSRWFilesFields()

        x, z, intensity_source_dimension = self.loadNumpyFormat(self.source_dimension_srw_file)
        x_first, z_first, intensity_angular_distribution = self.loadNumpyFormat(self.angular_distribution_srw_file)


        # SWITCH FROM SRW METERS TO SHADOWOUI U.M.
        x = x/self.workspace_units_to_m
        z = z/self.workspace_units_to_m

        return x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution


    def file_load(self, _fname, _read_labels=1):
        nLinesHead = 11
        hlp = []

        with open(_fname,'r') as f:
            for i in range(nLinesHead):
                hlp.append(f.readline())

        ne, nx, ny = [int(hlp[i].replace('#','').split()[0]) for i in [3,6,9]]
        ns = 1
        testStr = hlp[nLinesHead - 1]
        if testStr[0] == '#':
            ns = int(testStr.replace('#','').split()[0])

        e0,e1,x0,x1,y0,y1 = [float(hlp[i].replace('#','').split()[0]) for i in [1,2,4,5,7,8]]

        data = numpy.squeeze(numpy.loadtxt(_fname, dtype=numpy.float64)) #get data from file (C-aligned flat)

        allrange = e0, e1, ne, x0, x1, nx, y0, y1, ny

        arLabels = ['Photon Energy', 'Horizontal Position', 'Vertical Position', 'Intensity']
        arUnits = ['eV', 'm', 'm', 'ph/s/.1%bw/mm^2']

        if _read_labels:

            arTokens = hlp[0].split(' [')
            arLabels[3] = arTokens[0].replace('#','')
            arUnits[3] = '';
            if len(arTokens) > 1:
                arUnits[3] = arTokens[1].split('] ')[0]

            for i in range(3):
                arTokens = hlp[i*3 + 1].split()
                nTokens = len(arTokens)
                nTokensLabel = nTokens - 3
                nTokensLabel_mi_1 = nTokensLabel - 1
                strLabel = ''
                for j in range(nTokensLabel):
                    strLabel += arTokens[j + 2]
                    if j < nTokensLabel_mi_1: strLabel += ' '
                arLabels[i] = strLabel
                arUnits[i] = arTokens[nTokens - 1].replace('[','').replace(']','')

        return data, None, allrange, arLabels, arUnits

    def loadNumpyFormat(self, filename):
        data, dump, allrange, arLabels, arUnits = self.file_load(filename)

        dim_x = allrange[5]
        dim_y = allrange[8]
        np_array = data.reshape((dim_y, dim_x))
        np_array = np_array.transpose()
        x_coordinates = numpy.linspace(allrange[3], allrange[4], dim_x)
        y_coordinates = numpy.linspace(allrange[6], allrange[7], dim_y)

        return x_coordinates, y_coordinates, np_array

    ####################################################################################
    # ASCII FILES
    ####################################################################################

    def checkASCIIFilesFields(self):
        congruence.checkFile(self.x_positions_file)
        congruence.checkFile(self.z_positions_file)
        congruence.checkFile(self.x_divergences_file)
        congruence.checkFile(self.z_divergences_file)

        self.x_positions_factor = float(self.x_positions_factor)
        self.z_positions_factor = float(self.z_positions_factor)
        self.x_divergences_factor = float(self.x_divergences_factor)
        self.z_divergences_factor = float(self.z_divergences_factor)

        congruence.checkStrictlyPositiveNumber(self.x_positions_factor, "X Position Units to Workspace Units")
        congruence.checkStrictlyPositiveNumber(self.z_positions_factor, "Z Position Units to Workspace Units")
        congruence.checkStrictlyPositiveNumber(self.x_divergences_factor, "X Divergence Units to rad")
        congruence.checkStrictlyPositiveNumber(self.z_divergences_factor, "Z Divergence Units to rad")

    def loadASCIIFiles(self):
        self.checkASCIIFilesFields()

        x_positions = self.extract_distribution_from_file(distribution_file_name=self.x_positions_file)
        z_positions = self.extract_distribution_from_file(distribution_file_name=self.z_positions_file)

        x_positions[:, 0] *= self.x_positions_factor
        z_positions[:, 0] *= self.z_positions_factor

        x_divergences = self.extract_distribution_from_file(distribution_file_name=self.x_divergences_file)
        z_divergences = self.extract_distribution_from_file(distribution_file_name=self.z_divergences_file)

        x_divergences[:, 0] *= self.x_divergences_factor
        z_divergences[:, 0] *= self.z_divergences_factor

        x, z, intensity_source_dimension = self.combine_distributions(x_positions, z_positions)
        x_first, z_first, intensity_angular_distribution = self.combine_distributions(x_divergences, z_divergences)

        return x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution


    def extract_distribution_from_file(self, distribution_file_name):
        distribution = []

        try:
            distribution_file = open(distribution_file_name, "r")

            rows = distribution_file.readlines()

            for index in range(0, len(rows)):
                row = rows[index]

                if not row.strip() == "":
                    values = row.split()

                    if not len(values) == 2: raise Exception("Malformed file, must be: <value> <spaces> <frequency>")

                    value = float(values[0].strip())
                    frequency = float(values[1].strip())

                    distribution.append([value, frequency])

        except Exception as err:
            raise Exception("Problems reading distribution file: {0}".format(err))
        except:
            raise Exception("Unexpected error reading distribution file: ", sys.exc_info()[0])

        return numpy.array(distribution)



    def combine_distributions(self, distribution_x, distribution_y):

        coord_x = distribution_x[:, 0]
        coord_y = distribution_y[:, 0]

        intensity_x = repmat(distribution_x[:, 1], len(coord_y), 1).transpose()
        intensity_y = repmat(distribution_y[:, 1], len(coord_x), 1)

        if self.combine_strategy == 0:
            convoluted_intensity = numpy.sqrt(intensity_x*intensity_y)
        elif self.combine_strategy == 1:
            convoluted_intensity = numpy.sqrt(intensity_x**2 + intensity_y**2)
        elif self.combine_strategy == 2:
            convoluted_intensity = convolve2d(intensity_x, intensity_y, boundary='fill', mode='same', fillvalue=0)
        elif self.combine_strategy == 3:
            convoluted_intensity = 0.5*(intensity_x + intensity_y)

        return coord_x, coord_y, convoluted_intensity


class CustomDistribution(object):
    """
    draws samples from a one dimensional probability distribution,
    by means of inversion of a discrete inverstion of a cumulative density function

    the pdf can be sorted first to prevent numerical error in the cumulative sum
    this is set as default; for big density functions with high contrast,
    it is absolutely necessary, and for small density functions,
    the overhead is minimal

    a call to this distibution object returns indices into density array
    """
    def __init__(self, pdf, sort = True, interpolation = True, transform = lambda x: x, seed=0):
        self.shape          = pdf.shape
        self.pdf            = pdf.ravel()
        self.sort           = sort
        self.interpolation  = interpolation
        self.transform      = transform
        self.seed = seed

        #a pdf can not be negative
        assert(numpy.all(pdf>=0))

        #sort the pdf by magnitude
        if self.sort:
            self.sortindex = numpy.argsort(self.pdf, axis=None)
            self.pdf = self.pdf[self.sortindex]
        #construct the cumulative distribution function
        self.cdf = numpy.cumsum(self.pdf)
    @property
    def ndim(self):
        return len(self.shape)
    @property
    def sum(self):
        """cached sum of all pdf values; the pdf need not sum to one, and is imlpicitly normalized"""
        return self.cdf[-1]
    def __call__(self, N):
        if self.seed > 0: numpy.random.seed(self.seed)

        """draw """
        #pick numbers which are uniformly random over the cumulative distribution function
        choice = numpy.random.uniform(high = self.sum, size = N)
        #find the indices corresponding to this point on the CDF
        index = numpy.searchsorted(self.cdf, choice)
        #if necessary, map the indices back to their original ordering
        if self.sort:
            index = self.sortindex[index]
        #map back to multi-dimensional indexing
        index = numpy.unravel_index(index, self.shape)
        index = numpy.vstack(index)
        #is this a discrete or piecewise continuous distribution?
        if self.interpolation:
            index = index + numpy.random.uniform(size=index.shape)
        return self.transform(index)


if __name__ == "__main__":

    x = numpy.linspace(-100, 100, 512)
    p = numpy.exp(-x**2)
    pdf = p[:,None]*p[None,:]     #2d gaussian
    dist = CustomDistribution(pdf, transform=lambda i:i-256)

    import matplotlib.pyplot as pp
    pp.scatter(*dist(100000))
    pp.show()

    '''
    a = QApplication(sys.argv)
    ow = APSUndulator()
    ow.show()
    a.exec_()
    ow.saveSettings()
    '''
