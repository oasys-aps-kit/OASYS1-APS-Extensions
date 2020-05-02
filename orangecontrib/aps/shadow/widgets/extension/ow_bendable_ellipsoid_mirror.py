import os, sys, numpy
from scipy.interpolate import RectBivariateSpline, interp2d
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

    output_file_name = Setting("mirror_bender.dat")

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

        file_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal", height=25)
        self.le_output_file_name = oasysgui.lineEdit(file_box, self, "output_file_name", "Out File Name", labelWidth=100, valueType=str, orientation="horizontal")
        gui.button(file_box, self, "...", callback=self.select_output_file, width=20)

        length_box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")

        self.cb_optimized_length = gui.comboBox(length_box, self, "which_length", label="Optimized Length ", items=["Total", "Partial"],
                     labelWidth=150, orientation="horizontal", callback=self.set_which_length)
        self.le_optimized_length = oasysgui.lineEdit(length_box, self, "optimized_length", " ", labelWidth=10, valueType=float, orientation="horizontal")
        self.set_which_length()

        gui.separator(fit_box)

        def add_parameter_box(variable, label):
            box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
            oasysgui.lineEdit(box, self, variable, label, labelWidth=50, valueType=float, orientation="horizontal")

            le = oasysgui.lineEdit(box, self, variable + "_out", " ", labelWidth=4, valueType=float, orientation="horizontal")
            le.setEnabled(False)
            le.setStyleSheet("color: blue; background-color: rgb(254, 244, 205); font:bold")
            def set_variable_fit(): setattr(self, variable, getattr(self, variable + "_out"))
            gui.button(box, self, "<-", width=20, callback=set_variable_fit)

            box = oasysgui.widgetBox(fit_box, "", addSpace=False, orientation="horizontal")
            gui.label(box, self, "       ", labelWidth=50)
            gui.checkBox(box, self, variable + "_fixed", " ", labelWidth=15, callback=getattr(self, "set_" + variable))

            setattr(self, "le_" + variable + "_min", oasysgui.lineEdit(box, self, variable + "_min", "Fixed or Min",
                                                                       labelWidth=75, valueType=float, orientation="horizontal"))
            setattr(self, "le_" + variable + "_max", oasysgui.lineEdit(box, self, variable + "_max", "Max",
                                                                        labelWidth=30, valueType=float, orientation="horizontal"))
            getattr(self, "set_" + variable)()

        add_parameter_box("M1", "M1")
        gui.separator(fit_box)
        add_parameter_box("ratio", "M1/M2")
        gui.separator(fit_box)
        add_parameter_box("e", "e")

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

    def select_output_file(self):
        self.le_output_file_name.setText(oasysgui.selectFileFromDialog(self, self.output_file_name, "Select Output File", file_extension_filter="Data Files (*.dat)"))

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
        label = self.cb_optimized_length.parent().layout().itemAt(0).widget()
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
        self.output_file_name_full = congruence.checkFileName(self.output_file_name)

    def completeOperations(self, shadow_oe):
        shadow_oe_temp  = shadow_oe.duplicate()
        input_beam_temp = self.input_beam.duplicate(history=False)

        self.manage_acceptance_slits(shadow_oe_temp)

        ShadowBeam.traceFromOE(input_beam_temp,
                               shadow_oe_temp,
                               write_start_file=0,
                               write_end_file=0,
                               widget_class_name=type(self).__name__)

        x, y, z = self.calculate_ideal_surface(shadow_oe_temp)

        bender_parameter, z_bender_correction = self.calculate_bender_correction(y, z)

        self.e_out     = round(bender_parameter[0], 5)
        self.ratio_out = round(bender_parameter[1], 5)
        self.M1_out    = round(bender_parameter[2], int(6*self.workspace_units_to_mm))

        self.plot3D(x, y, z_bender_correction, 2, "Ideal - Bender Surfaces")

        if self.modified_surface > 0:
            x_e, y_e, z_e = ShadowPreProcessor.read_surface_error_file(self.ms_defect_file_name)

            if len(x) == len(x_e) and len(y) == len(y_e) and \
                    x[0] == x_e[0] and x[-1] == x_e[-1] and \
                    y[0] == y_e[0] and y[-1] == y_e[-1]:
                z_figure_error = z_e
            else:
                z_figure_error = interp2d(y_e, x_e, z_e, kind='cubic')(y, x)

            z_bender_correction += z_figure_error

            self.plot3D(x, y, z_figure_error,      3, "Figure Error Surface")
            self.plot3D(x, y, z_bender_correction, 4, "Ideal - Bender + Figure Error Surfaces")

        ST.write_shadow_surface(z_bender_correction.T, numpy.round(x, 6), numpy.round(y, 6), self.output_file_name_full)

        # Add new surface as figure error
        shadow_oe._oe.F_RIPPLE  = 1
        shadow_oe._oe.F_G_S     = 2
        shadow_oe._oe.FILE_RIP  = bytes(self.output_file_name_full, 'utf-8')

        # Redo Raytracing with the new file
        super().completeOperations(shadow_oe)

        self.send("PreProcessor_Data", ShadowPreProcessorData(error_profile_data_file=self.output_file_name,
                                                              error_profile_x_dim=self.dim_x_plus+self.dim_x_minus,
                                                              error_profile_y_dim=self.dim_y_plus+self.dim_y_minus))

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

        # flip the coordinate system to be consistent with Mike's formulas
        ideal_profile = z[0, :][::-1]  # one row is the profile of the cylinder, enough for the minimizer

        # 𝑥′=𝑥cos𝜃−𝑦sin𝜃
        # 𝑦′=𝑥sin𝜃 + 𝑦cos𝜃
        #yp = y*numpy.cos(theta) - ideal_profile*numpy.sin(theta)
        # TODO: think about rotating the conic coefficients instead
        #       or reinterpolating the ellipsis on the original coordinates?
        #theta         = numpy.arctan((ideal_profile[0] - ideal_profile[-1]) / L)
        #ideal_profile = y*numpy.sin(theta) + ideal_profile*numpy.cos(theta)
        #ideal_profile -= numpy.max(ideal_profile)

        ideal_profile += -ideal_profile[0] + ((L/2 + y)*(ideal_profile[0]-ideal_profile[-1]))/L

        if self.which_length == 0:
            y_fit             = y
            ideal_profile_fit = ideal_profile
        else:
            cursor            = numpy.where(numpy.logical_and(y >= -self.optimized_length/2,
                                                              y <= self.optimized_length/2) )
            y_fit             = y[cursor]
            ideal_profile_fit = ideal_profile[cursor]

        def bender_function(Y, e, ratio, M1):
            Eh_3 = self.E*self.h**3
            M2   = M1 * ratio
            A    = (M1 + M2)/2
            B    = (M1 - M2)/L
            C    = Eh_3*(2*b0 + e*b0)/24
            D    = Eh_3*e*b0/(12*L)
            H    = (A*D + B*C)/D**2
            CDLP = C + D*L/2
            CDLM = C - D*L/2
            F    = (H/L)*((CDLM*numpy.log(CDLM) - CDLP*numpy.log(CDLP))/D + L)
            G    = -(H*((CDLM*numpy.log(CDLM) + CDLP*numpy.log(CDLP))) - (B*L**2)/4)/(2*D)
            CDY  = C + D*Y

            return H * ((CDY/D)*numpy.log(CDY) - Y) - (B*Y**2)/(2*D) + F*Y + G

        epsilon = 1e-12
        parameters, _ = curve_fit(bender_function, y_fit, ideal_profile_fit,
                                  p0=[self.e, self.ratio, self.M1],
                                  bounds=([self.e_min if self.e_fixed==0 else (self.e-epsilon),
                                           self.ratio_min if self.ratio_fixed==0 else (self.ratio-epsilon),
                                           self.M1_min if self.M1_fixed==0 else (self.M1-epsilon)],
                                          [self.e_max if self.e_fixed == 0 else self.e,
                                           self.ratio_max if self.ratio_fixed == 0 else self.ratio,
                                           self.M1_max if self.M1_fixed == 0 else self.M1]),
                                  method='trf')#, jac="3-point")

        bender_profile = bender_function(y, parameters[0], parameters[1], parameters[2])

        # rotate back to Shadow system
        bender_profile = bender_profile[::-1]
        ideal_profile  = ideal_profile[::-1]

        # from here it's Shadow Axis system
        correction_profile = ideal_profile - bender_profile

        # r-squared = 1 - residual sum of squares / total sum of squares
        r_squared = 1 - (numpy.sum(correction_profile**2) / numpy.sum((ideal_profile - numpy.mean(ideal_profile))**2))
        rms       = round(correction_profile.std()*1e9*self.workspace_units_to_m, 6)


        self.plot1D(y, bender_profile, y_values_2=ideal_profile, index=0,
                    title = "Bender vs. Ideal Profiles" + "\n" + r'$R^2$ = ' + str(r_squared), um=1)
        self.plot1D(y, correction_profile, index=1, title="Correction Profile 1D, r.m.s. = " + str(rms) + " nm")

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

            axis.mouse_init()

if __name__ == "__main__":
    a = QApplication(sys.argv)
    ow = BendableEllipsoidMirror()
    ow.show()
    a.exec_()
    ow.saveSettings()
