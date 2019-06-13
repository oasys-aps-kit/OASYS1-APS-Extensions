import os, sys

import numpy
from PyQt5.QtCore import QRect
from PyQt5.QtWidgets import QApplication, QMessageBox

from matplotlib import cm
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure

from orangewidget import gui
from orangewidget.settings import Setting

from oasys.widgets.widget import OWWidget
from oasys.widgets import gui as oasysgui
from oasys.widgets import congruence

from oasys.util.oasys_objects import OasysSurfaceData

from Shadow import ShadowTools as ST
from orangecontrib.shadow.util.shadow_objects import ShadowPreProcessorData

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
    priority = 51
    category = ""
    keywords = ["surface_file_reader"]

    outputs = [{"name": "PreProcessor_Data",
                "type": ShadowPreProcessorData,
                "doc": "PreProcessor Data",
                "id": "PreProcessor_Data"},
               {"name":"Files",
                "type":list,
                "doc":"Files",
                "id":"Files"}]

    want_main_area = 1
    want_control_area = 1

    MAX_WIDTH = 1320
    MAX_HEIGHT = 700

    IMAGE_WIDTH = 860
    IMAGE_HEIGHT = 645

    CONTROL_AREA_WIDTH = 405
    TABS_AREA_HEIGHT = 618

    xx = None
    yy = None
    zz = None

    separator = Setting(0)
    skip_rows = Setting(1)
    surface_file_name = Setting('thickness.dat')

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

        input_box_l = oasysgui.widgetBox(self.controlArea, "Input", addSpace=True, orientation="vertical", height=self.TABS_AREA_HEIGHT)

        box = oasysgui.widgetBox(input_box_l, "", addSpace=False, orientation="horizontal")

        self.le_surface_file_name = oasysgui.lineEdit(box, self, "surface_file_name", "Thickness File Name",
                                                        labelWidth=120, valueType=str, orientation="horizontal")

        gui.button(box, self, "...", callback=self.selectSurfaceFile)

        gui.comboBox(input_box_l, self, "separator", label="Separator", labelWidth=350,
                     items=["Comma", "Space"], sendSelectedValue=False, orientation="horizontal")

        gui.lineEdit(input_box_l, self, "skip_rows", label="Skip Rows", labelWidth=350, orientation="horizontal", valueType=int)
        gui.comboBox(input_box_l, self, "negate", label="Invert Surface", labelWidth=350,
                     items=["No", "Yes"], sendSelectedValue=False, orientation="horizontal")

        self.figure = Figure(figsize=(600, 600))
        self.figure.patch.set_facecolor('white')

        self.axis = self.figure.add_subplot(111, projection='3d')

        self.axis.set_zlabel("Z [m]")

        self.figure_canvas = FigureCanvasQTAgg(self.figure)

        self.mainArea.layout().addWidget(self.figure_canvas)

        gui.rubber(self.mainArea)

    def read_surface(self):
        try:
            self.read_data_file()

            #self.send("Surface Data", OasysSurfaceData(xx=self.xx, yy=self.yy, zz=self.zz, surface_data_file=self.surface_file_name))
        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def render_surface(self):
        try:
            self.read_data_file()

            self.axis.clear()

            x_to_plot, y_to_plot = numpy.meshgrid(self.xx, self.yy)

            self.axis.plot_surface(x_to_plot, y_to_plot, self.zz,
                                   rstride=1, cstride=1, cmap=cm.autumn, linewidth=0.5, antialiased=True)

            self.axis.set_xlabel("X [m]")
            self.axis.set_ylabel("Y [m]")
            self.axis.set_zlabel("Z [m]")
            self.axis.mouse_init()

            self.figure_canvas.draw()

            #self.send("Surface Data", OasysSurfaceData(xx=self.xx, yy=self.yy, zz=self.zz, surface_data_file=self.surface_file_name))

        except Exception as exception:
            QMessageBox.critical(self, "Error",
                                 exception.args[0],
                                 QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def selectSurfaceFile(self):
        self.le_surface_file_name.setText(oasysgui.selectFileFromDialog(self, self.surface_file_name, "Select Input File", file_extension_filter="Txt Files (*.txt *.dat)"))


    def read_data_file(self):
        self.surface_file_name = congruence.checkDir(self.surface_file_name)

        data = numpy.loadtxt(self.surface_file_name, delimiter="," if self.separator==0 else " ", skiprows=self.skip_rows)

        xx = numpy.unique(data[:, 0])
        yy = numpy.unique(data[:, 1])

        dim_x = len(xx)
        dim_y = len(yy)

        zz = numpy.zeros((dim_x, dim_y))

        print(xx, yy)
        for i in range(dim_x):
            for j in range(dim_y):
                index = i * dim_x + j

                zz[i, j] = data[index, 2]

        zz = zz if self.negate == 0 else -1.0 * zz

        self.xx = xx
        self.yy = yy
        self.zz = zz
