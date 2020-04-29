import os, sys, numpy
from scipy.interpolate import RectBivariateSpline
from scipy.optimize import curve_fit

from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QSettings

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence
from oasys.util.oasys_util import TriggerIn

from orangecontrib.shadow.util.shadow_objects import ShadowOpticalElement, ShadowBeam, ShadowPreProcessorData
from orangecontrib.shadow.util.shadow_util import ShadowPreProcessor
from orangecontrib.shadow.widgets.gui import ow_ellipsoid_element, ow_optical_element

from Shadow import ShadowTools as ST

class BendableEllipsoidMirror(ow_ellipsoid_element.EllipsoidElement):
    name = "Bendable Ellipsoid Mirror"
    description = "Shadow OE: Bendable Ellipsoid Mirror"
    icon = "icons/bendable_ellipsoid_mirror.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 6
    category = "Optical Elements"
    keywords = ["data", "file", "load", "read"]

    send_footprint_beam = QSettings().value("output/send-footprint", 0, int) == 1

    if send_footprint_beam:
        outputs = [{"name":"Beam",
                    "type":ShadowBeam,
                    "doc":"Shadow Beam",
                    "id":"beam"},
                   {"name":"Footprint",
                    "type":list,
                    "doc":"Footprint",
                    "id":"beam"},
                   {"name":"Trigger",
                    "type": TriggerIn,
                    "doc":"Feedback signal to start a new beam simulation",
                    "id":"Trigger"},
                   {"name": "PreProcessor_Data",
                    "type": ShadowPreProcessorData,
                    "doc": "PreProcessor Data",
                    "id": "PreProcessor_Data"}
                   ]
    else:
        outputs = [{"name":"Beam",
                    "type":ShadowBeam,
                    "doc":"Shadow Beam",
                    "id":"beam"},
                   {"name":"Trigger",
                    "type": TriggerIn,
                    "doc":"Feedback signal to start a new beam simulation",
                    "id":"Trigger"},
                   {"name": "PreProcessor_Data",
                    "type": ShadowPreProcessorData,
                    "doc": "PreProcessor Data",
                    "id": "PreProcessor_Data"}
                   ]

    show_bender_plots = Setting(0)

    bender_bin_x = Setting(100)
    bender_bin_y = Setting(500)

    E = Setting(131000)
    h = Setting(10)

    which_length = Setting(0)
    optimized_length = Setting(0.0)

    M1    = Setting(0.0)
    ratio = Setting(0.5)
    e     = Setting(0.3)

    M1_out    = 0.0
    ratio_out = 0.0
    e_out     = 0.0

    M1_fixed    = Setting(0)
    ratio_fixed = Setting(0)
    e_fixed     = Setting(0)

    M1_min    = Setting(0.0)
    ratio_min = Setting(0.0)
    e_min     = Setting(0.0)

    M1_max    = Setting(1000.0)
    ratio_max = Setting(10.0)
    e_max     = Setting(1.0)

    def __init__(self):
        graphical_Options=ow_optical_element.GraphicalOptions(is_mirror=True)

        super().__init__(graphical_Options)

        tab_bender = oasysgui.createTabPage(self.tabs_basic_setting, "Bender")

        surface_box = oasysgui.widgetBox(tab_bender, "Surface Setting", addSpace=False, orientation="vertical")

        oasysgui.lineEdit(surface_box, self, "bender_bin_x", "bins Sagittal", labelWidth=260, valueType=int, orientation="horizontal")
        oasysgui.lineEdit(surface_box, self, "bender_bin_y", "bins Transversal", labelWidth=260, valueType=int, orientation="horizontal")

        material_box = oasysgui.widgetBox(tab_bender, "Bender Setting", addSpace=False, orientation="vertical")

        self.le_E = oasysgui.lineEdit(material_box, self, "E", "Young's Modulus ", labelWidth=260, valueType=float, orientation="horizontal")
        self.le_h = oasysgui.lineEdit(material_box, self, "h", "Thickness ", labelWidth=260, valueType=float, orientation="horizontal")

        fit_box = oasysgui.widgetBox(tab_bender, "Fit Setting", addSpace=False, orientation="vertical")

        gui.comboBox(fit_box, self, "which_length", label="Optimized Length", items=["Total", "Partial"], labelWidth=150, orientation="horizontal",
                     callback=self.set_which_length)
        self.le_optimized_length = oasysgui.lineEdit(fit_box, self, "optimized_length", "Optimized Length ", labelWidth=260, valueType=float, orientation="horizontal")
        self.set_which_length()

        gui.separator(fit_box)

        m1_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
        oasysgui.lineEdit(m1_box, self, "M1", "Momentum 1", labelWidth=170, valueType=float, orientation="horizontal")
        le = oasysgui.lineEdit(m1_box, self, "M1_out", " ", labelWidth=4, valueType=float, orientation="horizontal")
        le.setEnabled(False)
        le.setStyleSheet("color: blue; background-color: orange; font:bold")
        def set_M1_fit(): self.M1 = self.M1_out
        gui.button(m1_box, self, "<-", width=20, callback=set_M1_fit)
        m1_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
        gui.checkBox(m1_box, self, "M1_fixed", " ", labelWidth=20, callback=self.set_M1)
        gui.label(m1_box, self, "  Fixed")
        self.le_M1_min = oasysgui.lineEdit(m1_box, self, "M1_min", "    or             Min", labelWidth=100, valueType=float, orientation="horizontal")
        self.le_M1_max = oasysgui.lineEdit(m1_box, self, "M1_max", "Max", labelWidth=30, valueType=float, orientation="horizontal")
        self.set_M1()

        gui.separator(fit_box)

        ratio_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
        oasysgui.lineEdit(ratio_box, self, "ratio", "Momentum 1/Momentum 2", labelWidth=170, valueType=float, orientation="horizontal")
        le = oasysgui.lineEdit(ratio_box, self, "ratio_out", " ", labelWidth=4, valueType=float, orientation="horizontal")
        le.setEnabled(False)
        le.setStyleSheet("color: blue; background-color: orange; font:bold")
        def set_ratio_fit(): self.ratio = self.ratio_out
        gui.button(ratio_box, self, "<-", width=20, callback=set_ratio_fit)
        ratio_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
        gui.checkBox(ratio_box, self, "ratio_fixed", " ", labelWidth=20, callback=self.set_ratio)
        gui.label(ratio_box, self, "  Fixed")
        self.le_ratio_min = oasysgui.lineEdit(ratio_box, self, "ratio_min", "    or             Min", labelWidth=100, valueType=float, orientation="horizontal")
        self.le_ratio_max = oasysgui.lineEdit(ratio_box, self, "ratio_max", "Max", labelWidth=30, valueType=float, orientation="horizontal")
        self.set_ratio()

        gui.separator(fit_box)

        e_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
        oasysgui.lineEdit(e_box, self, "e", "Minor side/Major side", labelWidth=170, valueType=float, orientation="horizontal")
        le = oasysgui.lineEdit(e_box, self, "e_out", " ", labelWidth=4, valueType=float, orientation="horizontal")
        le.setEnabled(False)
        le.setStyleSheet("color: blue; background-color: orange; font:bold")
        def set_e_fit(): self.e = self.e_out
        gui.button(e_box, self, "<-", width=20, callback=set_e_fit)
        e_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
        gui.checkBox(e_box, self, "e_fixed", " ", labelWidth=20, callback=self.set_e)
        gui.label(e_box, self, "  Fixed")
        self.le_e_min = oasysgui.lineEdit(e_box, self, "e_min", "    or             Min", labelWidth=100, valueType=float, orientation="horizontal")
        self.le_e_max = oasysgui.lineEdit(e_box, self, "e_max", "Max", labelWidth=30, valueType=float, orientation="horizontal")
        self.set_e()

        #######################################################
        
        plot_tab = oasysgui.createTabPage(self.main_tabs, "Bender Plots")

        view_box = oasysgui.widgetBox(plot_tab, "Plotting Style", addSpace=False, orientation="vertical", width=350)

        self.view_type_combo = gui.comboBox(view_box, self, "show_bender_plots", label="Show Plots", labelWidth=220,
                                            items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        bender_tabs = oasysgui.tabWidget(plot_tab)

        tabs = [oasysgui.createTabPage(bender_tabs, "Bender vs. Ideal (1D)"),
                oasysgui.createTabPage(bender_tabs, "Ideal - Bender (1D)"),
                oasysgui.createTabPage(bender_tabs, "Ideal - Bender (3D)"),
                oasysgui.createTabPage(bender_tabs, "Figure Error (3D)"),
                oasysgui.createTabPage(bender_tabs, "Ideal - Bender + Figure Error (3D)")]

        def create_figure_canvas(mode="3D"):
            figure = Figure(figsize=(100, 100))
            figure.patch.set_facecolor('white')
            if mode == "3D": figure.add_subplot(111, projection='3d')
            else: figure.add_subplot(111)

            figure_canvas = FigureCanvasQTAgg(figure)
            figure_canvas.setFixedWidth(self.IMAGE_WIDTH)
            figure_canvas.setFixedHeight(self.IMAGE_HEIGHT-10)

            return figure_canvas

        self.figure_canvas = [create_figure_canvas("1D"), create_figure_canvas("1D"),
                              create_figure_canvas(), create_figure_canvas(), create_figure_canvas()]

        for tab, figure_canvas in zip(tabs, self.figure_canvas): tab.layout().addWidget(figure_canvas)

        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)

    ################################################################
    #
    #  SHADOW MANAGEMENT
    #
    ################################################################

    def set_which_length(self):
        self.le_optimized_length.setEnabled(self.which_length==1)
    
    def set_M1(self):
        self.le_M1_min.setEnabled(self.M1_fixed==0)
        self.le_M1_max.setEnabled(self.M1_fixed==0)

    def set_ratio(self):
        self.le_ratio_min.setEnabled(self.ratio_fixed==0)
        self.le_ratio_max.setEnabled(self.ratio_fixed==0)
        
    def set_e(self):
        self.le_e_min.setEnabled(self.e_fixed==0)
        self.le_e_max.setEnabled(self.e_fixed==0)

    def after_change_workspace_units(self):
        super().after_change_workspace_units()

        label = self.le_E.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [N/" + self.workspace_units_label + "^2]")
        label = self.le_h.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_optimized_length.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

    def checkFields(self):
        super().checkFields()

        if self.is_cylinder != 1: raise ValueError("Bender Ellipse must be a cylinder")
        if self.cylinder_orientation != 0: raise ValueError("Cylinder orientation must be 0")
        if self.is_infinite == 0: raise ValueError("This OE can't have infinite dimensions")
        if self.which_length==1:
            congruence.checkStrictlyPositiveNumber(self.optimized_length, "Optimized Length")
            congruence.checkLessOrEqualThan(self.optimized_length, self.dim_y_plus+self.dim_y_minus, "Optimized Length", "Total Length")

        if self.modified_surface > 0:
            if not (self.modified_surface == 1 and self.ms_type_of_defect == 2):
                raise ValueError("Only Preprocessor generated error profiles are admitted")

        congruence.checkStrictlyPositiveNumber(self.bender_bin_x, "Bins X")
        congruence.checkStrictlyPositiveNumber(self.bender_bin_y, "Bins Y")

    def completeOperations(self, shadow_oe):
        shadow_oe_temp  = shadow_oe.duplicate()
        input_beam_temp = self.input_beam.duplicate(history=False)

        if self.add_acceptance_slits==1:
            congruence.checkStrictlyPositiveNumber(self.auto_slit_width_xaxis, "Slit width/x-axis")
            congruence.checkStrictlyPositiveNumber(self.auto_slit_height_zaxis, "Slit height/z-axis")

            n_screen = 1
            i_screen = numpy.zeros(10)  # after
            i_abs = numpy.zeros(10)
            i_slit = numpy.zeros(10)
            i_stop = numpy.zeros(10)
            k_slit = numpy.zeros(10)
            thick = numpy.zeros(10)
            file_abs = ['', '', '', '', '', '', '', '', '', '']
            rx_slit = numpy.zeros(10)
            rz_slit = numpy.zeros(10)
            sl_dis = numpy.zeros(10)
            file_scr_ext = ['', '', '', '', '', '', '', '', '', '']
            cx_slit = numpy.zeros(10)
            cz_slit = numpy.zeros(10)

            i_screen[0] = 1
            i_slit[0] = 1

            rx_slit[0] = self.auto_slit_width_xaxis
            rz_slit[0] = self.auto_slit_height_zaxis
            cx_slit[0] = self.auto_slit_center_xaxis
            cz_slit[0] = self.auto_slit_center_zaxis

            shadow_oe_temp._oe.set_screens(n_screen,
                                           i_screen,
                                           i_abs,
                                           sl_dis,
                                           i_slit,
                                           i_stop,
                                           k_slit,
                                           thick,
                                           numpy.array(file_abs),
                                           rx_slit,
                                           rz_slit,
                                           cx_slit,
                                           cz_slit,
                                           numpy.array(file_scr_ext))

        ShadowBeam.traceFromOE(input_beam_temp,
                               shadow_oe_temp,
                               write_start_file=0,
                               write_end_file=0,
                               widget_class_name=type(self).__name__)

        x, y, z  = self.calculate_ideal_surface(shadow_oe_temp)

        bender_parameter, z_bender_correction = self.calculate_bender_correction(y, z)

        self.e_out     = round(bender_parameter[0], 5)
        self.ratio_out = round(bender_parameter[1], 5)
        self.M1_out    = round(bender_parameter[2], int(6*self.workspace_units_to_mm))

        self.plot3D(x, y, z_bender_correction, 2, "Ideal - Bender Surfaces")

        if self.modified_surface > 0:
            x_e, y_e, z_e = ShadowPreProcessor.read_surface_error_file(self.ms_defect_file_name)

            if (len(x) == len(x_e) and len(y) == len(y_e)) and \
               (numpy.allclose(x, x_e) and numpy.allclose(y, y_e)):
                z_figure_error = z_e
            else:
                z_figure_error = numpy.zeros((z.shape))
                for i in range(z.shape[0]):
                    for j in range(z.shape[1]):
                        z_figure_error[i, j] = RectBivariateSpline(x_e, y_e, z_e).ev(x[i], y[j])

            z_bender_correction += z_figure_error

            self.plot3D(x, y, z_figure_error, 3, "Figure Error Surface")
            self.plot3D(x, y, z_bender_correction, 4, "Ideal - Bender + Figure Error Surfaces")

        self.temporary_file, _ = os.path.splitext(self.ms_defect_file_name)
        self.temporary_file += "_bender.dat"

        ST.write_shadow_surface(z_bender_correction.T, numpy.round(x, 6), numpy.round(y, 6), self.temporary_file)

        shadow_oe._oe.FILE_RIP  = bytes(self.temporary_file, 'utf-8')

        super().completeOperations(shadow_oe)

        self.send("PreProcessor_Data", ShadowPreProcessorData(error_profile_data_file=self.temporary_file,
                                                              error_profile_x_dim=self.bender_bin_x,
                                                              error_profile_y_dim=self.bender_bin_y))

    def instantiateShadowOE(self):
        return ShadowOpticalElement.create_ellipsoid_mirror()

    def calculate_ideal_surface(self, shadow_oe, sign=-1):
        x = numpy.linspace(-self.dim_x_minus, self.dim_x_plus, self.bender_bin_x + 1)
        y = numpy.linspace(-self.dim_y_minus, self.dim_y_plus, self.bender_bin_y + 1)

        c1  = round(shadow_oe._oe.CCC[0], 10)
        c2  = round(shadow_oe._oe.CCC[1], 10)
        c3  = round(shadow_oe._oe.CCC[2], 10)
        c4  = round(shadow_oe._oe.CCC[3], 10)
        c5  = round(shadow_oe._oe.CCC[4], 10)
        c6  = round(shadow_oe._oe.CCC[5], 10)
        c7  = round(shadow_oe._oe.CCC[6], 10)
        c8  = round(shadow_oe._oe.CCC[7], 10)
        c9  = round(shadow_oe._oe.CCC[8], 10)
        c10 = round(shadow_oe._oe.CCC[9], 10)

        xx, yy = numpy.meshgrid(x, y)

        c = c1*(xx**2) + c2*(yy**2) + c4*xx*yy + c7*xx + c8*yy + c10
        b = c5*yy + c6*xx + c9
        a = c3

        z = (-b + sign*numpy.sqrt(b**2 - 4*a*c))/(2*a)
        z[b**2 - 4*a*c < 0] = numpy.nan

        return x, y, z.T

    def calculate_bender_correction(self, y, z):
        b0 = self.dim_x_plus + self.dim_x_minus
        L = self.dim_y_plus + self.dim_y_minus  # add optimization length

        ideal_profile = z[0, :]  # one row is the profile of the cylinder, enough for the minimizer

        # 𝑥′=𝑥cos𝜃−𝑦sin𝜃
        # 𝑦′=𝑥sin𝜃 + 𝑦cos𝜃
        #yp = y*numpy.cos(theta) - ideal_profile*numpy.sin(theta)

        theta = numpy.arctan((ideal_profile[0] - ideal_profile[-1]) / L)
        ideal_profile = y*numpy.sin(theta) + ideal_profile*numpy.cos(theta)
        ideal_profile -= numpy.max(ideal_profile)

        if self.which_length == 0:
            y_fit = y
            ideal_profile_fit = ideal_profile
        else:
            cursor = numpy.where(numpy.logical_and(y >= -self.optimized_length/2, y <= self.optimized_length/2) )

            y_fit             = y[cursor]
            ideal_profile_fit = ideal_profile[cursor]

        def bender_function(Y, e, ratio, M1):
            Eh_3 = self.E*self.h**3

            M2 = M1 * ratio
            A = (M1 + M2)/2
            B = (M1 - M2)/L
            C = Eh_3*(2*b0 + e*b0)/24
            D = Eh_3*e*b0/(12*L) #e*b0/L # TODO: verify formula
            H = (A*D + B*C)/D**2

            CDLP = C + D*L/2
            CDLM = C - D*L/2
            CDY  = C + D*Y

            F = (H/L)*((CDLM*numpy.log(CDLM) - CDLP*numpy.log(CDLP))/D + L)
            G = -(H*((CDLM*numpy.log(CDLM) + CDLP*numpy.log(CDLP))) - (B*L**2)/4)/(2*D) # TODO: verify sing of the second term

            return H * ((CDY/D)*numpy.log(CDY) - Y) - (B*Y**2)/(2*D) + F*Y + G

        epsilon = 1e-12
        parameters, _ = curve_fit(bender_function, y_fit, ideal_profile_fit,
                                  p0=[self.e, self.ratio, self.M1],
                                  bounds=([self.e_min if self.e_fixed==0 else self.e-epsilon,
                                           self.ratio_min if self.ratio_fixed==0 else self.ratio-epsilon,
                                           self.M1_min if self.M1_fixed==0 else self.M1-epsilon],
                                          [self.e_max if self.e_fixed == 0 else self.e,
                                           self.ratio_max if self.ratio_fixed == 0 else self.ratio,
                                           self.M1_max if self.M1_fixed == 0 else self.M1]),
                                  method='trf',
                                  jac="3-point")#, loss="soft_l1", f_scale=0.1)

        bender_profile = bender_function(y, parameters[0], parameters[1], parameters[2])
        correction_profile = ideal_profile - bender_profile
        
        self.plot1D(y, bender_profile, y_values_2=ideal_profile, index=0, title="Bender vs. Ideal Profiles", um=1)
        self.plot1D(y, correction_profile, index=1, title="Correction Profile 1D")

        z_bender_correction = numpy.zeros(z.shape)
        for i in range(z_bender_correction.shape[0]): z_bender_correction[i, :] = numpy.copy(correction_profile)

        return parameters, z_bender_correction

    def plot1D(self, x_coords, y_values, y_values_2=None, index=0, title="", um=0):
        if self.show_bender_plots == 1:
            figure = self.figure_canvas[index].figure

            axis = figure.gca()
            axis.clear()

            axis.set_xlabel("Y [" + self.workspace_units_label + "]")
            axis.set_ylabel("Z [" + ("nm" if um==0 else "\u03bcm") + "]")
            axis.set_title(title)
            
            axis.plot(x_coords, (y_values * self.workspace_units_to_m * (1e9 if um==0 else 1e6)), color="blue", label="bender", linewidth=2)
            if not y_values_2 is None: axis.plot(x_coords, (y_values_2 * self.workspace_units_to_m * (1e9 if um==0 else 1e6)), "-.r", label="ideal")

            axis.legend(loc=0, fontsize='small')

            figure.canvas.draw()

    def plot3D(self, x_coords, y_coords, z_values, index, title=""):
        if self.show_bender_plots == 1:
            figure = self.figure_canvas[index].figure
            x_to_plot, y_to_plot = numpy.meshgrid(x_coords, y_coords)
            z_to_plot = z_values.T

            axis = figure.gca()
            axis.clear()

            axis.set_xlabel("X [" + self.workspace_units_label + "]")
            axis.set_ylabel("Y [" + self.workspace_units_label + "]")
            axis.set_zlabel("Z [nm]")
            axis.set_title(title)

            axis.plot_surface(x_to_plot, y_to_plot, (z_to_plot * self.workspace_units_to_m * 1e9),
                              rstride=1, cstride=1, cmap=cm.autumn, linewidth=0.5, antialiased=True)

            figure.canvas.draw()

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = BendableEllipsoidMirror()
    ow.show()
    a.exec_()
    ow.saveSettings()
