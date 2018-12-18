import copy
import sys
import time

import numpy
from PyQt5 import QtGui, QtWidgets
from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog

from oasys.util.oasys_util import EmittingStream

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.aps.shadow.util.gui import PowerPlotXYWidget

class PowerPlotXY(AutomaticElement):

    name = "Power Plot XY"
    description = "Display Data Tools: Power Plot XY"
    icon = "icons/plot_xy.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "Display Data Tools"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    IMAGE_WIDTH = 878
    IMAGE_HEIGHT = 570

    want_main_area=1
    plot_canvas=None
    input_beam=None

    image_plane=Setting(0)
    image_plane_new_position=Setting(10.0)
    image_plane_rel_abs_position=Setting(0)

    x_column_index=Setting(0)
    y_column_index=Setting(2)

    x_range=Setting(0)
    x_range_min=Setting(0.0)
    x_range_max=Setting(0.0)

    y_range=Setting(0)
    y_range_min=Setting(0.0)
    y_range_max=Setting(0.0)

    rays=Setting(1)
    number_of_bins=Setting(100)

    title=Setting("X,Z")

    keep_result=Setting(0)
    last_ticket=None

    energy_min = None
    energy_max = None
    energy_step = None
    total_power = None
    cumulated_power = None

    view_type=Setting(1)

    def __init__(self):
        super().__init__(show_automatic_box=False)

        gui.button(self.controlArea, self, "Plot Cumulated Data", callback=self.plot_cumulated_data, height=45)

        gui.separator(self.controlArea, 10)

        self.tabs_setting = oasysgui.tabWidget(self.controlArea)
        self.tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-5)

        # graph tab
        tab_set = oasysgui.createTabPage(self.tabs_setting, "Plot Settings")
        tab_gen = oasysgui.createTabPage(self.tabs_setting, "Histogram Settings")

        screen_box = oasysgui.widgetBox(tab_set, "Screen Position Settings", addSpace=True, orientation="vertical", height=120)

        self.image_plane_combo = gui.comboBox(screen_box, self, "image_plane", label="Position of the Image",
                                            items=["On Image Plane", "Retraced"], labelWidth=260,
                                            callback=self.set_ImagePlane, sendSelectedValue=False, orientation="horizontal")

        self.image_plane_box = oasysgui.widgetBox(screen_box, "", addSpace=False, orientation="vertical", height=50)
        self.image_plane_box_empty = oasysgui.widgetBox(screen_box, "", addSpace=False, orientation="vertical", height=50)

        oasysgui.lineEdit(self.image_plane_box, self, "image_plane_new_position", "Image Plane new Position", labelWidth=220, valueType=float, orientation="horizontal")

        gui.comboBox(self.image_plane_box, self, "image_plane_rel_abs_position", label="Position Type", labelWidth=250,
                     items=["Absolute", "Relative"], sendSelectedValue=False, orientation="horizontal")

        self.set_ImagePlane()

        general_box = oasysgui.widgetBox(tab_set, "Variables Settings", addSpace=True, orientation="vertical", height=350)

        self.x_column = gui.comboBox(general_box, self, "x_column_index", label="X Column",labelWidth=70,
                                     items=["1: X",
                                            "2: Y",
                                            "3: Z",
                                     ],
                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "x_range", label="X Range", labelWidth=250,
                                     items=["<Default>",
                                            "Set.."],
                                     callback=self.set_XRange, sendSelectedValue=False, orientation="horizontal")

        self.xrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)
        self.xrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)

        oasysgui.lineEdit(self.xrange_box, self, "x_range_min", "X min", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.xrange_box, self, "x_range_max", "X max", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_XRange()

        self.y_column = gui.comboBox(general_box, self, "y_column_index", label="Y Column",labelWidth=70,
                                     items=["1: X",
                                            "2: Y",
                                            "3: Z",
                                     ],

                                     sendSelectedValue=False, orientation="horizontal")

        gui.comboBox(general_box, self, "y_range", label="Y Range",labelWidth=250,
                                     items=["<Default>",
                                            "Set.."],
                                     callback=self.set_YRange, sendSelectedValue=False, orientation="horizontal")

        self.yrange_box = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)
        self.yrange_box_empty = oasysgui.widgetBox(general_box, "", addSpace=True, orientation="vertical", height=100)

        oasysgui.lineEdit(self.yrange_box, self, "y_range_min", "Y min", labelWidth=220, valueType=float, orientation="horizontal")
        oasysgui.lineEdit(self.yrange_box, self, "y_range_max", "Y max", labelWidth=220, valueType=float, orientation="horizontal")

        self.set_YRange()

        self.cb_rays = gui.comboBox(general_box, self, "rays", label="Rays", labelWidth=250,
                                    items=["Transmitted", "Absorbed"],
                                    sendSelectedValue=False, orientation="horizontal")

        incremental_box = oasysgui.widgetBox(tab_gen, "Incremental Result", addSpace=True, orientation="horizontal", height=80)

        gui.checkBox(incremental_box, self, "keep_result", "Keep Result")
        gui.button(incremental_box, self, "Clear", callback=self.clearResults)

        histograms_box = oasysgui.widgetBox(tab_gen, "Histograms settings", addSpace=True, orientation="vertical", height=90)

        oasysgui.lineEdit(histograms_box, self, "number_of_bins", "Number of Bins", labelWidth=250, valueType=int, orientation="horizontal")

        self.main_tabs = oasysgui.tabWidget(self.mainArea)
        plot_tab = oasysgui.createTabPage(self.main_tabs, "Plots")
        out_tab = oasysgui.createTabPage(self.main_tabs, "Output")

        view_box = oasysgui.widgetBox(plot_tab, "Plotting", addSpace=False, orientation="vertical", width=self.IMAGE_WIDTH)
        view_box_1 = oasysgui.widgetBox(view_box, "", addSpace=False, orientation="vertical", width=350)

        gui.comboBox(view_box_1, self, "view_type", label="Plot Accumulated Results", labelWidth=320,
                     items=["No", "Yes"],  sendSelectedValue=False, orientation="horizontal")

        self.image_box = gui.widgetBox(plot_tab, "Plot Result", addSpace=True, orientation="vertical")
        self.image_box.setFixedHeight(self.IMAGE_HEIGHT)
        self.image_box.setFixedWidth(self.IMAGE_WIDTH)

        self.shadow_output = oasysgui.textArea(height=580, width=800)

        out_box = gui.widgetBox(out_tab, "System Output", addSpace=True, orientation="horizontal")
        out_box.layout().addWidget(self.shadow_output)

    def clearResults(self, interactive=True):
        if not interactive: proceed = True
        else: proceed = ConfirmDialog.confirmed(parent=self)

        if proceed:
            self.input_beam = None
            self.last_ticket = None
            self.energy_min = None
            self.energy_max = None
            self.energy_step = None
            self.total_power = None
            self.cumulated_power = None

            if not self.plot_canvas is None:
                self.plot_canvas.clear()

    def set_ImagePlane(self):
        self.image_plane_box.setVisible(self.image_plane==1)
        self.image_plane_box_empty.setVisible(self.image_plane==0)

    def set_XRange(self):
        self.xrange_box.setVisible(self.x_range == 1)
        self.xrange_box_empty.setVisible(self.x_range == 0)

    def set_YRange(self):
        self.yrange_box.setVisible(self.y_range == 1)
        self.yrange_box_empty.setVisible(self.y_range == 0)

    def replace_fig(self, shadow_beam, var_x, var_y, xrange, yrange, nbins, nolost):
        if self.plot_canvas is None:
            self.plot_canvas = PowerPlotXYWidget()
            self.image_box.layout().addWidget(self.plot_canvas)

        try:
            if self.keep_result == 1:
                    self.last_ticket = self.plot_canvas.plot_power_density(shadow_beam, var_x, var_y,
                                                                           self.total_power, self.cumulated_power, self.energy_min, self.energy_max, self.energy_step,
                                                                           nbins=nbins, xrange=xrange, yrange=yrange, nolost=nolost,
                                                                           ticket_to_add=self.last_ticket, to_mm=self.workspace_units_to_mm, show_image=self.view_type==1)
            else:
                self.last_ticket = None
                self.plot_canvas.plot_power_density(shadow_beam, var_x, var_y,
                                                    self.total_power, self.cumulated_power, self.energy_min, self.energy_max, self.energy_step,
                                                    nbins=nbins, xrange=xrange, yrange=yrange, nolost=nolost, to_mm=self.workspace_units_to_mm, show_image=self.view_type==1)

        except Exception as e:
            raise Exception("Data not plottable: No good rays or bad content: " + str(e))

    def plot_xy(self, var_x, var_y):
        beam_to_plot = self.input_beam

        if self.image_plane == 1:
            new_shadow_beam = self.input_beam.duplicate(history=False)

            if self.image_plane_rel_abs_position == 1:  # relative
                dist = self.image_plane_new_position
            else:  # absolute
                if self.input_beam.historySize() == 0:
                    historyItem = None
                else:
                    historyItem = self.input_beam.getOEHistory(oe_number=self.input_beam._oe_number)

                if historyItem is None: image_plane = 0.0
                elif self.input_beam._oe_number == 0: image_plane = 0.0
                else: image_plane = historyItem._shadow_oe_end._oe.T_IMAGE

                dist = self.image_plane_new_position - image_plane

            self.retrace_beam(new_shadow_beam, dist)

            beam_to_plot = new_shadow_beam

        xrange, yrange = self.get_ranges()

        self.replace_fig(beam_to_plot, var_x, var_y, xrange=xrange, yrange=yrange, nbins=int(self.number_of_bins), nolost=self.rays+1)

    def get_ranges(self):
        xrange = None
        yrange = None
        factor1 = self.workspace_units_to_mm
        factor2 = self.workspace_units_to_mm

        if self.x_range == 1:
            congruence.checkLessThan(self.x_range_min, self.x_range_max, "X range min", "X range max")

            xrange = [self.x_range_min / factor1, self.x_range_max / factor1]

        if self.y_range == 1:
            congruence.checkLessThan(self.y_range_min, self.y_range_max, "Y range min", "Y range max")

            yrange = [self.y_range_min / factor2, self.y_range_max / factor2]

        return xrange, yrange

    def plot_cumulated_data(self):
        if not self.last_ticket is None:
            self.plot_canvas.plot_power_density_ticket(ticket=self.last_ticket,
                                                       var_x=self.x_column_index+1,
                                                       var_y=self.y_column_index+1,
                                                       cumulated_power=self.cumulated_power,
                                                       energy_min=self.energy_min,
                                                       energy_max=self.energy_max,
                                                       energy_step=self.energy_step,
                                                       show_image=self.view_type==1)

    def plot_results(self):
        try:
            sys.stdout = EmittingStream(textWritten=self.writeStdOut)

            if ShadowCongruence.checkEmptyBeam(self.input_beam):
                self.number_of_bins = congruence.checkStrictlyPositiveNumber(self.number_of_bins, "Number of Bins")

                self.plot_xy(self.x_column_index+1, self.y_column_index+1)

            time.sleep(0.1)  # prevents a misterious dead lock in the Orange cycle when refreshing the histogram
        except Exception as exception:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       str(exception),
                                       QtWidgets.QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def setBeam(self, input_beam):
        self.cb_rays.setEnabled(True)

        if not input_beam is None:
            if not input_beam.scanned_variable_data is None and input_beam.scanned_variable_data.has_additional_parameter("total_power"):
                self.input_beam = input_beam

                self.total_power = self.input_beam.scanned_variable_data.get_additional_parameter("total_power")

                if self.energy_min is None:
                    self.energy_min  = self.input_beam.scanned_variable_data.get_scanned_variable_value()
                    self.energy_step = self.input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")
                    self.cumulated_power = self.total_power
                else:
                    self.cumulated_power += self.total_power

                self.energy_max  = self.input_beam.scanned_variable_data.get_scanned_variable_value()

                if self.input_beam.scanned_variable_data.has_additional_parameter("is_footprint"):
                    if self.input_beam.scanned_variable_data.get_additional_parameter("is_footprint"):
                        self.cb_rays.setEnabled(False)
                        self.rays = 0 # transmitted, absorbed doesn't make sense since is precalculated by footprint object
                    else:
                        self.cb_rays.setEnabled(True)

                if ShadowCongruence.checkEmptyBeam(input_beam):
                    if ShadowCongruence.checkGoodBeam(input_beam):
                        self.plot_results()

    def writeStdOut(self, text):
        cursor = self.shadow_output.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        cursor.insertText(text)
        self.shadow_output.setTextCursor(cursor)
        self.shadow_output.ensureCursorVisible()

    def retrace_beam(self, new_shadow_beam, dist):
            new_shadow_beam._beam.retrace(dist)
