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

__author__ = 'labx'

import os, sys
import orangecanvas.resources as resources
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from orangewidget import gui, widget
from orangewidget.settings import Setting
from oasys.util.oasys_util import EmittingStream

from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow.util.shadow_objects import ShadowBeam

from PyQt5.QtGui import QImage, QPixmap,  QPalette, QFont, QColor, QTextCursor
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QMessageBox, QFileDialog

from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.shadow.widgets.special_elements import hybrid_control

from orangecontrib.shadow.util.shadow_objects import ShadowPreProcessorData

from orangecontrib.aps.util.gui import HistogramData, StatisticalDataCollection, HistogramDataCollection, \
    DoublePlotWidget, write_histo_and_stats_file
from orangecontrib.aps.shadow.util.gui import Scan3DHistoWidget, ScanHistoWidget

class HybridScreenErrorAnalysis(AutomaticElement):

    inputs = [("Input Beam", ShadowBeam, "setBeam"),
              ("PreProcessor Data", ShadowPreProcessorData, "setPreProcessorData")]

    name = "Hybrid Screen - Error Analysis"
    description = "Shadow HYBRID: Hybrid Screen - Error Analysis"
    icon = "icons/hybrid_screen.png"
    maintainer = "Luca Rebuffi and Xianbo Shi"
    maintainer_email = "lrebuffi(@at@)anl.gov, xshi(@at@)aps.anl.gov"
    priority = 2
    category = "HYBRID"
    keywords = ["data", "file", "load", "read"]

    want_control_area = 1
    want_main_area = 1

    ghy_diff_plane = Setting(1)
    ghy_calcType = Setting(0)

    focal_length_calc = Setting(0)
    ghy_focallength = Setting(0.0)
    distance_to_image_calc = Setting(0)
    ghy_distance = Setting(0.0)

    ghy_nf = Setting(0)

    ghy_nbins_x = Setting(100)
    ghy_nbins_z = Setting(100)
    ghy_npeak = Setting(10)
    ghy_fftnpts = Setting(1e6)

    file_to_write_out = 0

    ghy_automatic = Setting(1)

    files_area = None
    ghy_files = Setting([""])

    input_beam = None

    TABS_AREA_HEIGHT = 560
    CONTROL_AREA_WIDTH = 405

    IMAGE_WIDTH = 865
    IMAGE_HEIGHT = 605

    current_histo_data_x_ff = None
    current_histo_data_x_nf = None
    current_histo_data_z_ff = None
    current_histo_data_z_nf = None
    current_stats_x_ff = None
    current_stats_x_nf = None
    current_stats_z_ff = None
    current_stats_z_nf = None

    plot_type = Setting(1)
    plot_type_3D = Setting(0)
    colormap = Setting(0)

    def __init__(self):
        super().__init__()

        self.runaction = widget.OWAction("Run Hybrid", self)
        self.runaction.triggered.connect(self.run_hybrid)
        self.addAction(self.runaction)

        self.controlArea.setFixedWidth(self.CONTROL_AREA_WIDTH)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Run HYBRID", callback=self.run_hybrid)
        font = QFont(button.font())
        font.setBold(True)
        button.setFont(font)
        palette = QPalette(button.palette()) # make a copy of the palette
        palette.setColor(QPalette.ButtonText, QColor('Dark Blue'))
        button.setPalette(palette) # assign new palette
        button.setFixedHeight(45)

        main_tabs = oasysgui.tabWidget(self.mainArea)
        plot_tab = oasysgui.createTabPage(main_tabs, "Plots")
        out_tab = oasysgui.createTabPage(main_tabs, "Output")

        self.tabs = oasysgui.tabWidget(plot_tab)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(self.TABS_AREA_HEIGHT)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        tab_bas = oasysgui.createTabPage(tabs_setting, "Basic Setting")
        tab_adv = oasysgui.createTabPage(tabs_setting, "Advanced Setting")

        box_1 = oasysgui.widgetBox(tab_bas, "Calculation Parameters", addSpace=True, orientation="vertical", height=100)

        gui.comboBox(box_1, self, "ghy_diff_plane", label="Diffraction Plane", labelWidth=310,
                     items=["Sagittal", "Tangential", "Both (2D)", "Both (1D+1D)"],
                     callback=self.set_DiffPlane,
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(box_1, self, "ghy_calcType", label="Calculation", labelWidth=70,
                     items=["Diffraction by Mirror Size + Figure Errors",
                            "Diffraction by Grating Size + Figure Errors",],
                     callback=self.set_CalculationType,
                     sendSelectedValue=False, orientation="horizontal")

        gui.separator(box_1, 10)

        box_files = oasysgui.widgetBox(tab_bas, "Height Error Profiles", addSpace=True, orientation="vertical", height=180)

        gui.button(box_files, self, "Select Height Error Profile Data Files", callback=self.select_files)

        self.files_area = oasysgui.textArea(height=120, width=360)

        self.refresh_files_text_area()

        box_files.layout().addWidget(self.files_area)

        box_2 = oasysgui.widgetBox(tab_bas, "Numerical Control Parameters", addSpace=True, orientation="vertical", height=140)

        self.le_nbins_x = oasysgui.lineEdit(box_2, self, "ghy_nbins_x", "Number of bins for I(Sagittal) histogram", labelWidth=260, valueType=int, orientation="horizontal")
        self.le_nbins_z = oasysgui.lineEdit(box_2, self, "ghy_nbins_z", "Number of bins for I(Tangential) histogram", labelWidth=260, valueType=int, orientation="horizontal")
        self.le_npeak   = oasysgui.lineEdit(box_2, self, "ghy_npeak",   "Number of diffraction peaks", labelWidth=260, valueType=int, orientation="horizontal")
        self.le_fftnpts = oasysgui.lineEdit(box_2, self, "ghy_fftnpts", "Number of points for FFT", labelWidth=260, valueType=int, orientation="horizontal")

        box_3 = oasysgui.widgetBox(tab_adv, "Propagation Parameters", addSpace=True, orientation="vertical", height=200)

        self.cb_focal_length_calc = gui.comboBox(box_3, self, "focal_length_calc", label="Focal Length", labelWidth=180,
                     items=["Use O.E. Focal Distance", "Specify Value"],
                     callback=self.set_FocalLengthCalc,
                     sendSelectedValue=False, orientation="horizontal")

        self.le_focal_length = oasysgui.lineEdit(box_3, self, "ghy_focallength", "Focal Length value", labelWidth=260, valueType=float, orientation="horizontal")

        gui.separator(box_3)

        self.cb_distance_to_image_calc = gui.comboBox(box_3, self, "distance_to_image_calc", label="Distance to image", labelWidth=150,
                     items=["Use O.E. Image Plane Distance", "Specify Value"],
                     callback=self.set_DistanceToImageCalc,
                     sendSelectedValue=False, orientation="horizontal")

        self.le_distance_to_image = oasysgui.lineEdit(box_3, self, "ghy_distance", "Distance to Image value", labelWidth=260, valueType=float, orientation="horizontal")

        gui.separator(box_3)

        self.cb_nf = gui.comboBox(box_3, self, "ghy_nf", label="Near Field Calculation", labelWidth=310,
                                             items=["No", "Yes"],
                                             sendSelectedValue=False, orientation="horizontal", callback=self.set_NF)


        box_4 = oasysgui.widgetBox(tab_adv, "Geometrical Parameters", addSpace=True, orientation="vertical", height=70)

        gui.comboBox(box_4, self, "ghy_automatic", label="Analize geometry to avoid unuseful calculations", labelWidth=310,
                     items=["No", "Yes"],
                     sendSelectedValue=False, orientation="horizontal")


        box_5 = oasysgui.widgetBox(tab_adv, "Plot Setting", addSpace=True, orientation="vertical", height=150)

        gui.comboBox(box_5, self, "plot_type", label="Plot Type", labelWidth=310,
                     items=["2D", "3D"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_PlotType)

        self.box_pt_1 = oasysgui.widgetBox(box_5, "", addSpace=False, orientation="vertical", height=30)
        self.box_pt_2 = oasysgui.widgetBox(box_5, "", addSpace=False, orientation="vertical", height=30)

        gui.comboBox(self.box_pt_2, self, "plot_type_3D", label="3D Plot Aspect", labelWidth=310,
                     items=["Lines", "Surface"],
                     sendSelectedValue=False, orientation="horizontal")

        self.set_DiffPlane()
        self.set_DistanceToImageCalc()
        self.set_CalculationType()
        self.set_NF()
        self.set_PlotType()

        self.initializeTabs()

        adv_other_box = oasysgui.widgetBox(tab_bas, "Export Data", addSpace=False, orientation="vertical")

        gui.button(adv_other_box, self, "Export Error Analysis", callback=self.export_error_analysis)

        self.shadow_output = oasysgui.textArea(height=580, width=800)

        out_box = gui.widgetBox(out_tab, "System Output", addSpace=True, orientation="horizontal")
        out_box.layout().addWidget(self.shadow_output)

    def after_change_workspace_units(self):
        label = self.le_focal_length.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_distance_to_image.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")


    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "Select Height Error Profiles", "","Data Files (*.dat);;Sha Files (*.sha)",
                                                options=QFileDialog.Options())
        if files:
            self.ghy_files = files

            self.refresh_files_text_area()

    def initializeTabs(self):
        self.tabs.clear()

        tabs = []

        if self.ghy_diff_plane < 2:


            tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Image Plane")))

            self.tab = [[gui.createTabPage(tabs[0], "Position"), gui.createTabPage(tabs[0], "Stats")]]

            if self.ghy_nf == 1:
                tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Near Field")))

                self.tab.append([gui.createTabPage(tabs[1], "Position"), gui.createTabPage(tabs[1], "Stats")])

        elif self.ghy_diff_plane >= 2:
            if self.ghy_nf == 1:
                tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Image Plane (S)")))
                tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Near Field (S)")))
                tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Image Plane (T)")))
                tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Near Field (T)")))

                self.tab = [[gui.createTabPage(tabs[0], "Position"), gui.createTabPage(tabs[0], "Stats")],
                            [gui.createTabPage(tabs[1], "Position"), gui.createTabPage(tabs[1], "Stats")],
                            [gui.createTabPage(tabs[2], "Position"), gui.createTabPage(tabs[2], "Stats")],
                            [gui.createTabPage(tabs[3], "Position"), gui.createTabPage(tabs[3], "Stats")]
                            ]
            else:
                tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Image Plane (S)")))
                tabs.append(oasysgui.tabWidget(gui.createTabPage(self.tabs, "Distribution of Position at Image Plane (T)")))

                self.tab = [[gui.createTabPage(tabs[0], "Position"), gui.createTabPage(tabs[0], "Stats")],
                            [gui.createTabPage(tabs[1], "Position"), gui.createTabPage(tabs[1], "Stats")]
                            ]

        for tab in tabs:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

        self.plot_canvas = [None, None, None, None]
        self.plot_canvas_stats = [None, None, None, None]


    def plot_emtpy(self, progressBarValue, plot_canvas_index):
        if self.plot_canvas[plot_canvas_index] is None:
            widget = QWidget()
            widget.setLayout(QHBoxLayout())
            label = QLabel(widget)
            label.setPixmap(QPixmap(QImage(os.path.join(resources.package_dirname("orangecontrib.shadow.widgets.extension"), "icons", "no_result.png"))))

            widget.layout().addWidget(label)

            self.plot_canvas[plot_canvas_index] = widget

            self.tab[plot_canvas_index].layout().addWidget(self.plot_canvas[plot_canvas_index])

        self.progressBarSet(progressBarValue)

    def setBeam(self, beam):
        if ShadowCongruence.checkEmptyBeam(beam):
            if ShadowCongruence.checkGoodBeam(beam):
                self.input_beam = beam

                if self.is_automatic_run:
                    self.run_hybrid()

    def set_PlotType(self):
        self.plot_canvas = [None, None, None, None]

        self.box_pt_1.setVisible(self.plot_type==0)
        self.box_pt_2.setVisible(self.plot_type==1)

    def set_DiffPlane(self):
        self.le_nbins_x.setEnabled(self.ghy_diff_plane == 0 or self.ghy_diff_plane == 2)
        self.le_nbins_z.setEnabled(self.ghy_diff_plane == 1 or self.ghy_diff_plane == 2)

        if self.ghy_diff_plane != 2:
            self.cb_nf.setEnabled(True)
        else:
            self.cb_nf.setEnabled(False)
            self.ghy_nf = 0

        self.set_NF()

    def set_CalculationType(self):
        if self.ghy_diff_plane != 2:
            self.cb_nf.setEnabled(True)
        else:
            self.cb_nf.setEnabled(False)
            self.ghy_nf = 0

        self.set_NF()

    def set_NF(self):
        if self.ghy_nf == 0:
            self.focal_length_calc = 0
            self.distance_to_image_calc = 0
            self.cb_focal_length_calc.setEnabled(False)
            self.le_focal_length.setEnabled(False)
        else:
            self.cb_focal_length_calc.setEnabled(True)
            self.le_focal_length.setEnabled(True)

        self.set_FocalLengthCalc()

    def set_FocalLengthCalc(self):
         self.le_focal_length.setEnabled(self.focal_length_calc == 1)

    def set_DistanceToImageCalc(self):
         self.le_distance_to_image.setEnabled(self.distance_to_image_calc == 1)

    def run_hybrid(self):
        try:
            self.setStatusMessage("")
            self.progressBarInit()
            self.initializeTabs()

            if ShadowCongruence.checkEmptyBeam(self.input_beam):
                if ShadowCongruence.checkGoodBeam(self.input_beam):
                    sys.stdout = EmittingStream(textWritten=self.write_stdout)

                    self.check_fields()

                    input_parameters = hybrid_control.HybridInputParameters()
                    input_parameters.ghy_lengthunit = self.workspace_units
                    input_parameters.widget = self
                    input_parameters.ghy_diff_plane = self.ghy_diff_plane + 1

                    if self.distance_to_image_calc == 0:
                        input_parameters.ghy_distance = -1
                    else:
                        input_parameters.ghy_distance = self.ghy_distance

                    if self.focal_length_calc == 0:
                        input_parameters.ghy_focallength = -1
                    else:
                        input_parameters.ghy_focallength = self.ghy_focallength

                    input_parameters.ghy_nf = self.ghy_nf

                    input_parameters.ghy_nbins_x = int(self.ghy_nbins_x)
                    input_parameters.ghy_nbins_z = int(self.ghy_nbins_z)
                    input_parameters.ghy_npeak = int(self.ghy_npeak)
                    input_parameters.ghy_fftnpts = int(self.ghy_fftnpts)
                    input_parameters.file_to_write_out = self.file_to_write_out

                    input_parameters.ghy_automatic = self.ghy_automatic

                    # -----------------------------------------------
                    #cycling or figure errors

                    # add the reference (no error profile)

                    shadow_beam = self.input_beam.duplicate()

                    history_entry =  shadow_beam.getOEHistory(shadow_beam._oe_number)
                    shadow_oe = history_entry._shadow_oe_start # changes to the original object!
                    shadow_oe._oe.F_RIPPLE = 0

                    input_parameters.ghy_calcType = 2

                    input_parameters.shadow_beam = shadow_beam

                    calculation_parameters = hybrid_control.hy_run(input_parameters)

                    self.ghy_focallength = input_parameters.ghy_focallength
                    self.ghy_distance = input_parameters.ghy_distance
                    self.ghy_nbins_x = int(input_parameters.ghy_nbins_x)
                    self.ghy_nbins_z = int(input_parameters.ghy_nbins_z)
                    self.ghy_npeak   = int(input_parameters.ghy_npeak)
                    self.ghy_fftnpts = int(input_parameters.ghy_fftnpts)

                    if input_parameters.ghy_calcType == 3 or input_parameters.ghy_calcType == 4:
                        do_plot_x = True
                        do_plot_z = True
                    else:
                        if self.ghy_automatic == 1:
                            do_plot_x = not calculation_parameters.beam_not_cut_in_x
                            do_plot_z = not calculation_parameters.beam_not_cut_in_z
                        else:
                            do_plot_x = True
                            do_plot_z = True

                    do_nf = input_parameters.ghy_nf == 1 and input_parameters.ghy_calcType > 1

                    if do_plot_x or do_plot_z:
                        self.setStatusMessage("Plotting Results")

                    profile = 0

                    self.current_histo_data_x_ff = None
                    self.current_histo_data_x_nf = None
                    self.current_histo_data_z_ff = None
                    self.current_histo_data_z_nf = None
                    self.current_stats_x_ff = None
                    self.current_stats_x_nf = None
                    self.current_stats_z_ff = None
                    self.current_stats_z_nf = None

                    histo_data_x_ff, \
                    histo_data_z_ff, \
                    histo_data_x_nf, \
                    histo_data_z_nf = self.plot_results(calculation_parameters=calculation_parameters,
                                                        do_nf=do_nf,
                                                        do_plot_x=do_plot_x,
                                                        do_plot_z=do_plot_z,
                                                        histo_data_x_ff=HistogramData(),
                                                        histo_data_z_ff=HistogramData(),
                                                        histo_data_x_nf=HistogramData(),
                                                        histo_data_z_nf=HistogramData(),
                                                        profile=profile)

                    if not histo_data_x_ff.bins is None: self.current_histo_data_x_ff = HistogramDataCollection(histo_data_x_ff)
                    if not histo_data_z_ff.bins is None: self.current_histo_data_z_ff = HistogramDataCollection(histo_data_z_ff)
                    if not histo_data_x_nf.bins is None: self.current_histo_data_x_nf = HistogramDataCollection(histo_data_x_nf)
                    if not histo_data_z_nf.bins is None: self.current_histo_data_z_nf = HistogramDataCollection(histo_data_z_nf)

                    stats_x_ff = StatisticalDataCollection(histo_data_x_ff)
                    stats_z_ff = StatisticalDataCollection(histo_data_z_ff)
                    stats_x_nf = StatisticalDataCollection(histo_data_x_nf)
                    stats_z_nf = StatisticalDataCollection(histo_data_z_nf)

                    input_parameters.ghy_calcType = self.ghy_calcType + 3

                    for file in self.ghy_files:
                        shadow_beam = self.input_beam.duplicate()

                        history_entry =  shadow_beam.getOEHistory(shadow_beam._oe_number)
                        shadow_oe = history_entry._shadow_oe_start # changes to the original object!

                        shadow_oe._oe.F_RIPPLE = 1
                        shadow_oe._oe.F_G_S = 2

                        file = congruence.checkFile(file)
                        ShadowCongruence.checkErrorProfileFile(file)

                        shadow_oe._oe.FILE_RIP = bytes(file, 'utf-8')

                        input_parameters.shadow_beam = shadow_beam

                        calculation_parameters = hybrid_control.hy_run(input_parameters)

                        if do_plot_x or do_plot_z:
                            self.setStatusMessage("Plotting Results")

                        profile += 1

                        histo_data_x_ff, \
                        histo_data_z_ff, \
                        histo_data_x_nf, \
                        histo_data_z_nf = self.plot_results(calculation_parameters,
                                                            do_nf,
                                                            do_plot_x,
                                                            do_plot_z,
                                                            histo_data_x_ff,
                                                            histo_data_z_ff,
                                                            histo_data_x_nf,
                                                            histo_data_z_nf,
                                                            profile)

                        if not histo_data_x_ff.bins is None: self.current_histo_data_x_ff.add_histogram_data(histo_data_x_ff)
                        if not histo_data_z_ff.bins is None: self.current_histo_data_z_ff.add_histogram_data(histo_data_z_ff)
                        if not histo_data_x_nf.bins is None: self.current_histo_data_x_nf.add_histogram_data(histo_data_x_nf)
                        if not histo_data_z_nf.bins is None: self.current_histo_data_z_nf.add_histogram_data(histo_data_z_nf)

                        stats_x_ff.add_statistical_data(histo_data_x_ff)
                        stats_z_ff.add_statistical_data(histo_data_z_ff)
                        stats_x_nf.add_statistical_data(histo_data_x_nf)
                        stats_z_nf.add_statistical_data(histo_data_z_nf)

                    self.current_stats_x_ff = stats_x_ff
                    self.current_stats_z_ff = stats_z_ff
                    self.current_stats_x_nf = stats_x_nf
                    self.current_stats_z_nf = stats_z_nf

                    self.add_empty_curves(do_nf,
                                          do_plot_x,
                                          do_plot_z,
                                          histo_data_x_ff,
                                          histo_data_x_nf,
                                          histo_data_z_ff,
                                          histo_data_z_nf)


                    self.plot_stats(do_nf,
                                    do_plot_x,
                                    do_plot_z,
                                    stats_x_ff,
                                    stats_z_ff,
                                    stats_x_nf,
                                    stats_z_nf,)

                else:
                    raise Exception("Input Beam with no good rays")
            else:
                raise Exception("Empty Input Beam")
        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

        self.setStatusMessage("")
        self.progressBarFinished()

    def plot_results(self, 
                     calculation_parameters, 
                     do_nf, 
                     do_plot_x, 
                     do_plot_z, 
                     histo_data_x_ff,
                     histo_data_z_ff, 
                     histo_data_x_nf, 
                     histo_data_z_nf, 
                     profile):
        if self.ghy_diff_plane == 0:
            if do_plot_x:
                histo_data_x_ff = self.plot_histo(calculation_parameters.ff_beam, 1, progressBarValue=88,
                                              plot_canvas_index=0, title="X",
                                              xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                              offset=histo_data_x_ff.offset, xrange=histo_data_x_ff.xrange)
                if do_nf:
                    histo_data_x_nf = self.plot_histo(calculation_parameters.nf_beam, 1, progressBarValue=96,
                                                  plot_canvas_index=1, title="X",
                                                  xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_x_nf.offset, xrange=histo_data_x_nf.xrange)
            else:
                if do_nf:
                    self.plot_emtpy(88, 0)
                    self.plot_emtpy(96, 1)
                else:
                    self.plot_emtpy(88, 0)
        elif self.ghy_diff_plane == 1:
            if do_plot_z:
                histo_data_z_ff = self.plot_histo(calculation_parameters.ff_beam, 3, progressBarValue=88,
                                              plot_canvas_index=0, title="Z",
                                              xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                              offset=histo_data_z_ff.offset, xrange=histo_data_z_ff.xrange)
                if do_nf:
                    histo_data_z_nf = self.plot_histo(calculation_parameters.nf_beam, 3, progressBarValue=96,
                                                  plot_canvas_index=1, title="Z",
                                                  xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_z_nf.offset, xrange=histo_data_z_nf.xrange)
            else:
                self.plot_emtpy(88, 0)

                if do_nf:
                    self.plot_emtpy(96, 1)

        elif self.ghy_diff_plane >= 2:
            if do_plot_x and do_plot_z:
                histo_data_x_ff = self.plot_histo(calculation_parameters.ff_beam, 1, progressBarValue=88,
                                              plot_canvas_index=0, title="X",
                                              xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                              offset=histo_data_x_ff.offset, xrange=histo_data_x_ff.xrange)
                histo_data_z_ff = self.plot_histo(calculation_parameters.ff_beam, 3, progressBarValue=88,
                                              plot_canvas_index=1, title="Z",
                                              xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                              offset=histo_data_z_ff.offset, xrange=histo_data_z_ff.xrange)
                if do_nf:
                    histo_data_x_nf = self.plot_histo(calculation_parameters.nf_beam, 1, progressBarValue=96,
                                                  plot_canvas_index=2, title="X",
                                                  xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_x_nf.offset, xrange=histo_data_x_nf.xrange)
                    histo_data_z_nf = self.plot_histo(calculation_parameters.nf_beam, 3, progressBarValue=96,
                                                  plot_canvas_index=3, title="Z",
                                                  xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_z_nf.offset, xrange=histo_data_z_nf.xrange)
            else:
                if do_plot_x:
                    histo_data_x_ff = self.plot_histo(calculation_parameters.ff_beam, 1, progressBarValue=88,
                                                  plot_canvas_index=0, title="X",
                                                  xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_x_ff.offset, xrange=histo_data_x_ff.xrange)
                    if do_nf:
                        histo_data_x_nf = self.plot_histo(calculation_parameters.nf_beam, 1, progressBarValue=96,
                                                      plot_canvas_index=1, title="X",
                                                      xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                      offset=histo_data_x_nf.offset, xrange=histo_data_x_nf.xrange)
                elif do_plot_z:
                    histo_data_z_ff = self.plot_histo(calculation_parameters.ff_beam, 3, progressBarValue=88,
                                                  plot_canvas_index=0, title="Z",
                                                  xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_z_ff.offset, xrange=histo_data_z_ff.xrange)
                    if do_nf:
                        histo_data_z_nf = self.plot_histo(calculation_parameters.nf_beam, 3, progressBarValue=96,
                                                      plot_canvas_index=1, title="Z",
                                                      xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                      offset=histo_data_z_nf.offset, xrange=histo_data_z_nf.xrange)
                else:
                    self.plot_emtpy(88, 0)

                    if do_nf:
                        self.plot_emtpy(96, 1)

        return histo_data_x_ff, histo_data_z_ff, histo_data_x_nf, histo_data_z_nf

    def add_empty_curves(self, do_nf, do_plot_x, do_plot_z, histo_data_x_ff, histo_data_x_nf, histo_data_z_ff,
                         histo_data_z_nf):

        if self.ghy_diff_plane == 0:
            if do_plot_x:
                self.plot_canvas_stats[0].add_empty_curve(histo_data_x_ff)

                if do_nf:
                    self.plot_canvas[1].add_empty_curve(histo_data_x_nf)
        elif self.ghy_diff_plane == 1:
            if do_plot_z:
                self.plot_canvas[0].add_empty_curve(histo_data_z_ff)

                if do_nf:
                    self.plot_canvas[1].add_empty_curve(histo_data_z_nf)
        else:
            if do_plot_x and do_plot_z:
                self.plot_canvas[0].add_empty_curve(histo_data_x_ff)
                self.plot_canvas[1].add_empty_curve(histo_data_z_ff)

                if do_nf:
                    self.plot_canvas[2].add_empty_curve(histo_data_x_nf)
                    self.plot_canvas[3].add_empty_curve(histo_data_z_nf)
            else:
                if do_plot_x:
                    self.plot_canvas[0].add_empty_curve(histo_data_x_ff)

                    if do_nf:
                        self.plot_canvas[1].add_empty_curve(histo_data_x_nf)
                elif do_plot_z:
                    self.plot_canvas[0].add_empty_curve(histo_data_z_ff)

                    if do_nf:
                        self.plot_canvas[1].add_empty_curve(histo_data_z_nf)

    def plot_stats(self, do_nf, do_plot_x, do_plot_z, stats_x_ff, stats_z_ff, stats_x_nf, stats_z_nf):

        if self.ghy_diff_plane == 0:
            if do_plot_x:
                self.plot_stat(stats_x_ff, 0)

                if do_nf:
                    self.plot_stat(stats_x_nf, 1)
        elif self.ghy_diff_plane == 1:
            if do_plot_z:
                self.plot_stat(stats_z_ff, 0)

                if do_nf:
                    self.plot_stat(stats_z_nf, 1)
        else:
            if do_plot_x and do_plot_z:
                self.plot_stat(stats_x_ff, 0)
                self.plot_stat(stats_z_ff, 1)

                if do_nf:
                    self.plot_stat(stats_x_nf, 2)
                    self.plot_stat(stats_z_nf, 3)

            else:
                if do_plot_x:
                    self.plot_stat(stats_x_ff, 0)

                    if do_nf:
                        self.plot_stat(stats_x_nf, 1)
                elif do_plot_z:
                    self.plot_stat(stats_z_ff, 0)

                    if do_nf:
                        self.plot_stat(stats_z_nf, 1)

    def plot_stat(self, stats, plot_canvas_index, sigma_um="$\mu$m"):
        if self.plot_canvas_stats[plot_canvas_index] is None:
            self.plot_canvas_stats[plot_canvas_index] = DoublePlotWidget(parent=None)

            self.tab[plot_canvas_index][1].layout().addWidget(self.plot_canvas_stats[plot_canvas_index])

        self.plot_canvas_stats[plot_canvas_index].plotCurves(stats.get_scan_values(),
                                                             stats.get_sigmas(),
                                                             stats.get_relative_peak_intensities(),
                                                             "Statistics",
                                                             "Profiles",
                                                             "Sigma [" + sigma_um + "]",
                                                             "Relative Peak Intensity")

    def plot_histo(self, beam, col, nbins=100, progressBarValue=80, plot_canvas_index=0, title="", xtitle="", ytitle="",
                   profile=1, offset=0.0, xrange=None):

        if self.plot_canvas[plot_canvas_index] is None:
            if self.plot_type == 0:
                self.plot_canvas[plot_canvas_index] = ScanHistoWidget(self.workspace_units_to_cm)
            elif self.plot_type==1:
                self.plot_canvas[plot_canvas_index] = Scan3DHistoWidget(self.workspace_units_to_cm,
                                                                        type=Scan3DHistoWidget.PlotType.LINES if self.plot_type_3D==0 else Scan3DHistoWidget.PlotType.SURFACE)

            self.tab[plot_canvas_index][0].layout().addWidget(self.plot_canvas[plot_canvas_index])

        histo_data = self.plot_canvas[plot_canvas_index].plot_histo(beam=beam,
                                                                    col=col,
                                                                    nbins=nbins,
                                                                    title=title,
                                                                    xtitle=xtitle,
                                                                    ytitle=ytitle,
                                                                    histo_index=profile,
                                                                    scan_variable_name="Profile #",
                                                                    scan_variable_value=profile,
                                                                    offset=offset,
                                                                    xrange=xrange)
        histo_data.scan_value=profile

        self.progressBarSet(progressBarValue)

        return histo_data

    def check_fields(self):
        if self.focal_length_calc == 1:
            congruence.checkPositiveNumber(self.ghy_focallength, "Focal Length value")

        if self.distance_to_image_calc == 1:
            congruence.checkPositiveNumber(self.ghy_distance, "Distance to image value")

        if self.ghy_diff_plane == 0 or self.ghy_diff_plane == 2:
            congruence.checkStrictlyPositiveNumber(self.ghy_nbins_x, "Number of bins for I(Sagittal) histogram")
        if self.ghy_diff_plane == 1 or self.ghy_diff_plane == 2:
            congruence.checkStrictlyPositiveNumber(self.ghy_nbins_z, "Number of bins for I(Tangential) histogram")

        if self.ghy_files is None or len(self.ghy_files) == 0 or (len(self.ghy_files) == 1 and self.ghy_files[0] == ""):
            raise ValueError("Height Error Profiles list is empty")

        congruence.checkStrictlyPositiveNumber(self.ghy_npeak, "Number of diffraction peaks")
        congruence.checkStrictlyPositiveNumber(self.ghy_fftnpts, "Number of points for FFT")

    def set_progress_bar(self, value):
        if value >= 100:
            self.progressBarFinished()
        elif value <=0:
            self.progressBarInit()
        else:
            self.progressBarSet(value)

    def status_message(self, message):
        self.setStatusMessage(message)

    def write_stdout(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

    def setPreProcessorData(self, data):
        if data is not None:
            if data.error_profile_data_file != ShadowPreProcessorData.NONE:
                if isinstance(data.error_profile_data_file, str):
                    self.ghy_files.append(data.error_profile_data_file)
                elif isinstance(data.error_profile_data_file, list):
                    self.ghy_files = data.error_profile_data_file
                else:
                    raise ValueError("Error Profile Data File: format not recognized")

                self.refresh_files_text_area()

    def refresh_files_text_area(self):
        text = ""
        for file in self.ghy_files:
            text += file + "\n"
        self.files_area.setText(text)

    def export_error_analysis(self):

        output_folder = QFileDialog.getExistingDirectory(self, "Select Output Directory", directory=os.curdir)

        if output_folder:
            if not self.current_histo_data_x_ff is None:
                write_histo_and_stats_file(histo_data=self.current_histo_data_x_ff,
                                           stats=self.current_stats_x_ff,
                                           suffix="_S_FF",
                                           output_folder=output_folder)

            if not self.current_histo_data_x_nf is None:
                write_histo_and_stats_file(histo_data=self.current_histo_data_x_nf,
                                           stats=self.current_stats_x_nf,
                                           suffix="_S_NF",
                                           output_folder=output_folder)

            if not self.current_histo_data_z_ff is None:
                write_histo_and_stats_file(histo_data=self.current_histo_data_z_ff,
                                           stats=self.current_stats_z_ff,
                                           suffix="_T_FF",
                                           output_folder=output_folder)

            if not self.current_histo_data_z_nf is None:
                write_histo_and_stats_file(histo_data=self.current_histo_data_z_nf.bins,
                                           stats=self.current_stats_z_nf,
                                           suffix="_T_NF",
                                           output_folder=output_folder)

            QMessageBox.information(self, "Export Error Analysis Data", "Data saved into directory: " + output_folder, QMessageBox.Ok)
