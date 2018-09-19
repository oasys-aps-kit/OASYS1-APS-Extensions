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
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QMessageBox, QFileDialog

from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.shadow.widgets.special_elements import hybrid_control

from silx.gui.plot.ImageView import ImageView

class HistoData(object):
    offset = 0.0
    xrange = None
    sigma = 0.0
    peak_intensity = 0.0

    def __init__(self, offset=0.0, xrange=None, sigma=0.0, peak_intensity=0.0):
        self.offset = offset
        self.xrange = xrange
        self.sigma = sigma
        self.peak_intensity = peak_intensity

    def get_centroid(self):
        return self.xrange[0] + (self.xrange[1] - self.xrange[0])*0.5

class HybridScreenErrorAnalysis(AutomaticElement):

    inputs = [("Input Beam", ShadowBeam, "setBeam"),]

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

    file_to_write_out = Setting(0)

    ghy_automatic = Setting(1)

    files_area = None
    ghy_files = Setting([""])

    input_beam = None

    TABS_AREA_HEIGHT = 560
    CONTROL_AREA_WIDTH = 405

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 545

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
        self.files_area.setReadOnly(True)

        text = ""
        for file in self.ghy_files:
            text += file + "\n"
        self.files_area.setText(text)

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

        adv_other_box = oasysgui.widgetBox(tab_bas, "Optional file output", addSpace=False, orientation="vertical")

        gui.comboBox(adv_other_box, self, "file_to_write_out", label="Files to write out", labelWidth=220,
                     items=["None", "Debug (star.xx)"],
                     sendSelectedValue=False,
                     orientation="horizontal")

        self.shadow_output = oasysgui.textArea(height=600, width=600)

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
            text = ""
            for file in self.ghy_files:
                text += file + "\n"
            self.files_area.setText(text)

    def initializeTabs(self):
        self.tabs.clear()

        if self.ghy_diff_plane < 2:
            if self.ghy_nf == 1:
                self.tab = [gui.createTabPage(self.tabs, "Distribution of Position at Image Plane"),
                            gui.createTabPage(self.tabs, "Distribution of Position at Near Field")
                            ]
            else:
                self.tab = [gui.createTabPage(self.tabs, "Distribution of Position at Image Plane")]
        elif self.ghy_diff_plane == 2:
             self.tab = [gui.createTabPage(self.tabs, "Distribution of Position at Image Plane")]
        elif self.ghy_diff_plane == 3:
            if self.ghy_nf == 1:
                self.tab = [gui.createTabPage(self.tabs, "Distribution of Position at Near Field"),
                            gui.createTabPage(self.tabs, "Distribution of Position at Image Plane")
                            ]
            else:
                self.tab = [gui.createTabPage(self.tabs, "Distribution of Position at Image Plane")
                            ]

        for tab in self.tab:
            tab.setFixedHeight(self.IMAGE_HEIGHT)
            tab.setFixedWidth(self.IMAGE_WIDTH)

        self.plot_canvas = [None, None]


    def plot_emtpy(self, progressBarValue, plot_canvas_index):
        if self.plot_canvas[plot_canvas_index] is None:
            widget = QWidget()
            widget.setLayout(QHBoxLayout())
            label = QLabel(widget)
            label.setPixmap(QPixmap(QImage(os.path.join(resources.package_dirname("orangecontrib.shadow.widgets.special_elements"), "icons", "no_result.png"))))

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

        sigma = ticket['histogram_sigma']
        peak_intensity = numpy.max(histogram)

        if profile == 0:
            h_title = "Reference"
        else:
            h_title = "Profile #" + str(profile)

        hex_r = hex(min(255, 128 + profile*10))[2:].upper()
        hex_g = hex(min(255, 20 + profile*15))[2:].upper()
        hex_b = hex(min(255, profile*10))[2:].upper()
        if len(hex_r) == 1: hex_r = "0" + hex_r
        if len(hex_g) == 1: hex_g = "0" + hex_g
        if len(hex_b) == 1: hex_b = "0" + hex_b

        color="#" + hex_r + hex_g + hex_b

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
            self.plot_canvas[plot_canvas_index].setActiveCurveColor(color="#00008B")
            self.plot_canvas[plot_canvas_index].setGraphXLabel(xtitle)
            self.plot_canvas[plot_canvas_index].setGraphYLabel(ytitle)
            self.plot_canvas[plot_canvas_index].setGraphTitle(title)

            self.tab[plot_canvas_index].layout().addWidget(self.plot_canvas[plot_canvas_index])

        import matplotlib
        matplotlib.rcParams['axes.formatter.useoffset']='False'

        if profile == 0:
            offset = int(peak_intensity*0.3)

        self.plot_canvas[plot_canvas_index].addCurve(bins, histogram + offset*profile, h_title, symbol='', color=color, xlabel=xtitle, ylabel=ytitle, replace=False) #'+', '^', ','

        self.plot_canvas[plot_canvas_index]._backend.ax.text(xrange[0]*factor, offset*profile, h_title)

        if not xtitle is None: self.plot_canvas[plot_canvas_index].setGraphXLabel(xtitle)
        if not ytitle is None: self.plot_canvas[plot_canvas_index].setGraphYLabel(ytitle)

        self.plot_canvas[plot_canvas_index].setDrawModeEnabled(True, 'rectangle')
        self.plot_canvas[plot_canvas_index].setInteractiveMode('zoom',color='orange')
        self.plot_canvas[plot_canvas_index].resetZoom()
        self.plot_canvas[plot_canvas_index].replot()

        self.plot_canvas[plot_canvas_index].setGraphXLimits(xrange[0]*factor, xrange[1]*factor)

        self.plot_canvas[plot_canvas_index].setActiveCurve(h_title)

        self.progressBarSet(progressBarValue)

        self.plot_canvas[plot_canvas_index].setDefaultPlotLines(True)
        self.plot_canvas[plot_canvas_index].setDefaultPlotPoints(False)

        self.plot_canvas[plot_canvas_index].getLegendsDockWidget().setFixedHeight(150)
        self.plot_canvas[plot_canvas_index].getLegendsDockWidget().setVisible(True)
        self.plot_canvas[plot_canvas_index].getLegendsDockWidget().setFixedHeight(150)

        from PyQt5.QtCore import Qt
        self.plot_canvas[plot_canvas_index].addDockWidget(Qt.RightDockWidgetArea, self.plot_canvas[plot_canvas_index].getLegendsDockWidget())

        return HistoData(offset, xrange, sigma, peak_intensity)

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

                    centroid_x_ff = histo_data_x_ff.get_centroid()

                    input_parameters.ghy_calcType = self.ghy_calcType + 3

                    for file in self.ghy_files:
                        shadow_beam = self.input_beam.duplicate()

                        history_entry =  shadow_beam.getOEHistory(shadow_beam._oe_number)
                        shadow_oe = history_entry._shadow_oe_start # changes to the original object!

                        shadow_oe._oe.F_RIPPLE = 1
                        shadow_oe._oe.F_G_S = 2

                        shadow_oe._oe.FILE_RIP = bytes(congruence.checkFileName(file), 'utf-8')

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


                    self.plot_canvas[0].addCurve(numpy.array([histo_data_z_ff.get_centroid()]),
                                                 numpy.array([0]),
                                                     "Click on curve to highlight it",
                                                     xlabel="", ylabel="",
                                                     symbol='', color='white')

                    self.plot_canvas[0].setActiveCurve("Click on curve to highlight it")
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
                if do_nf:
                    histo_data_x_ff = self.plot_histo(calculation_parameters.ff_beam, 1, progressBarValue=88,
                                                  plot_canvas_index=0, title="X",
                                                  xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_x_ff.offset, xrange=histo_data_x_ff.xrange)
                    histo_data_x_nf = self.plot_histo(calculation_parameters.nf_beam, 1, progressBarValue=96,
                                                  plot_canvas_index=1, title="X",
                                                  xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_x_nf.offset, xrange=histo_data_x_nf.xrange)
                else:
                    histo_data_x_ff = self.plot_histo(calculation_parameters.ff_beam, 1, progressBarValue=88,
                                                  plot_canvas_index=0, title="X",
                                                  xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_x_ff.offset, xrange=histo_data_x_ff.xrange)
            else:
                if do_nf:
                    self.plot_emtpy(88, 0)
                    self.plot_emtpy(96, 1)
                else:
                    self.plot_emtpy(88, 0)
        elif self.ghy_diff_plane == 1:
            if do_plot_z:
                if do_nf:
                    histo_data_z_ff = self.plot_histo(calculation_parameters.ff_beam, 3, progressBarValue=88,
                                                  plot_canvas_index=0, title="Z",
                                                  xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_z_ff.offset, xrange=histo_data_z_ff.xrange)
                    histo_data_z_nf = self.plot_histo(calculation_parameters.nf_beam, 3, progressBarValue=96,
                                                  plot_canvas_index=1, title="Z",
                                                  xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_z_nf.offset, xrange=histo_data_z_nf.xrange)
                else:
                    histo_data_z_ff = self.plot_histo(calculation_parameters.ff_beam, 3, progressBarValue=88,
                                                  plot_canvas_index=0, title="Z",
                                                  xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays', profile=profile,
                                                  offset=histo_data_z_ff.offset, xrange=histo_data_z_ff.xrange)
            else:
                if do_nf:
                    self.plot_emtpy(88, 0)
                    self.plot_emtpy(96, 1)
                else:
                    self.plot_emtpy(88, 0)

        elif self.ghy_diff_plane == 2:
            if do_plot_x and do_plot_z:
                self.plot_xy(calculation_parameters.ff_beam, 1, 3, plot_canvas_index=0, title="X,Z",
                             xtitle=r'X [$\mu$m]', ytitle=r'Z [$\mu$m]')

            else:
                if do_plot_x:
                    self.plot_histo(calculation_parameters.ff_beam, 1, plot_canvas_index=0, title="X",
                                    xtitle=r'X [$\mu$m]', ytitle=r'Number of Rays')
                elif do_plot_z:
                    self.plot_histo(calculation_parameters.ff_beam, 3, plot_canvas_index=0, title="Z",
                                    xtitle=r'Z [$\mu$m]', ytitle=r'Number of Rays')
                else:
                    self.plot_emtpy(88, 0)

        elif self.ghy_diff_plane == 3:
            if (do_plot_x or do_plot_z):
                if do_nf:
                    self.plot_xy(calculation_parameters.nf_beam, 88, 1, 3, plot_canvas_index=0, title="X,Z",
                                 xtitle=r'X [$\mu$m]', ytitle=r'Z [$\mu$m]')
                    self.plot_xy(calculation_parameters.ff_beam, 96, 1, 3, plot_canvas_index=1, title="X,Z",
                                 xtitle=r'X [$\mu$m]', ytitle=r'Z [$\mu$m]')
                else:
                    self.plot_xy(calculation_parameters.ff_beam, 88, 1, 3, plot_canvas_index=0, title="X,Z",
                                 xtitle=r'X [$\mu$m]', ytitle=r'Z [$\mu$m]')
            else:
                if do_nf:
                    self.plot_emtpy(88, 4)
                    self.plot_emtpy(96, 5)
                else:
                    self.plot_emtpy(88, 0)

        return histo_data_x_ff, histo_data_z_ff, histo_data_x_nf, histo_data_z_nf

    def check_fields(self):
        if self.focal_length_calc == 1:
            congruence.checkPositiveNumber(self.ghy_focallength, "Focal Length value")

        if self.distance_to_image_calc == 1:
            congruence.checkPositiveNumber(self.ghy_distance, "Distance to image value")

        if self.ghy_diff_plane == 0 or self.ghy_diff_plane == 2:
            congruence.checkStrictlyPositiveNumber(self.ghy_nbins_x, "Number of bins for I(Sagittal) histogram")
        if self.ghy_diff_plane == 1 or self.ghy_diff_plane == 2:
            congruence.checkStrictlyPositiveNumber(self.ghy_nbins_z, "Number of bins for I(Tangential) histogram")

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

