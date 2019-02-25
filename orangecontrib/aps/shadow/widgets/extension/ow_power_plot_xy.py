import sys
import time

from PyQt5 import QtGui, QtWidgets
from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.widgets.gui import ConfirmDialog

from oasys.util.oasys_util import EmittingStream

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence, ShadowPlot
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement
from orangecontrib.aps.shadow.util.gui import PowerPlotXYWidget

class PowerPlotXY(AutomaticElement):

    name = "Power Plot XY"
    description = "Display Data Tools: Power Plot XY"
    icon = "icons/plot_xy_power.png"
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

    keep_result=Setting(1)
    autosave_partial_results = Setting(0)

    autosave = Setting(0)
    autosave_file_name = Setting("autosave_power_density.hdf5")


    replace_poor_statistic = Setting(0)
    good_rays_limit = Setting(100)
    sigma_x = Setting(0.0)
    sigma_y = Setting(0.0)

    cumulated_ticket=None
    plotted_ticket   = None
    energy_min = None
    energy_max = None
    energy_step = None
    total_power = None
    cumulated_total_power = None

    view_type=Setting(1)

    autosave_file = None

    def __init__(self):
        super().__init__(show_automatic_box=False)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        gui.button(button_box, self, "Plot Cumulated Data", callback=self.plot_cumulated_data, height=45)
        gui.button(button_box, self, "Save Current Plot", callback=self.save_cumulated_data, height=45)

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

        autosave_box = oasysgui.widgetBox(tab_gen, "Autosave", addSpace=True, orientation="vertical", height=85)

        gui.comboBox(autosave_box, self, "autosave", label="Save automatically plot into file", labelWidth=250,
                                         items=["No", "Yes"],
                                         sendSelectedValue=False, orientation="horizontal", callback=self.set_autosave)

        self.autosave_box_1 = oasysgui.widgetBox(autosave_box, "", addSpace=False, orientation="horizontal", height=25)
        self.autosave_box_2 = oasysgui.widgetBox(autosave_box, "", addSpace=False, orientation="horizontal", height=25)

        self.le_autosave_file_name = oasysgui.lineEdit(self.autosave_box_1, self, "autosave_file_name", "File Name", labelWidth=100,  valueType=str, orientation="horizontal")

        gui.button(self.autosave_box_1, self, "...", callback=self.selectAutosaveFile)

        incremental_box = oasysgui.widgetBox(tab_gen, "Incremental Result", addSpace=True, orientation="vertical", height=120)

        gui.comboBox(incremental_box, self, "keep_result", label="Keep Result", labelWidth=250,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal", callback=self.set_autosave)

        self.cb_autosave_partial_results = gui.comboBox(incremental_box, self, "autosave_partial_results", label="Save partial plots into file", labelWidth=250,
                                                        items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        gui.button(incremental_box, self, "Clear", callback=self.clearResults)

        self.set_autosave()

        histograms_box = oasysgui.widgetBox(tab_gen, "Histograms settings", addSpace=True, orientation="vertical", height=200)

        oasysgui.lineEdit(histograms_box, self, "number_of_bins", "Number of Bins", labelWidth=250, valueType=int, orientation="horizontal")

        gui.separator(histograms_box)

        gui.comboBox(histograms_box, self, "replace_poor_statistic", label="Manage Poor Statistics", labelWidth=250,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal", callback=self.set_manage_poor_statistics)


        self.poor_statistics_box_1 = oasysgui.widgetBox(histograms_box, "", addSpace=False, orientation="vertical", height=100)
        self.poor_statistics_box_2 = oasysgui.widgetBox(histograms_box, "", addSpace=False, orientation="vertical", height=100)

        self.le_autosave_file_name = oasysgui.lineEdit(self.poor_statistics_box_1, self, "good_rays_limit", "Good Rays Limit", labelWidth=100,  valueType=int, orientation="horizontal")
        oasysgui.widgetLabel(self.poor_statistics_box_1, "Distribute Power on a Gaussian:")
        self.le_sigma_x = oasysgui.lineEdit(self.poor_statistics_box_1, self, "sigma_x", "Sigma H", labelWidth=100,  valueType=float, orientation="horizontal")
        self.le_sigma_y = oasysgui.lineEdit(self.poor_statistics_box_1, self, "sigma_y", "Sigma V", labelWidth=100,  valueType=float, orientation="horizontal")

        self.set_manage_poor_statistics()

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
            self.cumulated_ticket = None
            self.plotted_ticket = None
            self.energy_min = None
            self.energy_max = None
            self.energy_step = None
            self.total_power = None
            self.cumulated_total_power = None

            if not self.autosave_file is None:
                self.autosave_file.close()
                self.autosave_file = None

            if not self.plot_canvas is None:
                self.plot_canvas.clear()

    def set_manage_poor_statistics(self):
        self.poor_statistics_box_1.setVisible(self.replace_poor_statistic==1)
        self.poor_statistics_box_2.setVisible(self.replace_poor_statistic==0)

    def set_autosave(self):
        self.autosave_box_1.setVisible(self.autosave==1)
        self.autosave_box_2.setVisible(self.autosave==0)

        self.cb_autosave_partial_results.setEnabled(self.autosave==1 and self.keep_result==1)

    def set_ImagePlane(self):
        self.image_plane_box.setVisible(self.image_plane==1)
        self.image_plane_box_empty.setVisible(self.image_plane==0)

    def set_XRange(self):
        self.xrange_box.setVisible(self.x_range == 1)
        self.xrange_box_empty.setVisible(self.x_range == 0)

    def set_YRange(self):
        self.yrange_box.setVisible(self.y_range == 1)
        self.yrange_box_empty.setVisible(self.y_range == 0)

    def selectAutosaveFile(self):
        self.le_autosave_file_name.setText(oasysgui.selectFileFromDialog(self, self.autosave_file_name, "Select File", file_extension_filter="HDF5 Files (*.hdf5 *.h5 *.hdf)"))

    def save_cumulated_data(self):
        if not self.plotted_ticket is None:
            try:
                file_name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save Current Plot", filter="HDF5 Files (*.hdf5 *.h5 *.hdf)")

                if not file_name is None and not file_name.strip()=="":
                    if not (file_name.endswith("hd5") or file_name.endswith("hdf5") or file_name.endswith("hdf")):
                        file_name += ".hdf5"

                    save_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(file_name))

                    save_file.write_coordinates(self.plotted_ticket)
                    save_file.add_plot_xy(self.plotted_ticket, dataset_name="power_density")

                    save_file.close()
            except Exception as exception:
                QtWidgets.QMessageBox.critical(self, "Error", str(exception), QtWidgets.QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def replace_fig(self, shadow_beam, var_x, var_y, xrange, yrange, nbins, nolost):
        if self.plot_canvas is None:
            self.plot_canvas = PowerPlotXYWidget()
            self.image_box.layout().addWidget(self.plot_canvas)

        try:

            if self.autosave == 1:
                if self.autosave_file is None:
                    self.autosave_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(self.autosave_file_name))
                elif self.autosave_file.filename != congruence.checkFileName(self.autosave_file_name):
                    self.autosave_file.close()
                    self.autosave_file = ShadowPlot.PlotXYHdf5File(congruence.checkDir(self.autosave_file_name))

            if self.keep_result == 1:
                self.cumulated_ticket, last_ticket = self.plot_canvas.plot_power_density(shadow_beam, var_x, var_y,
                                                                                         self.total_power, self.cumulated_total_power,
                                                                                         self.energy_min, self.energy_max, self.energy_step,
                                                                                         nbins=nbins, xrange=xrange, yrange=yrange, nolost=nolost,
                                                                                         ticket_to_add=self.cumulated_ticket,
                                                                                         to_mm=self.workspace_units_to_mm,
                                                                                         show_image=self.view_type==1,
                                                                                         poor_statistics=self.replace_poor_statistic,
                                                                                         limit=self.good_rays_limit,
                                                                                         sigma_x=self.sigma_x,
                                                                                         sigma_y=self.sigma_y)
                self.plotted_ticket = self.cumulated_ticket

                if self.autosave == 1:
                    self.autosave_file.write_coordinates(self.cumulated_ticket)
                    dataset_name = "power_density"

                    self.autosave_file.add_plot_xy(self.cumulated_ticket, dataset_name=dataset_name)

                    if self.autosave_partial_results == 1:
                        if last_ticket is None:
                            self.autosave_file.add_plot_xy(self.cumulated_ticket,
                                                           plot_name="Energy Range: " + str(round(self.energy_max-self.energy_step, 2)) + "-" + str(round(self.energy_max, 2)),
                                                           dataset_name=dataset_name)
                        else:
                            self.autosave_file.add_plot_xy(last_ticket,
                                                           plot_name="Energy Range: " + str(round(self.energy_max-self.energy_step, 2)) + "-" + str(round(self.energy_max, 2)),
                                                           dataset_name=dataset_name)

                    self.autosave_file.flush()
            else:
                ticket, _ = self.plot_canvas.plot_power_density(shadow_beam, var_x, var_y,
                                                                self.total_power, self.cumulated_total_power,
                                                                self.energy_min, self.energy_max, self.energy_step,
                                                                nbins=nbins, xrange=xrange, yrange=yrange, nolost=nolost,
                                                                to_mm=self.workspace_units_to_mm,
                                                                show_image=self.view_type==1,
                                                                poor_statistics=self.replace_poor_statistic,
                                                                limit=self.good_rays_limit,
                                                                sigma_x=self.sigma_x,
                                                                sigma_y=self.sigma_y)

                self.cumulated_ticket = None
                self.plotted_ticket = ticket

                if self.autosave == 1:
                    self.autosave_file.write_coordinates(ticket)
                    self.autosave_file.add_plot_xy(ticket, dataset_name="power_density")
                    self.autosave_file.flush()

        except Exception as e:
            if not self.IS_DEVELOP:
                raise Exception("Data not plottable: No good rays or bad content")
            else:
                raise e

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
        if not self.cumulated_ticket is None:
            self.plot_canvas.plot_power_density_ticket(ticket=self.cumulated_ticket,
                                                       var_x=self.x_column_index+1,
                                                       var_y=self.y_column_index+1,
                                                       cumulated_total_power=self.cumulated_total_power,
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
                    self.cumulated_total_power = self.total_power
                else:
                    self.cumulated_total_power += self.total_power

                self.energy_step = self.input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")
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
