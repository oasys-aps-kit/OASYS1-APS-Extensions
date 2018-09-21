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
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt

from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.shadow.widgets.special_elements import hybrid_control

from orangecontrib.shadow.util.shadow_objects import ShadowPreProcessorData

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5 import NavigationToolbar2QT as NavigationToolbar

class HistoData(object):
    histogram = None
    bins = None
    offset = 0.0
    xrange = None
    sigma = 0.0
    peak_intensity = 0.0

    def __init__(self, histogram=None, bins=None, offset=0.0, xrange=None, sigma=0.0, peak_intensity=0.0):
        self.histogram = histogram
        self.bins = bins
        self.offset = offset
        self.xrange = xrange
        self.sigma = sigma
        self.peak_intensity = peak_intensity

    def get_centroid(self):
        return self.xrange[0] + (self.xrange[1] - self.xrange[0])*0.5

class HybridScreenErrorAnalysis(AutomaticElement):

    inputs = [("Input Beam", ShadowBeam, "setBeam"),
              ("PreProcessor Data", ShadowPreProcessorData, "setPreProcessorData")]

    name = "Hybrid Screen - Error Analysis"
    description = "Shadow HYBRID: Hybrid Screen - Error Analysis"
    icon = "icons/hybrid_screen.png"
    maintainer = "Luca Rebuffi and Xianbo Shi"
    maintainer_email = "lrebuffi(@at@)anl.gov, xshi(@at@)aps.anl.gov"
    priority = 1
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

        self.set_DiffPlane()
        self.set_DistanceToImageCalc()
        self.set_CalculationType()
        self.set_NF()

        self.initializeTabs()

        adv_other_box = oasysgui.widgetBox(tab_bas, "Export Data", addSpace=False, orientation="vertical")

        gui.button(adv_other_box, self, "Export Error Analysis", callback=self.export_error_analysis)

        self.shadow_output = oasysgui.textArea(height=590, width=800)

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

                    self.current_histo_data_x_ff = []
                    self.current_histo_data_x_nf = []
                    self.current_histo_data_z_ff = []
                    self.current_histo_data_z_nf = []
                    self.current_stats_x_ff = []
                    self.current_stats_x_nf = []
                    self.current_stats_z_ff = []
                    self.current_stats_z_nf = []

                    histo_data_x_ff, \
                    histo_data_z_ff, \
                    histo_data_x_nf, \
                    histo_data_z_nf = self.plot_results(calculation_parameters=calculation_parameters,
                                                        do_nf=do_nf,
                                                        do_plot_x=do_plot_x,
                                                        do_plot_z=do_plot_z,
                                                        histo_data_x_ff=HistoData(),
                                                        histo_data_z_ff=HistoData(),
                                                        histo_data_x_nf=HistoData(),
                                                        histo_data_z_nf=HistoData(),
                                                        profile=profile)

                    if not histo_data_x_ff.bins is None: self.current_histo_data_x_ff.append([histo_data_x_ff.bins, histo_data_x_ff.histogram])
                    if not histo_data_z_ff.bins is None: self.current_histo_data_z_ff.append([histo_data_z_ff.bins, histo_data_z_ff.histogram])
                    if not histo_data_x_nf.bins is None: self.current_histo_data_x_nf.append([histo_data_x_nf.bins, histo_data_x_nf.histogram])
                    if not histo_data_z_nf.bins is None: self.current_histo_data_z_nf.append([histo_data_z_nf.bins, histo_data_z_nf.histogram])

                    stats_x_ff = [[histo_data_x_ff.sigma], [histo_data_x_ff.peak_intensity]]
                    stats_z_ff = [[histo_data_z_ff.sigma], [histo_data_z_ff.peak_intensity]]
                    stats_x_nf = [[histo_data_x_nf.sigma], [histo_data_x_nf.peak_intensity]]
                    stats_z_nf = [[histo_data_z_nf.sigma], [histo_data_z_nf.peak_intensity]]


                    #centroid_x_ff = histo_data_x_ff.get_centroid()

                    input_parameters.ghy_calcType = self.ghy_calcType + 3

                    for file in self.ghy_files:
                        shadow_beam = self.input_beam.duplicate()

                        history_entry =  shadow_beam.getOEHistory(shadow_beam._oe_number)
                        shadow_oe = history_entry._shadow_oe_start # changes to the original object!

                        shadow_oe._oe.F_RIPPLE = 1
                        shadow_oe._oe.F_G_S = 2

                        shadow_oe._oe.FILE_RIP = bytes(congruence.checkFile(file), 'utf-8')

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

                        if not histo_data_x_ff.bins is None: self.current_histo_data_x_ff.append([histo_data_x_ff.bins, histo_data_x_ff.histogram])
                        if not histo_data_z_ff.bins is None: self.current_histo_data_z_ff.append([histo_data_z_ff.bins, histo_data_z_ff.histogram])
                        if not histo_data_x_nf.bins is None: self.current_histo_data_x_nf.append([histo_data_x_nf.bins, histo_data_x_nf.histogram])
                        if not histo_data_z_nf.bins is None: self.current_histo_data_z_nf.append([histo_data_z_nf.bins, histo_data_z_nf.histogram])

                        stats_x_ff[0].append(histo_data_x_ff.sigma)
                        stats_z_ff[0].append(histo_data_z_ff.sigma)
                        stats_x_nf[0].append(histo_data_x_nf.sigma)
                        stats_z_nf[0].append(histo_data_z_nf.sigma)
                        stats_x_ff[1].append(histo_data_x_ff.peak_intensity)
                        stats_z_ff[1].append(histo_data_z_ff.peak_intensity)
                        stats_x_nf[1].append(histo_data_x_nf.peak_intensity)
                        stats_z_nf[1].append(histo_data_z_nf.peak_intensity)

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
            #self.error_id = self.error_id + 1
            #self.error(self.error_id, "Exception occurred: " + str(exception))

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
                self.plot_canvas[0].addCurve(numpy.array([histo_data_x_ff.get_centroid()]),
                                             numpy.zeros(1),
                                             "Click on curve to highlight it",
                                             xlabel="", ylabel="",
                                             symbol='', color='white')

                self.plot_canvas[0].setActiveCurve("Click on curve to highlight it")

                if do_nf:
                    self.plot_canvas[1].addCurve(numpy.array([histo_data_x_nf.get_centroid()]),
                                                 numpy.zeros(1),
                                                 "Click on curve to highlight it",
                                                 xlabel="", ylabel="",
                                                 symbol='', color='white')

                    self.plot_canvas[1].setActiveCurve("Click on curve to highlight it")
        elif self.ghy_diff_plane == 1:
            if do_plot_z:
                self.plot_canvas[0].addCurve(numpy.array([histo_data_z_ff.get_centroid()]),
                                             numpy.zeros(1),
                                             "Click on curve to highlight it",
                                             xlabel="", ylabel="",
                                             symbol='', color='white')

                self.plot_canvas[0].setActiveCurve("Click on curve to highlight it")

                if do_nf:
                    self.plot_canvas[1].addCurve(numpy.array([histo_data_z_nf.get_centroid()]),
                                                 numpy.zeros(1),
                                                 "Click on curve to highlight it",
                                                 xlabel="", ylabel="",
                                                 symbol='', color='white')

                    self.plot_canvas[1].setActiveCurve("Click on curve to highlight it")
        else:
            if do_plot_x and do_plot_z:
                self.plot_canvas[0].addCurve(numpy.array([histo_data_x_ff.get_centroid()]),
                                             numpy.zeros(1),
                                             "Click on curve to highlight it",
                                             xlabel="", ylabel="",
                                             symbol='', color='white')

                self.plot_canvas[0].setActiveCurve("Click on curve to highlight it")

                self.plot_canvas[1].addCurve(numpy.array([histo_data_z_ff.get_centroid()]),
                                             numpy.zeros(1),
                                             "Click on curve to highlight it",
                                             xlabel="", ylabel="",
                                             symbol='', color='white')

                self.plot_canvas[1].setActiveCurve("Click on curve to highlight it")

                if do_nf:
                    self.plot_canvas[2].addCurve(numpy.array([histo_data_x_nf.get_centroid()]),
                                                 numpy.zeros(1),
                                                 "Click on curve to highlight it",
                                                 xlabel="", ylabel="",
                                                 symbol='', color='white')

                    self.plot_canvas[2].setActiveCurve("Click on curve to highlight it")

                    self.plot_canvas[2].addCurve(numpy.array([histo_data_z_nf.get_centroid()]),
                                                 numpy.zeros(1),
                                                 "Click on curve to highlight it",
                                                 xlabel="", ylabel="",
                                                 symbol='', color='white')

                    self.plot_canvas[2].setActiveCurve("Click on curve to highlight it")
            else:
                if do_plot_x:
                    self.plot_canvas[0].addCurve(numpy.array([histo_data_x_ff.get_centroid()]),
                                                 numpy.zeros(1),
                                                 "Click on curve to highlight it",
                                                 xlabel="", ylabel="",
                                                 symbol='', color='white')

                    self.plot_canvas[0].setActiveCurve("Click on curve to highlight it")

                    if do_nf:
                        self.plot_canvas[1].addCurve(numpy.array([histo_data_x_nf.get_centroid()]),
                                                     numpy.zeros(1),
                                                     "Click on curve to highlight it",
                                                     xlabel="", ylabel="",
                                                     symbol='', color='white')

                        self.plot_canvas[1].setActiveCurve("Click on curve to highlight it")
                elif do_plot_z:
                    self.plot_canvas[0].addCurve(numpy.array([histo_data_z_ff.get_centroid()]),
                                                 numpy.zeros(1),
                                                 "Click on curve to highlight it",
                                                 xlabel="", ylabel="",
                                                 symbol='', color='white')

                    self.plot_canvas[0].setActiveCurve("Click on curve to highlight it")

                    if do_nf:
                        self.plot_canvas[1].addCurve(numpy.array([histo_data_z_nf.get_centroid()]),
                                                     numpy.zeros(1),
                                                     "Click on curve to highlight it",
                                                     xlabel="", ylabel="",
                                                     symbol='', color='white')

                        self.plot_canvas[1].setActiveCurve("Click on curve to highlight it")

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
            self.plot_canvas_stats[plot_canvas_index] = StatsPlotWindow2(parent=None)

            self.tab[plot_canvas_index][1].layout().addWidget(self.plot_canvas_stats[plot_canvas_index])

        self.plot_canvas_stats[plot_canvas_index].plotCurves(numpy.arange(0, len(stats[0])),
                                                             stats[0][:],
                                                             stats[1][:]/stats[1][0],
                                                             "Statistics",
                                                             "Profiles",
                                                             "Sigma [" + sigma_um + "]",
                                                             "Relative Peak Intensity")

    def plot_histo(self, beam, col, nbins=100, progressBarValue=80, plot_canvas_index=0, title="", xtitle="", ytitle="",
                   profile=1, control=True, offset=0.0, xrange=None):

        factor=ShadowPlot.get_factor(col, conv=self.workspace_units_to_cm)

        if profile == 0:
            ticket = beam._beam.histo1(col, xrange=None, nbins=nbins, nolost=1, ref=23)

            fwhm = ticket['fwhm']
            xrange = ticket['xrange']
            centroid = xrange[0] + (xrange[1] - xrange[0])*0.5
            xrange = [centroid - 2*fwhm , centroid + 2*fwhm]

        ticket = beam._beam.histo1(col, xrange=xrange, nbins=nbins, nolost=1, ref=23)

        if not ytitle is None:  ytitle = ytitle + ' weighted by ' + ShadowPlot.get_shadow_label(23)

        histogram = ticket['histogram_path']
        bins = ticket['bin_path']*factor

        histogram_stats = ticket['histogram']
        bins_stats = ticket['bin_center']


        sigma =  numpy.average(ticket['histogram_sigma'])
        peak_intensity = numpy.average(histogram_stats[numpy.where(histogram_stats>=numpy.max(histogram_stats)*0.85)])

        if profile == 0:
            h_title = "Reference"
        else:
            h_title = "Profile #" + str(profile)

        color="#000000"

        if self.plot_canvas[plot_canvas_index] is None:
            self.plot_canvas[plot_canvas_index] = oasysgui.plotWindow(parent=None,
                                                                      backend=None,
                                                                      resetzoom=True,
                                                                      autoScale=False,
                                                                      logScale=False,
                                                                      grid=True,
                                                                      curveStyle=True,
                                                                      colormap=False,
                                                                      aspectRatio=False,
                                                                      yInverted=False,
                                                                      copy=True,
                                                                      save=True,
                                                                      print_=True,
                                                                      control=control,
                                                                      position=True,
                                                                      roi=False,
                                                                      mask=False,
                                                                      fit=False)

            self.tab[plot_canvas_index][0].layout().addWidget(self.plot_canvas[plot_canvas_index])

        import matplotlib
        matplotlib.rcParams['axes.formatter.useoffset']='False'

        if profile == 0:
            offset = int(peak_intensity*0.3)

        self.plot_canvas[plot_canvas_index].addCurve(bins, histogram + offset*profile, h_title, symbol='', color=color, xlabel=xtitle, ylabel=ytitle, replace=False) #'+', '^', ','

        self.plot_canvas[plot_canvas_index]._backend.ax.text(xrange[0]*factor*1.05, offset*profile*1.05, h_title)

        if not xtitle is None: self.plot_canvas[plot_canvas_index].setGraphXLabel(xtitle)
        if not ytitle is None: self.plot_canvas[plot_canvas_index].setGraphYLabel(ytitle)
        if not title is None:  self.plot_canvas[plot_canvas_index].setGraphTitle(title)

        for label in self.plot_canvas[plot_canvas_index]._backend.ax.yaxis.get_ticklabels():
            label.set_color('white')
            label.set_fontsize(1)

        self.plot_canvas[plot_canvas_index].setActiveCurveColor(color="#00008B")

        self.plot_canvas[plot_canvas_index].setDrawModeEnabled(True, 'rectangle')
        self.plot_canvas[plot_canvas_index].setInteractiveMode('zoom',color='orange')
        self.plot_canvas[plot_canvas_index].resetZoom()
        self.plot_canvas[plot_canvas_index].replot()

        self.plot_canvas[plot_canvas_index].setGraphXLimits(xrange[0]*factor, xrange[1]*factor)

        self.plot_canvas[plot_canvas_index].setActiveCurve(h_title)

        self.plot_canvas[plot_canvas_index].setDefaultPlotLines(True)
        self.plot_canvas[plot_canvas_index].setDefaultPlotPoints(False)

        self.plot_canvas[plot_canvas_index].getLegendsDockWidget().setFixedHeight(510)
        self.plot_canvas[plot_canvas_index].getLegendsDockWidget().setVisible(True)

        self.plot_canvas[plot_canvas_index].addDockWidget(Qt.RightDockWidgetArea, self.plot_canvas[plot_canvas_index].getLegendsDockWidget())

        self.progressBarSet(progressBarValue)

        return HistoData(histogram_stats, bins_stats, offset, xrange, sigma, peak_intensity)

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
            if len(self.current_histo_data_x_ff) > 0:
                self.write_histo_and_stats_file(histo_data=self.current_histo_data_x_ff,
                                                stats=self.current_stats_x_ff,
                                                suffix="_S_FF")

            if len(self.current_histo_data_x_nf) > 0:
                self.write_histo_and_stats_file(histo_data=self.current_histo_data_x_nf,
                                                stats=self.current_stats_x_nf,
                                                suffix="_S_NF")

            if len(self.current_histo_data_z_ff) > 0:
                self.write_histo_and_stats_file(histo_data=self.current_histo_data_z_ff,
                                                stats=self.current_stats_z_ff,
                                                suffix="_T_FF")

            if len(self.current_histo_data_z_nf) > 0:
                self.write_histo_and_stats_file(histo_data=self.current_histo_data_z_nf.bins,
                                                stats=self.current_stats_z_nf,
                                                suffix="_T_NF")

            QMessageBox.information(self, "Export Error Analysis Data", "Data saved into directory: " + output_folder, QMessageBox.Ok)


    def write_histo_and_stats_file(self, histo_data, stats, suffix="_T_FF"):

        profile_number = 0

        for data in histo_data:
            positions = data[0][:]
            intensities = data[1][:]

            file = open("histogram_profile_" + str(profile_number) + suffix + ".dat", "w")

            for position, intensity in zip(positions, intensities):
                file.write(str(position) + "   " + str(intensity) + "\n")

            file.flush()
            file.close()

            profile_number += 1

        file_sigma = open("sigma" + suffix + ".dat", "w")
        file_peak_intensity = open("peak_intensity" + suffix + ".dat", "w")


        for profile_number, sigma, peak_intensity in zip(numpy.arange(0, len(stats[0])),
                                                         numpy.array(stats[0][:]),
                                                         numpy.array(stats[1][:])/stats[1][0]):
            file_sigma.write(str(profile_number) + "   " + str(sigma) + "\n")
            file_peak_intensity.write(str(profile_number) + "   " + str(peak_intensity) + "\n")

        file_sigma.flush()
        file_peak_intensity.close()


