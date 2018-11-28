import sys
import os
import time
import copy
import numpy

from PyQt5 import QtGui, QtWidgets
from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog
from oasys.util.oasys_util import EmittingStream, TTYGrabber

from orangecontrib.srw.util.srw_util import SRWPlot
from orangecontrib.srw.util.srw_objects import SRWData
from orangecontrib.srw.widgets.gui.ow_srw_widget import SRWWidget

from orangecontrib.aps.util.gui import StatisticalDataCollection, HistogramDataCollection, DoublePlotWidget, write_histo_and_stats_file
from orangecontrib.aps.srw.util.gui import ScanHistoWidget, Scan3DHistoWidget, Column

from wofrysrw.propagator.wavefront2D.srw_wavefront import PolarizationComponent, TypeOfDependence

TO_UM = 1e6

class Histogram(SRWWidget):
    name = "Scanning Variable Histogram"
    description = "Display Data Tools: Histogram"
    icon = "icons/histogram.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 1
    category = "Display Data Tools"
    keywords = ["data", "file", "load", "read"]

    inputs = [("SRWData", SRWData, "set_input")]

    IMAGE_WIDTH = 878
    IMAGE_HEIGHT = 635

    want_main_area=1
    plot_canvas=None
    plot_scan_canvas=None

    input_srw_data = None

    x_column_index=Setting(0)

    x_range=Setting(0)
    x_range_min=Setting(0.0)
    x_range_max=Setting(0.0)

    polarization_component_to_be_extracted=Setting(0)
    multi_electron = Setting(0)

    title=Setting("Y")

    iterative_mode = Setting(0)

    last_ticket=None

    current_histo_data = None
    current_stats = None
    last_histo_data = None
    histo_index = -1

    plot_type = Setting(1)
    add_labels=Setting(0)
    has_colormap=Setting(1)
    plot_type_3D = Setting(0)
    stats_to_plot = Setting(0)

    def __init__(self):
        super().__init__()

        self.refresh_button = gui.button(self.controlArea, self, "Refresh", callback=self.plot_results, height=45, width=400)
        gui.separator(self.controlArea, 10)

        self.tabs_setting = oasysgui.tabWidget(self.controlArea)
        self.tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        # graph tab
        tab_set = oasysgui.createTabPage(self.tabs_setting, "Plot Settings")
        tab_gen = oasysgui.createTabPage(self.tabs_setting, "Histogram Settings")

        general_box = oasysgui.widgetBox(tab_set, "General Settings", addSpace=True, orientation="vertical", height=250, width=390)

        self.x_column = gui.comboBox(general_box, self, "x_column_index", label="Intensity Cut", labelWidth=250,
                                     items=["Horizontal", "Vertical"],
                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "x_range", label="Position Range", labelWidth=250,
                                     items=["<Default>",
                                            "Set.."],
                                     callback=self.set_XRange, sendSelectedValue=False, orientation="horizontal")

        self.xrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)
        self.xrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)

        oasysgui.lineEdit(self.xrange_box, self, "x_range_min", "Min [\u03bcm]", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.xrange_box, self, "x_range_max", "Max [\u03bcm]", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_XRange()

        gui.comboBox(general_box, self, "polarization_component_to_be_extracted", label="Polarization Component", labelWidth=250,
                                     items=["Total", "\u03c3", "\u03c0"],
                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "multi_electron", label="Multi Electron (Convolution)", labelWidth=250,
                                     items=["No", "Yes"],
                                     sendSelectedValue=False, orientation="horizontal")

        incremental_box = oasysgui.widgetBox(tab_gen, "Incremental Result", addSpace=True, orientation="vertical", height=260)

        gui.button(incremental_box, self, "Clear Stored Data", callback=self.clearResults, height=30)
        gui.separator(incremental_box)

        gui.comboBox(incremental_box, self, "iterative_mode", label="Iterative Mode", labelWidth=250,
                                         items=["None", "Accumulating", "Scanning"],
                                         sendSelectedValue=False, orientation="horizontal", callback=self.set_IterativeMode)

        self.box_scan_empty = oasysgui.widgetBox(incremental_box, "", addSpace=False, orientation="vertical")
        self.box_scan = oasysgui.widgetBox(incremental_box, "", addSpace=False, orientation="vertical")

        gui.comboBox(self.box_scan, self, "plot_type", label="Plot Type", labelWidth=310,
                     items=["2D", "3D"],
                     sendSelectedValue=False, orientation="horizontal", callback=self.set_PlotType)

        self.box_pt_1 = oasysgui.widgetBox(self.box_scan, "", addSpace=False, orientation="vertical", height=25)

        gui.comboBox(self.box_pt_1, self, "add_labels", label="Add Labels (Variable Name/Value)", labelWidth=310,
                     items=["No", "Yes"],
                     sendSelectedValue=False, orientation="horizontal")

        self.box_pt_2 = oasysgui.widgetBox(self.box_scan, "", addSpace=False, orientation="vertical", height=25)

        gui.comboBox(self.box_pt_2, self, "plot_type_3D", label="3D Plot Aspect", labelWidth=310,
                     items=["Lines", "Surface"],
                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(self.box_scan, self, "has_colormap", label="Colormap", labelWidth=310,
                     items=["No", "Yes"],
                     sendSelectedValue=False, orientation="horizontal")

        gui.separator(self.box_scan)

        gui.comboBox(self.box_scan, self, "stats_to_plot", label="Stats: Spot Dimension", labelWidth=310,
                     items=["Sigma", "FWHM"],
                     sendSelectedValue=False, orientation="horizontal")

        gui.button(self.box_scan, self, "Export Scanning Results & Stats", callback=self.export_scanning_stats_analysis, height=30)

        self.set_IterativeMode()

        self.main_tabs = oasysgui.tabWidget(self.mainArea)
        plot_tab = oasysgui.createTabPage(self.main_tabs, "Plots")
        plot_tab_stats = oasysgui.createTabPage(self.main_tabs, "Stats")
        out_tab = oasysgui.createTabPage(self.main_tabs, "Output")

        self.image_box = gui.widgetBox(plot_tab, "Plot Result", addSpace=True, orientation="vertical")
        self.image_box.setFixedHeight(self.IMAGE_HEIGHT)
        self.image_box.setFixedWidth(self.IMAGE_WIDTH)

        self.image_box_stats = gui.widgetBox(plot_tab_stats, "Stats Result", addSpace=True, orientation="vertical")
        self.image_box_stats.setFixedHeight(self.IMAGE_HEIGHT)
        self.image_box_stats.setFixedWidth(self.IMAGE_WIDTH)

        self.shadow_output = oasysgui.textArea(height=580, width=800)

        out_box = gui.widgetBox(out_tab, "System Output", addSpace=True, orientation="horizontal")
        out_box.layout().addWidget(self.shadow_output)

    def clearResults(self):
        if ConfirmDialog.confirmed(parent=self):
            self.clear_data()

    def clear_data(self):
        self.input_srw_data = None
        self.last_ticket = None
        self.current_stats = None
        self.current_histo_data = None
        self.last_histo_data = None

        self.histo_index = -1

        if not self.plot_canvas is None:
            self.main_tabs.removeTab(1)
            self.main_tabs.removeTab(0)

            plot_tab = oasysgui.widgetBox(self.main_tabs, addToLayout=0, margin=4)

            self.image_box = gui.widgetBox(plot_tab, "Plot Result", addSpace=True, orientation="vertical")
            self.image_box.setFixedHeight(self.IMAGE_HEIGHT)
            self.image_box.setFixedWidth(self.IMAGE_WIDTH)

            plot_tab_stats = oasysgui.widgetBox(self.main_tabs, addToLayout=0, margin=4)

            self.image_box_stats = gui.widgetBox(plot_tab_stats, "Stats Result", addSpace=True, orientation="vertical")
            self.image_box_stats.setFixedHeight(self.IMAGE_HEIGHT)
            self.image_box_stats.setFixedWidth(self.IMAGE_WIDTH)

            self.main_tabs.insertTab(0, plot_tab_stats, "TEMP")
            self.main_tabs.setTabText(0, "Stats")
            self.main_tabs.insertTab(0, plot_tab, "TEMP")
            self.main_tabs.setTabText(0, "Plots")
            self.main_tabs.setCurrentIndex(0)

            self.plot_canvas = None
            self.plot_canvas_stats = None

    def set_IterativeMode(self):
        self.box_scan_empty.setVisible(self.iterative_mode<2)
        if self.iterative_mode==2:
            self.box_scan.setVisible(True)
            self.refresh_button.setEnabled(False)
            self.set_PlotType()
        else:
            self.box_scan.setVisible(False)
            self.refresh_button.setEnabled(True)

        self.clear_data()

    def set_PlotType(self):
        self.plot_canvas = None
        self.plot_canvas_stats = None

        self.box_pt_1.setVisible(self.plot_type==0)
        self.box_pt_2.setVisible(self.plot_type==1)

    def set_XRange(self):
        self.xrange_box.setVisible(self.x_range == 1)
        self.xrange_box_empty.setVisible(self.x_range == 0)

    def replace_fig(self, wavefront, var, xrange, title, xtitle, ytitle, xum):
        if self.plot_canvas is None:
            if self.iterative_mode < 2:
                self.plot_canvas = SRWPlot.Detailed1DWidget(y_scale_factor=1.14)
            else:
                if self.plot_type == 0:
                    self.plot_canvas = ScanHistoWidget()
                elif self.plot_type==1:
                    self.plot_canvas = Scan3DHistoWidget(type=Scan3DHistoWidget.PlotType.LINES if self.plot_type_3D==0 else Scan3DHistoWidget.PlotType.SURFACE)

                self.plot_canvas_stats = DoublePlotWidget(parent=None)
                self.image_box_stats.layout().addWidget(self.plot_canvas_stats)

            self.image_box.layout().addWidget(self.plot_canvas)

        if self.polarization_component_to_be_extracted == 0:
            polarization_component_to_be_extracted = PolarizationComponent.TOTAL
        elif self.polarization_component_to_be_extracted == 1:
            polarization_component_to_be_extracted = PolarizationComponent.LINEAR_HORIZONTAL
        elif self.polarization_component_to_be_extracted == 2:
            polarization_component_to_be_extracted = PolarizationComponent.LINEAR_VERTICAL

        e, h, v, i = wavefront.get_intensity(multi_electron=self.multi_electron==1,
                                            polarization_component_to_be_extracted=polarization_component_to_be_extracted,
                                            type_of_dependence=TypeOfDependence.VS_XY)

        ticket2D = SRWPlot.get_ticket_2D(h, v, i[int(e.size/2)])

        ticket = {}
        if var == Column.X:
            ticket["histogram"] = ticket2D["histogram_h"]
            ticket["bins"] = ticket2D["bin_h"]*TO_UM
            ticket["xrange"] = ticket2D["xrange"]
            ticket["fwhm"] = ticket2D["fwhm_h"]*TO_UM
            ticket["fwhm_coordinates"] = ticket2D["fwhm_coordinates_h"]
        elif var == Column.Y:
            ticket["histogram"] = ticket2D["histogram_v"]
            ticket["bins"] = ticket2D["bin_v"]*TO_UM
            ticket["xrange"] = ticket2D["yrange"]
            ticket["fwhm"] = ticket2D["fwhm_v"]*TO_UM
            ticket["fwhm_coordinates"] = ticket2D["fwhm_coordinates_v"]

        ticket["xrange"] = (ticket["xrange"][0]*TO_UM, ticket["xrange"][1]*TO_UM)

        if not ticket["fwhm"] is None and not ticket["fwhm"] == 0.0:
            ticket["fwhm_coordinates"] = (ticket["fwhm_coordinates"][0]*TO_UM, ticket["fwhm_coordinates"][1]*TO_UM)

        try:
            if self.iterative_mode==0:
                self.last_ticket = None
                self.current_histo_data = None
                self.current_stats = None
                self.last_histo_data = None
                self.histo_index = -1

                self.plot_canvas.plot_1D(ticket, var, title, xtitle, ytitle, xum, xrange, use_default_factor=False)
            elif self.iterative_mode == 1:
                self.current_histo_data = None
                self.current_stats = None
                self.last_histo_data = None
                self.histo_index = -1

                ticket['histogram'] += self.last_ticket['histogram']

                self.plot_canvas.plot_1D(ticket, var, title, xtitle, ytitle, xum, xrange, use_default_factor=False)

                self.last_ticket = ticket
            else:
                if not wavefront.scanned_variable_data is None:
                    self.last_ticket = None
                    self.histo_index += 1
                    histo_data = self.plot_canvas.plot_histo(ticket,
                                                             col=var,
                                                             title=title,
                                                             xtitle=xtitle,
                                                             ytitle=ytitle,
                                                             histo_index=self.histo_index,
                                                             scan_variable_name=wavefront.scanned_variable_data.get_scanned_variable_display_name() + " [" + wavefront.scanned_variable_data.get_scanned_variable_um() + "]",
                                                             scan_variable_value=wavefront.scanned_variable_data.get_scanned_variable_value(),
                                                             offset=0.0 if self.last_histo_data is None else self.last_histo_data.offset,
                                                             xrange=xrange,
                                                             show_reference=False,
                                                             add_labels=self.add_labels==1,
                                                             has_colormap=self.has_colormap==1,
                                                             use_default_factor=False
                                                             )
                    histo_data.scan_value=wavefront.scanned_variable_data.get_scanned_variable_value()

                    if not histo_data.bins is None:
                        if self.current_histo_data is None:
                            self.current_histo_data = HistogramDataCollection(histo_data)
                        else:
                            self.current_histo_data.add_histogram_data(histo_data)

                    if self.current_stats is None:
                        self.current_stats = StatisticalDataCollection(histo_data)
                    else:
                        self.current_stats.add_statistical_data(histo_data)

                    self.last_histo_data = histo_data

                    self.plot_canvas_stats.plotCurves(self.current_stats.get_scan_values(),
                                                      self.current_stats.get_sigmas() if self.stats_to_plot==0 else self.current_stats.get_fwhms(),
                                                      self.current_stats.get_relative_intensities(),
                                                      "Statistics",
                                                      wavefront.scanned_variable_data.get_scanned_variable_display_name() + " [" + wavefront.scanned_variable_data.get_scanned_variable_um() + "]",
                                                      "Sigma " + xum if self.stats_to_plot==0 else "FWHM " + xum,
                                                      "Relative Peak Intensity")


        except Exception as e:
            if self.IS_DEVELOP: raise e
            else: raise Exception("Data not plottable: No good rays or bad content")

    def plot_histo(self, var_x, title, xtitle, ytitle, xum):
        wavefront_to_plot = self.input_srw_data.get_srw_wavefront()

        xrange = self.get_range(wavefront_to_plot, var_x)

        self.replace_fig(wavefront_to_plot, var_x, xrange, title, xtitle, ytitle, xum)

    def get_range(self, wavefront_to_plot, var_x):
        if self.x_range == 0 :
            if var_x == 1: # horizontal
                x_max = wavefront_to_plot.mesh.xFin
                x_min = wavefront_to_plot.mesh.xStart
            else:
                x_max = wavefront_to_plot.mesh.yFin
                x_min = wavefront_to_plot.mesh.yStart

            xrange = [x_min*TO_UM, x_max*TO_UM]
        else:
            congruence.checkLessThan(self.x_range_min, self.x_range_max, "Range min", "Range max")

            xrange = [self.x_range_min, self.x_range_max]

        return xrange

    def plot_results(self):
        try:
            plotted = False

            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            if not self.input_srw_data is None:
                x, title, x_title, y_title, xum = self.get_titles()

                self.plot_histo(x, title=title, xtitle=x_title, ytitle=y_title, xum=xum)

                plotted = True

            time.sleep(0.5)  # prevents a misterious dead lock in the Orange cycle when refreshing the histogram

            return plotted
        except Exception as exception:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       str(exception),
                                       QtWidgets.QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

            return False

    def get_titles(self):
        auto_title = self.x_column.currentText()

        xum = "[\u03bcm]"
        x_title = auto_title + " Position " + xum
        title = auto_title + " Cut"
        x = self.x_column_index + 1

        me = " ME " if self.multi_electron else " SE "

        if self.polarization_component_to_be_extracted == 0:
            y_title = "Intensity" + me + "[ph/s/.1%bw/mm\u00b2]"
        elif self.polarization_component_to_be_extracted == 1:
            y_title = "Intensity" + me + "\u03c3 [ph/s/.1%bw/mm\u00b2]"
        else:
            y_title = "Intensity" + me + "\u03c0 [ph/s/.1%bw/mm\u00b2]"

        return x, title, x_title, y_title, xum

    def set_input(self, srw_data):
        if not srw_data is None:
            self.input_srw_data = srw_data

            if self.is_automatic_run:
                self.plot_results()
        else:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       "Data not displayable: no input data",
                                       QtWidgets.QMessageBox.Ok)


    def writeStdOut(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

    def export_scanning_stats_analysis(self):

        output_folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select Output Directory", directory=os.curdir)

        if output_folder:
            if not self.current_histo_data is None:
                write_histo_and_stats_file(histo_data=self.current_histo_data,
                                           stats=self.current_stats,
                                           suffix="",
                                           output_folder=output_folder)


            QtWidgets.QMessageBox.information(self, "Export Scanning Results/Stats", "Data saved into directory: " + output_folder, QtWidgets.QMessageBox.Ok)
