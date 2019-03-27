#!/usr/bin/env python
# -*- coding: utf-8 -*-
# #########################################################################
# Copyright (c) 2018, UChicago Argonne, LLC. All rights reserved.         #
#                                                                         #
# Copyright 2018. UChicago Argonne, LLC. This software was produced       #
# under U.S. Government contract DE-AC02-06CH11357 for Argonne National   #
# Laboratory (ANL), which is operated by UChicago Argonne, LLC for the    #
# U.S. Department of Energy. The U.S. Government has rights to use,       #
# reproduce, and distribute this software.  NEITHER THE GOVERNMENT NOR    #
# UChicago Argonne, LLC MAKES ANY WARRANTY, EXPRESS OR IMPLIED, OR        #
# ASSUMES ANY LIABILITY FOR THE USE OF THIS SOFTWARE.  If software is     #
# modified to produce derivative works, such modified software should     #
# be clearly marked, so as not to confuse it with the version available   #
# from ANL.                                                               #
#                                                                         #
# Additionally, redistribution and use in source and binary forms, with   #
# or without modification, are permitted provided that the following      #
# conditions are met:                                                     #
#                                                                         #
#     * Redistributions of source code must retain the above copyright    #
#       notice, this list of conditions and the following disclaimer.     #
#                                                                         #
#     * Redistributions in binary form must reproduce the above copyright #
#       notice, this list of conditions and the following disclaimer in   #
#       the documentation and/or other materials provided with the        #
#       distribution.                                                     #
#                                                                         #
#     * Neither the name of UChicago Argonne, LLC, Argonne National       #
#       Laboratory, ANL, the U.S. Government, nor the names of its        #
#       contributors may be used to endorse or promote products derived   #
#       from this software without specific prior written permission.     #
#                                                                         #
# THIS SOFTWARE IS PROVIDED BY UChicago Argonne, LLC AND CONTRIBUTORS     #
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT       #
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS       #
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL UChicago     #
# Argonne, LLC OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,        #
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,    #
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;        #
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER        #
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT      #
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN       #
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE         #
# POSSIBILITY OF SUCH DAMAGE.                                             #
# #########################################################################

import numpy
from numpy.matlib import repmat
from scipy.signal import convolve2d

from PyQt5 import QtWidgets
from PyQt5.QtGui import QPalette, QColor, QFont
from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from orangewidget import widget
from oasys.util.oasys_util import TriggerOut, EmittingStream

from syned.beamline.beamline import Beamline
from syned.beamline.optical_elements.absorbers.slit import Slit
from syned.storage_ring.light_source import ElectronBeam, LightSource
from syned.widget.widget_decorator import WidgetDecorator
from syned.beamline.shape import Rectangle

from orangecontrib.shadow.util.shadow_objects import ShadowBeam, ShadowSource
from orangecontrib.shadow.widgets.gui.ow_generic_element import GenericElement