from matplotlib import pyplot as plt

class StatsPlotWindow(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent=parent)

        self.fig, self.ax1 = plt.subplots()
        self.ax2 = self.ax1.twinx()

        layout = QVBoxLayout()

        figure_canvas = FigureCanvas(self.fig)
        figure_canvas.setFixedWidth(700)
        figure_canvas.setFixedHeight(520)

        layout.addWidget(NavigationToolbar(figure_canvas, self))
        layout.addWidget(figure_canvas)

        self.setLayout(layout)

    def plotCurves(self, x, y1, y2, xlabel, ylabel1, ylabel2):
        self.ax1.clear()
        self.ax2.clear()

        self.ax1.plot(x, y1, "b.-")
        self.ax1.set_xlabel(xlabel)
        self.ax1.set_ylabel(ylabel1, color="b")
        self.ax2.plot(x, y2, "r.-")
        self.ax2.set_ylabel(ylabel2, color="r")

        self.fig.tight_layout()

class StatsPlotWindow2(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent=parent)

        self.plotWindow = oasysgui.plotWindow(parent=None,
                                              backend=None,
                                              resetzoom=False,
                                              autoScale=False,
                                              logScale=False,
                                              grid=True,
                                              curveStyle=False,
                                              colormap=False,
                                              aspectRatio=False,
                                              yInverted=False,
                                              copy=False,
                                              save=True,
                                              print_=True,
                                              control=True,
                                              position=False,
                                              roi=False,
                                              mask=False,
                                              fit=False)
        self.plotWindow.setFixedWidth(700)
        self.plotWindow.setFixedHeight(520)

        self.plotWindow.setDefaultPlotLines(True)
        self.plotWindow.setDefaultPlotPoints(True)

        self.ax2 = self.plotWindow._backend.ax.twinx()

        layout = QVBoxLayout()

        layout.addWidget(self.plotWindow)

        self.setLayout(layout)

    def plotCurves(self, x, y1, y2, title, xlabel, ylabel1, ylabel2):
        self.plotWindow._backend.ax.clear()
        self.ax2.clear()

        self.plotWindow.addCurve(x, y1, replace=False, color="b", symbol=".", ylabel=ylabel1, linewidth=1.5)
        self.plotWindow.setGraphXLabel(xlabel)
        self.plotWindow.setGraphTitle(title)
        self.plotWindow._backend.ax.set_ylabel(ylabel1, color="b")

        self.ax2.plot(x, y2, "r.-")
        self.ax2.set_ylabel(ylabel2, color="r")
