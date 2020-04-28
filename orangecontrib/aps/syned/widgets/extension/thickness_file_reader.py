import os, sys

import numpy
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication, QMessageBox, QFileDialog

from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

import oasys.util.oasys_util as OU

try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

class OWThicknessFileReader(OWWidget):
    name = "Thickness File Reader"
    id = "thickness_file_reader"
    description = "Thickness File Reader"
    icon = "icons/thickness_reader.png"
    author = "Luca Rebuffi"
    maintainer_email = "lrebuffi@anl.gov"
    priority = 3
    category = ""
    keywords = ["thickness_file_reader"]

    outputs = [{"name":"Thickness Error Files",
                "type":list,
                "doc":"Thickness Error Files",
                "id":"Thickness Error Files"}]

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 800
    IMAGE_HEIGHT = 610

    CONTROL_AREA_WIDTH = 405

    data=None

    separator = Setting(0)
    skip_rows = Setting(0)
    conversion_to_m_z = Setting(1.0)
    conversion_to_m_xy = Setting(1.0)

    surface_file_names = Setting(["thickness.dat"])

    negate = Setting(0)

    def __init__(self):
        super().__init__()

        geom = QApplication.desktop().availableGeometry()
        self.setGeometry(QRect(round(geom.width() * 0.05),
                               round(geom.height() * 0.05),
                               round(min(geom.width() * 0.98, self.MAX_WIDTH)),
                               round(min(geom.height() * 0.95, self.MAX_HEIGHT))))

        self.setMaximumHeight(self.geometry().height())
        self.setMaximumWidth(self.geometry().width())

        gui.separator(self.controlArea)

        button_box = oasysgui.widgetBox(self.controlArea, "", addSpace=False, orientation="horizontal")

        button = gui.button(button_box, self, "Read Thickness", callback=self.read_surface)
        button.setFixedHeight(45)

        button = gui.button(button_box, self, "Render Thickness", callback=self.render_surface)
        button.setFixedHeight(45)

        input_box_l = oasysgui.widgetBox(self.controlArea, "Input", addSpace=True, orientation="vertical", height=460, width=self.CONTROL_AREA_WIDTH)

        gui.button(input_box_l, self, "Select Thickness Error Profile Data Files", callback=self.select_files)

        self.files_area = oasysgui.textArea(height=250)

        self.refresh_files_text_area()

        input_box_l.layout().addWidget(self.files_area)


        gui.comboBox(input_box_l, self, "separator", label="Separator", labelWidth=350,
                     items=["Comma", "Space"], sendSelectedValue=False, orientation="horizontal")

        oasysgui.lineEdit(input_box_l, self, "skip_rows", label="Skip Rows", labelWidth=350, orientation="horizontal", valueType=int)

        oasysgui.lineEdit(input_box_l, self, "conversion_to_m_z", label="Thickness conversion to m", labelWidth=300, orientation="horizontal", valueType=float)
        oasysgui.lineEdit(input_box_l, self, "conversion_to_m_xy", label="Coordinates conversion to m", labelWidth=300, orientation="horizontal", valueType=float)

        gui.comboBox(input_box_l, self, "negate", label="Invert Surface", labelWidth=350,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")


        main_tabs = oasysgui.tabWidget(self.mainArea)
        plot_tab = oasysgui.createTabPage(main_tabs, "Thickness Error Surfaces")

        self.tab = []
        self.tabs = oasysgui.tabWidget(plot_tab)

        self.initialize_figures()

        gui.rubber(self.controlArea)
        gui.rubber(self.mainArea)


    def initialize_figures(self):
        current_tab = self.tabs.currentIndex()

        size = len(self.tab)
        for index in range(size):
            self.tabs.removeTab(size-1-index)

        files = []

        for surface_file_name in self.surface_file_names:
            files.append(os.path.basename(surface_file_name))

        if not len(files) == 0:
            self.figures = [None]*len(files)
            self.axes    = [None]*len(files)
            self.tab     = []

            for title in files:
                self.tab.append(oasysgui.createTabPage(self.tabs, title))

            for tab in self.tab:
                tab.setFixedHeight(self.IMAGE_HEIGHT)
                tab.setFixedWidth(self.IMAGE_WIDTH)

            self.tabs.setCurrentIndex(current_tab)
        else:
            self.figures = None
            self.axes    = None

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self,
                                                "Select Thickness Error Profiles", "", "Data Files (*.txt *.dat)",
                                                options=QFileDialog.Options())
        if files:
            self.surface_file_names = files

            self.refresh_files_text_area()

    def refresh_files_text_area(self):
        text = ""

        for file in self.surface_file_names:
            text += file + "\n"

        self.files_area.setText(text)

    def write_thickness_files(self, error_profile_data_files, index, xx, yy, zz):
        zz = numpy.round(zz, 12)
        xx = numpy.round(xx, 12)
        yy = numpy.round(yy, 12)

        filename, _ = os.path.splitext(os.path.basename(self.surface_file_names[index]))

        thickness_profile_data_file = filename + ".h5"

        OU.write_surface_file(zz, xx, yy, thickness_profile_data_file)

        error_profile_data_files.append(thickness_profile_data_file)

    def plot_figures(self):
        error_profile_data_files = []

        for index in range(len(self.data)):
            if self.figures[index] is None:
                figure = Figure(figsize=(600, 600))
                figure.patch.set_facecolor('white')

                self.axes[index] = figure.add_subplot(111, projection='3d')
                self.figures[index] = FigureCanvasQTAgg(figure)

                self.tab[index].layout().addWidget(self.figures[index])

            xx = self.data[index][0]
            yy = self.data[index][1]
            zz = self.data[index][2]

            self.axes[index].clear()

            x_to_plot, y_to_plot = numpy.meshgrid(xx, yy)

            self.axes[index].plot_surface(x_to_plot*1e6, y_to_plot*1e6, zz*1e6,
                                          rstride=1, cstride=1, cmap=cm.coolwarm, linewidth=0.5, antialiased=True)

            self.axes[index].set_xlabel("X [\u03bcm]")
            self.axes[index].set_ylabel("Y [\u03bcm]")
            self.axes[index].set_zlabel("Z [\u03bcm]")
            self.axes[index].mouse_init()

            self.write_thickness_files(error_profile_data_files, index, xx, yy, zz)

        self.send("Thickness Error Files", error_profile_data_files)


    def send_data(self):
        error_profile_data_files = []

        for index in range(len(self.data)):
            xx = self.data[index][0]
            yy = self.data[index][1]
            zz = self.data[index][2]

            self.write_thickness_files(error_profile_data_files, index, xx, yy, zz)

        self.send("Thickness Error Files", error_profile_data_files)

    def read_surface(self):
        try:
            self.read_data_files()
            self.send_data()

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def render_surface(self):
        try:
            self.read_data_files()
            self.plot_figures()

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception


    def read_data_files(self):
        self.data = []

        for surface_file_name in self.surface_file_names:
            surface_file_name = congruence.checkDir(surface_file_name)

            data = numpy.loadtxt(surface_file_name, delimiter="," if self.separator==0 else " ", skiprows=self.skip_rows)

            xx = numpy.unique(data[:, 0]) * self.conversion_to_m_xy
            yy = numpy.unique(data[:, 1]) * self.conversion_to_m_xy
            zz = numpy.reshape(data[:, 2], (len(xx), len(yy))).T

            zz = zz * self.conversion_to_m_z if self.negate == 0 else -1.0 * zz * self.conversion_to_m_z

            self.data.append([xx, yy, zz])

        self.initialize_figures()
