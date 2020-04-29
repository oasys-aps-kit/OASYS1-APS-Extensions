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

from orangecontrib.shadow.widgets.gui import ow_ellipsoid_element, ow_optical_element

from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from orangecontrib.shadow.util.shadow_objects import ShadowOpticalElement, ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowPreProcessor

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

    def __init__(self):
        graphical_Options=ow_optical_element.GraphicalOptions(is_mirror=True)

        super().__init__(graphical_Options)

        plot_tab = oasysgui.createTabPage(self.main_tabs, "Bender Plots")

        bender_tabs = oasysgui.tabWidget(plot_tab)

        tabs = [oasysgui.createTabPage(bender_tabs, "Ideal - Bender"),
                oasysgui.createTabPage(bender_tabs, "Figure Error"),
                oasysgui.createTabPage(bender_tabs, "(Ideal - Bender) + Figure Error")]

        def create_figure_canvas():
            figure = Figure(figsize=(100, 100))
            figure.patch.set_facecolor('white')

            figure.add_subplot(111, projection='3d')

            figure_canvas = FigureCanvasQTAgg(figure)
            figure_canvas.setFixedWidth(self.IMAGE_WIDTH)
            figure_canvas.setFixedHeight(self.IMAGE_HEIGHT)

            return figure_canvas

        self.figure_canvas = [create_figure_canvas(), create_figure_canvas(), create_figure_canvas()]

        tabs[0].layout().addWidget(self.figure_canvas[0])
        tabs[1].layout().addWidget(self.figure_canvas[1])
        tabs[2].layout().addWidget(self.figure_canvas[2])

        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)

    ################################################################
    #
    #  SHADOW MANAGEMENT
    #
    ################################################################

    def completeOperations(self, shadow_oe):
        if self.is_cylinder != 1: raise ValueError("Bender Ellipse must be a cylinder")
        if self.cylinder_orientation != 0: raise ValueError("Cylinder orientation must be 0")
        if self.is_infinite == 0: raise ValueError("This OE can't have infinite dimensions")

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

        self.bin_x = 100
        self.bin_y = 500

        x, y, z  = self.calculate_ideal_surface(shadow_oe_temp)
        bender_parameter, z_bender_correction = self.calculate_bender_correction(y, z)

        self.plot3D(x, y, z_bender_correction, 0, "Ideal Surface - Bender Surface")

        if self.modified_surface > 0:
            if self.modified_surface == 1 and self.ms_type_of_defect == 2:
                x_e, y_e, z_e = ShadowPreProcessor.read_surface_error_file(self.ms_defect_file_name)

                if (len(x) == len(x_e) and len(y) == len(y_e)) and \
                   (numpy.allclose(x, x_e) and numpy.allclose(y, y_e)):
                    z_figure_error = z_e
                else:
                    z_figure_error = numpy.zeros((z.shape))
                    for i in range(z.shape[0]):
                        for j in range(z.shape[1]):
                            z_figure_error[i, j] = RectBivariateSpline(x_e, y_e, z_e).ev(x[i], y[j])
            else:
                raise ValueError("Only Preprocessor generated error profiles are admitted")

            z_bender_correction += z_figure_error

            self.plot3D(x, y, z_figure_error, 1, "Figure Error")
            self.plot3D(x, y, z_bender_correction, 2, "Ideal Surface - Bender Surface + Figure Error")

        self.temporary_file, _ = os.path.splitext(self.ms_defect_file_name)
        self.temporary_file += "_bender.dat"

        ST.write_shadow_surface(z_bender_correction.T, numpy.round(x, 6), numpy.round(y, 6), self.temporary_file)

        shadow_oe._oe.FILE_RIP  = bytes(self.temporary_file, 'utf-8')

        super().completeOperations(shadow_oe)

    def instantiateShadowOE(self):
        return ShadowOpticalElement.create_ellipsoid_mirror()

    def calculate_ideal_surface(self, shadow_oe, sign=-1):
        congruence.checkStrictlyPositiveNumber(self.bin_x, "Bins X")
        congruence.checkStrictlyPositiveNumber(self.bin_y, "Bins Y")

        x = numpy.linspace(-self.dim_x_minus, self.dim_x_plus, self.bin_x + 1)
        y = numpy.linspace(-self.dim_y_minus, self.dim_y_plus, self.bin_y + 1)

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
        E = 131000
        b0 = self.dim_x_plus + self.dim_x_minus
        L = self.dim_y_plus + self.dim_y_minus
        h = 10

        ideal_profile = z[0, :] # one row is the profile of the cylinder, enough for the minimizer
        ideal_profile -= numpy.max(ideal_profile)

        def bender_function(Y, e, ratio, M1):
            Eh_3 = E*h**3

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

        parameters, _ = curve_fit(bender_function, y, ideal_profile, p0=[0.527, 0.61, 50.0], bounds=(0, [1.0, 1.0, numpy.inf]), method='trf')#, jac="3-point")#, loss="soft_l1", f_scale=0.1)
        correction_profile = ideal_profile - bender_function(y, parameters[0], parameters[1], parameters[2])

        z_bender_correction = numpy.zeros(z.shape)
        for i in range(z_bender_correction.shape[0]): z_bender_correction[i, :] = numpy.copy(correction_profile)

        return parameters, z_bender_correction

    def plot3D(self, x_coords, y_coords, z_values, index, title=""):
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