from orangecontrib.aps.util.random_distributions import Distribution2D, Grid2D, distribution_from_grid
from orangecontrib.aps.util.custom_distribution import CustomDistribution

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

    inputs = WidgetDecorator.syned_input_data()
    inputs.append(("SynedData#2", Beamline, "receive_syned_data"))
    inputs.append(("Trigger", TriggerOut, "sendNewBeam"))

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

    type_of_initialization = Setting(0)

    moment_x = Setting(0.0)
    moment_y = Setting(0.0)
    moment_z = Setting(0.0)
    moment_xp = Setting(0.0)
    moment_yp = Setting(0.0)

    source_dimension_wf_h_slit_gap = Setting(0.0015)
    source_dimension_wf_v_slit_gap = Setting(0.0015)
    source_dimension_wf_h_slit_points=Setting(301)
    source_dimension_wf_v_slit_points=Setting(301)
    source_dimension_wf_distance = Setting(28.0)

    horizontal_range_modification_factor_at_resizing       = Setting(0.5)
    horizontal_resolution_modification_factor_at_resizing  = Setting(5.0)
    vertical_range_modification_factor_at_resizing         = Setting(0.5)
    vertical_resolution_modification_factor_at_resizing    = Setting(5.0)

    kind_of_sampler = Setting(1)
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
    harmonic_energy = 0.0
    energy=Setting(10000.0)

    polarization = Setting(1)
    coherent_beam = Setting(0)
    phase_diff = Setting(0.0)
    polarization_degree = Setting(1.0)

    optimize_source=Setting(0)
    optimize_file_name = Setting("NONESPECIFIED")
    max_number_of_rejected_rays = Setting(10000000)

    file_to_write_out = Setting(0)

    auto_energy = Setting(0.0)
    auto_harmonic_number = Setting(1)

    energy_step = None
    power_step = None
    compute_power = False
    test_mode = False

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
        tab_util = oasysgui.createTabPage(tabs_setting, "Utility")

        gui.comboBox(tab_spdiv, self, "distribution_source", label="Distribution Source", labelWidth=310,
                     items=["SRW Calculation", "SRW Files", "ASCII Files"], orientation="horizontal", callback=self.set_DistributionSource)

        self.srw_box = oasysgui.widgetBox(tab_spdiv, "", addSpace=False, orientation="vertical", height=550)
        self.srw_files_box = oasysgui.widgetBox(tab_spdiv, "", addSpace=False, orientation="vertical", height=550)
        self.ascii_box = oasysgui.widgetBox(tab_spdiv, "", addSpace=False, orientation="vertical", height=550)

        self.set_DistributionSource()

        ####################################################################################
        # SHADOW

        left_box_1 = oasysgui.widgetBox(tab_shadow, "Monte Carlo and Energy Spectrum", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "number_of_rays", "Number of Rays", tooltip="Number of Rays", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "seed", "Seed", tooltip="Seed (0=clock)", labelWidth=250, valueType=int, orientation="horizontal")

        gui.comboBox(left_box_1, self, "use_harmonic", label="Photon Energy Setting",
                     items=["Harmonic", "Other"], labelWidth=260,
                     callback=self.set_WFUseHarmonic, sendSelectedValue=False, orientation="horizontal")

        self.use_harmonic_box_1 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=50)
        oasysgui.lineEdit(self.use_harmonic_box_1, self, "harmonic_number", "Harmonic #", labelWidth=260, valueType=int, orientation="horizontal", callback=self.set_harmonic_energy)
        le_he = oasysgui.lineEdit(self.use_harmonic_box_1, self, "harmonic_energy", "Harmonic Energy", labelWidth=260, valueType=float, orientation="horizontal")
        le_he.setReadOnly(True)
        font = QFont(le_he.font())
        font.setBold(True)
        le_he.setFont(font)
        palette = QPalette(le_he.palette())
        palette.setColor(QPalette.Text, QColor('dark blue'))
        palette.setColor(QPalette.Base, QColor(243, 240, 160))
        le_he.setPalette(palette)

        self.use_harmonic_box_2 = oasysgui.widgetBox(left_box_1, "", addSpace=False, orientation="vertical", height=50)
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

        gui.comboBox(self.srw_box, self, "kind_of_sampler", label="Random Generator", labelWidth=250,
                     items=["Simple (Fast)", "Accurate (Slow)"], orientation="horizontal")

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
        oasysgui.lineEdit(left_box_1, self, "undulator_period", "Undulator Period [m]", labelWidth=260,  valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(left_box_1, self, "Kv", "K Vertical", labelWidth=260,  valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(left_box_1, self, "Kh", "K Horizontal", labelWidth=260,  valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)

        tab_und = oasysgui.tabWidget(tab_ls)

        tab_mach = oasysgui.createTabPage(tab_und, "Machine Parameters")
        tab_traj = oasysgui.createTabPage(tab_und, "Trajectory")

        oasysgui.lineEdit(tab_mach, self, "electron_energy_in_GeV", "Energy [GeV]", labelWidth=260, valueType=float, orientation="horizontal", callback=self.set_harmonic_energy)
        oasysgui.lineEdit(tab_mach, self, "electron_energy_spread", "Energy Spread", labelWidth=260, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "ring_current", "Ring Current [A]", labelWidth=260, valueType=float, orientation="horizontal")
        
        gui.separator(tab_mach)

        oasysgui.lineEdit(tab_mach, self, "electron_beam_size_h",       "Horizontal Beam Size [m]", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "electron_beam_size_v",       "Vertical Beam Size [m]",  labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "electron_beam_divergence_h", "Horizontal Beam Divergence [rad]", labelWidth=230, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(tab_mach, self, "electron_beam_divergence_v", "Vertical Beam Divergence [rad]", labelWidth=230, valueType=float, orientation="horizontal")


        gui.comboBox(tab_traj, self, "type_of_initialization", label="Trajectory Initialization", labelWidth=140,
                     items=["At Zero Point", "At Fixed Position", "Sampled from Phase Space"],
                     callback=self.set_TypeOfInitialization,
                     sendSelectedValue=False, orientation="horizontal")

        self.left_box_3_1 = oasysgui.widgetBox(tab_traj, "", addSpace=False, orientation="vertical", height=160)
        self.left_box_3_2 = oasysgui.widgetBox(tab_traj, "", addSpace=False, orientation="vertical", height=160)

        oasysgui.lineEdit(self.left_box_3_1, self, "moment_x", "x\u2080 [m]", labelWidth=200, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_3_1, self, "moment_y", "y\u2080 [m]", labelWidth=200, valueType=float, orientation="horizontal")

        box = oasysgui.widgetBox(self.left_box_3_1, "", addSpace=False, orientation="horizontal")

        oasysgui.lineEdit(box, self, "moment_z", "z\u2080 [m]", labelWidth=160, valueType=float, orientation="horizontal")
        gui.button(box, self, "Auto", width=35, callback=self.set_z0Default)

        oasysgui.lineEdit(self.left_box_3_1, self, "moment_xp", "x'\u2080 [rad]", labelWidth=200, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.left_box_3_1, self, "moment_yp", "y'\u2080 [rad]", labelWidth=200, valueType=float, orientation="horizontal")

        self.set_TypeOfInitialization()

        left_box_3 = oasysgui.widgetBox(tab_wf, "Wavefront Propagation Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_h_slit_gap", "H Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_v_slit_gap", "V Slit Gap [m]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_h_slit_points", "H Slit Points", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_v_slit_points", "V Slit Points", labelWidth=250, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(left_box_3, self, "source_dimension_wf_distance", "Propagation Distance [m]", labelWidth=250, valueType=float, orientation="horizontal")

        left_box_4 = oasysgui.widgetBox(tab_wf, "Drift Back Propagation Parameters", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_4, self, "horizontal_range_modification_factor_at_resizing", "H range modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_4, self, "horizontal_resolution_modification_factor_at_resizing", "H resolution modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_4, self, "vertical_range_modification_factor_at_resizing", "V range modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_4, self, "vertical_resolution_modification_factor_at_resizing", "V resolution modification factor at resizing", labelWidth=290, valueType=float, orientation="horizontal")

        ####################################################################################
        # SRW FILES

        gui.separator(self.srw_files_box)

        file_box = oasysgui.widgetBox(self.srw_files_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_source_dimension_srw_file = oasysgui.lineEdit(file_box, self, "source_dimension_srw_file", "Source Dimension File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectSourceDimensionFile)

        file_box = oasysgui.widgetBox(self.srw_files_box, "", addSpace=True, orientation="horizontal", height=45)

        self.le_angular_distribution_srw_file = oasysgui.lineEdit(file_box, self, "angular_distribution_srw_file", "Angular Distribution File", labelWidth=180,  valueType=str, orientation="vertical")

        gui.button(file_box, self, "...", height=45, callback=self.selectAngularDistributionFile)


        ####################################################################################
        # ASCII FILES

        gui.separator(self.ascii_box)

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

        ####################################################################################
        # Utility

        left_box_1 = oasysgui.widgetBox(tab_util, "Auto Setting of Undulator", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(left_box_1, self, "auto_energy", "Set Undulator at Energy [eV]", labelWidth=250, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(left_box_1, self, "auto_harmonic_number", "As Harmonic #",  labelWidth=250, valueType=int, orientation="horizontal")

        gui.button(left_box_1, self, "Set Kv value", callback=self.auto_set_undulator)

        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)



    ####################################################################################
    # GRAPHICS
    ####################################################################################

    def after_change_workspace_units(self):
        pass

    def set_TypeOfInitialization(self):
        self.left_box_3_1.setVisible(self.type_of_initialization==1)
        self.left_box_3_2.setVisible(self.type_of_initialization!=1)

    def set_z0Default(self):
        self.moment_z = self.get_default_initial_z()

    def get_default_initial_z(self):
        return -0.5*self.undulator_period*(self.number_of_periods + 4) # initial Longitudinal Coordinate (set before the ID)


    def auto_set_undulator(self):
        if not self.distribution_source == 0: raise Exception("This calculation can be performed only for explicit SRW Calculation")
        congruence.checkStrictlyPositiveNumber(self.auto_energy, "Set Undulator at Energy")
        congruence.checkStrictlyPositiveNumber(self.auto_harmonic_number, "As Harmonic #")
        congruence.checkStrictlyPositiveNumber(self.electron_energy_in_GeV, "Energy")
        congruence.checkStrictlyPositiveNumber(self.undulator_period, "Period Length")

        wavelength = self.auto_harmonic_number*m2ev/self.auto_energy

        self.Kv = round(numpy.sqrt(2*(((wavelength*2*self.gamma()**2)/self.undulator_period)-1)), 6)
        self.Kh = 0

        self.set_WFUseHarmonic()

    def set_harmonic_energy(self):
        if self.distribution_source==0 and self.use_harmonic==0:
            self.harmonic_energy = round(self.resonance_energy(harmonic=self.harmonic_number), 2)
        else:
            self.harmonic_energy = numpy.nan

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

        self.set_harmonic_energy()

    def set_DistributionSource(self):
        self.srw_box.setVisible(self.distribution_source == 0)
        self.srw_files_box.setVisible(self.distribution_source == 1)
        self.ascii_box.setVisible(self.distribution_source == 2)

        self.set_harmonic_energy()

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
    # SYNED
    ####################################################################################

    def receive_syned_data(self, data):
        if not data is None:
            try:
                if data.get_beamline_elements_number() > 0:
                    slit_element = data.get_beamline_element_at(0)
                    slit = slit_element.get_optical_element()
                    coordinates = slit_element.get_coordinates()

                    if isinstance(slit, Slit) and isinstance(slit.get_boundary_shape(), Rectangle):
                        rectangle = slit.get_boundary_shape()

                        self.source_dimension_wf_h_slit_gap = rectangle._x_right - rectangle._x_left
                        self.source_dimension_wf_v_slit_gap = rectangle._y_top - rectangle._y_bottom
                        self.source_dimension_wf_distance = coordinates.p()
                elif not data._light_source is None and isinstance(data._light_source, LightSource):
                    light_source = data._light_source

                    self.electron_energy_in_GeV = light_source._electron_beam._energy_in_GeV
                    self.electron_energy_spread = light_source._electron_beam._energy_spread
                    self.ring_current = light_source._electron_beam._current

                    x, xp, y, yp = light_source._electron_beam.get_sigmas_all()

                    self.electron_beam_size_h = round(x, 9)
                    self.electron_beam_size_v = round(y, 9)
                    self.electron_beam_divergence_h = round(xp, 10)
                    self.electron_beam_divergence_v = round(yp, 10)

                    self.Kh = light_source._magnetic_structure._K_horizontal
                    self.Kv = light_source._magnetic_structure._K_vertical
                    self.undulator_period = light_source._magnetic_structure._period_length
                    self.number_of_periods = light_source._magnetic_structure._number_of_periods
                else:
                    raise ValueError("Syned data not correct")
            except Exception as exception:
                QtWidgets.QMessageBox.critical(self, "Error", str(exception), QtWidgets.QMessageBox.Ok)

    def receive_specific_syned_data(self, data):
        raise NotImplementedError()

    ####################################################################################
    # PROCEDURES
    ####################################################################################

    def runShadowSource(self):
        self.setStatusMessage("")
        self.progressBarInit()

        sys.stdout = EmittingStream(textWritten=self.writeStdOut)

        try:
            if self.test_mode:
                beam_out = ShadowBeam()
                beam_out._beam.rays = numpy.zeros((1000, 18))
                total_power = 100.0
            else:
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

                    x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution, total_power = self.runSRWCalculation()
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
                                                                 coord_z=z,
                                                                 intensity=intensity_source_dimension,
                                                                 distribution_type=Distribution.POSITION,
                                                                 kind_of_sampler=self.kind_of_sampler,
                                                                 seed=0 if self.seed==0 else self.seed+1)

                self.progressBarSet(70)

                self.generate_user_defined_distribution_from_srw(beam_out=beam_out,
                                                                 coord_x=x_first,
                                                                 coord_z=z_first,
                                                                 intensity=intensity_angular_distribution,
                                                                 distribution_type=Distribution.DIVERGENCE,
                                                                 kind_of_sampler=self.kind_of_sampler,
                                                                 seed=0 if self.seed==0 else self.seed+2)

                self.setStatusMessage("Plotting Results")

                self.progressBarSet(80)
                self.plot_results(beam_out)

            self.setStatusMessage("")

            if self.compute_power and self.energy_step and total_power:
                additional_parameters = {}

                additional_parameters["total_power"]        = total_power
                additional_parameters["photon_energy_step"] = self.energy_step

                if self.test_mode:
                    additional_parameters["test_mode"] = True

                print("Total Power", total_power)

                beam_out.setScanningData(ShadowBeam.ScanningData("photon_energy", self.energy, "Energy for Power Calculation", "eV", additional_parameters))

            self.send("Beam", beam_out)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(self, "Error", str(exception), QtWidgets.QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

        self.progressBarFinished()

    def sendNewBeam(self, trigger):
        self.compute_power = False
        self.energy_step = None
        self.test_mode = False

        if trigger and trigger.new_object == True:
            if trigger.has_additional_parameter("seed_increment"):
                self.seed += trigger.get_additional_parameter("seed_increment")

            if trigger.has_additional_parameter("energy_value") and trigger.has_additional_parameter("energy_step"):
                self.compute_power = True
                self.use_harmonic = 1
                self.distribution_source = 0
                self.save_srw_result = 0

                self.energy = trigger.get_additional_parameter("energy_value")
                self.energy_step = trigger.get_additional_parameter("energy_step")
                self.power_step = trigger.get_additional_parameter("power_step")

                self.test_mode = trigger.has_additional_parameter("test_mode") and trigger.get_additional_parameter("test_mode") == True

                self.set_WFUseHarmonic()
                self.set_DistributionSource()
                self.set_SaveFileSRW()

            self.runShadowSource()

    def checkFields(self):
        self.number_of_rays = congruence.checkPositiveNumber(self.number_of_rays, "Number of rays")
        self.seed = congruence.checkPositiveNumber(self.seed, "Seed")

        if self.use_harmonic == 0:
            if self.distribution_source != 0: raise Exception("Harmonic Energy can be computed only for explicit SRW Calculation")

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

        shadow_src.src.PH1 = self.energy if self.use_harmonic==1 else self.resonance_energy(harmonic=self.harmonic_number)

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

        if self.type_of_initialization == 0: # zero
            self.moment_x = 0.0
            self.moment_y = 0.0
            self.moment_z = self.get_default_initial_z()
            self.moment_xp = 0.0
            self.moment_yp = 0.0
        elif self.type_of_initialization == 2: # sampled
            self.moment_x = numpy.random.normal(0.0, self.electron_beam_size_h)
            self.moment_y = numpy.random.normal(0.0, self.electron_beam_size_v)
            self.moment_z = self.get_default_initial_z()
            self.moment_xp = numpy.random.normal(0.0, self.electron_beam_divergence_h)
            self.moment_yp = numpy.random.normal(0.0, self.electron_beam_divergence_v)

        elecBeam.partStatMom1.x = self.moment_x
        elecBeam.partStatMom1.y = self.moment_y
        elecBeam.partStatMom1.z = self.moment_z
        elecBeam.partStatMom1.xp = self.moment_xp
        elecBeam.partStatMom1.yp = self.moment_yp
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

    def createInitialWavefrontMesh(self, elecBeam):
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
        ppDrift = [0, 0, 1., 1, 0,
                   self.horizontal_range_modification_factor_at_resizing,
                   self.horizontal_resolution_modification_factor_at_resizing,
                   self.vertical_range_modification_factor_at_resizing,
                   self.vertical_resolution_modification_factor_at_resizing,
                   0, 0, 0]

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
        wfr = self.createInitialWavefrontMesh(elecBeam)
        optBLSouDim = self.createBeamlineSourceDimension(wfr)

        arPrecParSpec = self.createCalculationPrecisionSettings()

        # This is the convergence parameter. Higher is more accurate but slower!!
        # 0.2 is used in the original example. But I think it should be higher. The calculation may then however need too much memory.
        sampFactNxNyForProp = 0.0 #0.6 #sampling factor for adjusting nx, ny (effective if > 0)

        # 1 calculate intensity distribution ME convoluted for dimension size

        arPrecParSpec[6] = sampFactNxNyForProp #sampling factor for adjusting nx, ny (effective if > 0)
        srwl.CalcElecFieldSR(wfr, 0, magFldCnt, arPrecParSpec)

        arI = array('f', [0]*wfr.mesh.nx*wfr.mesh.ny) #"flat" 2D array to take intensity data
        srwl.CalcIntFromElecField(arI, wfr, 6, 1, 3, wfr.mesh.eStart, 0, 0)

        # from radiation at the slit we can calculate Angular Distribution and Power

        x, z, intensity_angular_distribution = self.transform_srw_array(arI, wfr.mesh)

        if self.compute_power:
            if self.power_step > 0:
                total_power = self.power_step
            else:
                dx = (x[1] - x[0])*1e3 # mm for power computations
                dy = (z[1] - z[0])*1e3

                total_power = intensity_angular_distribution.sum() * dx * dy * (1e3 * self.energy_step * codata.e)
        else:
            total_power = None

        distance = wfr.mesh.zStart

        x_first = numpy.arctan(x/distance)
        z_first = numpy.arctan(z/distance)

        wfrAngDist = self.createInitialWavefrontMesh(elecBeam)
        wfrAngDist.mesh.xStart = numpy.arctan(wfr.mesh.xStart/distance)
        wfrAngDist.mesh.xFin   = numpy.arctan(wfr.mesh.xFin  /distance)
        wfrAngDist.mesh.yStart = numpy.arctan(wfr.mesh.yStart/distance)
        wfrAngDist.mesh.yFin   = numpy.arctan(wfr.mesh.yFin  /distance)

        if self.save_srw_result == 1: srwl_uti_save_intens_ascii(arI, wfrAngDist.mesh, self.angular_distribution_srw_file)

        # for source dimension, back propagation to the source central position

        srwl.PropagElecField(wfr, optBLSouDim)

        arI = array('f', [0]*wfr.mesh.nx*wfr.mesh.ny) #"flat" 2D array to take intensity data
        srwl.CalcIntFromElecField(arI, wfr, 6, 1, 3, wfr.mesh.eStart, 0, 0)

        if self.save_srw_result == 1: srwl_uti_save_intens_ascii(arI, wfr.mesh, self.source_dimension_srw_file)

        x, z, intensity_source_dimension = self.transform_srw_array(arI, wfr.mesh)

        # SWITCH FROM SRW METERS TO SHADOWOUI U.M.
        x /= self.workspace_units_to_m
        z /= self.workspace_units_to_m

        return x, z, intensity_source_dimension, x_first, z_first, intensity_angular_distribution, total_power


    def generate_user_defined_distribution_from_srw(self,
                                                    beam_out,
                                                    coord_x,
                                                    coord_z,
                                                    intensity,
                                                    distribution_type=Distribution.POSITION,
                                                    kind_of_sampler=0,
                                                    seed=0):
        if kind_of_sampler == 0:
            pdf = numpy.abs(intensity/numpy.max(intensity))
            pdf /= pdf.sum()
    
            distribution = CustomDistribution(pdf, seed=seed)
    
            sampled = distribution(len(beam_out._beam.rays))
    
            min_value_x = numpy.min(coord_x)
            step_x = numpy.abs(coord_x[1]-coord_x[0])
            min_value_z = numpy.min(coord_z)
            step_z = numpy.abs(coord_z[1]-coord_z[0])
    
            if distribution_type == Distribution.POSITION:
                beam_out._beam.rays[:, 0] = min_value_x + sampled[0, :]*step_x
                beam_out._beam.rays[:, 2] = min_value_z + sampled[1, :]*step_z
    
            elif distribution_type == Distribution.DIVERGENCE:
                alpha_x = min_value_x + sampled[0, :]*step_x
                alpha_z = min_value_z + sampled[1, :]*step_z
    
                beam_out._beam.rays[:, 3] =  numpy.cos(alpha_z)*numpy.sin(alpha_x)
                beam_out._beam.rays[:, 4] =  numpy.cos(alpha_z)*numpy.cos(alpha_x)
                beam_out._beam.rays[:, 5] =  numpy.sin(alpha_z)
        elif kind_of_sampler == 1:
            min_x = numpy.min(coord_x)
            max_x = numpy.max(coord_x)
            delta_x = max_x - min_x
    
            min_z = numpy.min(coord_z)
            max_z = numpy.max(coord_z)
            delta_z = max_z - min_z
    
            dim_x = len(coord_x)
            dim_z = len(coord_z)
    
            grid = Grid2D((dim_x, dim_z))
            grid[..., ...] = intensity.tolist()
    
            d = Distribution2D(distribution_from_grid(grid, dim_x, dim_z), (0, 0), (dim_x, dim_z))
    
            samples = d.get_samples(len(beam_out._beam.rays), seed)
    
            if distribution_type == Distribution.POSITION:
                beam_out._beam.rays[:, 0] = min_x + samples[:, 0]*delta_x
                beam_out._beam.rays[:, 2] = min_z + samples[:, 1]*delta_z
    
            elif distribution_type == Distribution.DIVERGENCE:
                alpha_x = min_x + samples[:, 0]*delta_x
                alpha_z = min_z + samples[:, 1]*delta_z
    
                beam_out._beam.rays[:, 3] =  numpy.cos(alpha_z)*numpy.sin(alpha_x)
                beam_out._beam.rays[:, 4] =  numpy.cos(alpha_z)*numpy.cos(alpha_x)
                beam_out._beam.rays[:, 5] =  numpy.sin(alpha_z)
        else:
            raise ValueError("Sampler not recognized")
        
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


