import sys, numpy, os

from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QMessageBox, QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap

import orangecanvas.resources as resources

from orangewidget import gui
from orangewidget.widget import OWAction

from oasys.widgets.exchange import DataExchangeObject
from oasys.widgets import gui as oasysgui

from orangecontrib.shadow.util.shadow_objects import ShadowBeam
from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow.widgets.gui.ow_automatic_element import AutomaticElement

class FluxCalculator(AutomaticElement):

    name = "Flux Calculator"
    description = "Tools: Flux Calculator"
    icon = "icons/flux.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 10
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Shadow Beam", ShadowBeam, "setBeam"),
              ("Spectrum Data", DataExchangeObject, "setSpectrumData")]

    outputs = [{"name":"Beam",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam"}]

    want_main_area = 0
    want_control_area = 1

    input_beam     = None
    input_spectrum = None
    flux_index = -1

    usage_path = os.path.join(resources.package_dirname("orangecontrib.aps.shadow.widgets.extension"), "misc", "flux_calculator.png")

    def __init__(self):
        super(FluxCalculator, self).__init__()

        self.runaction = OWAction("Calculate Flux", self)
        self.runaction.triggered.connect(self.calculate_flux)
        self.addAction(self.runaction)

        self.setMaximumWidth(self.CONTROL_AREA_WIDTH+10)
        self.setMaximumHeight(580)

        box0 = gui.widgetBox(self.controlArea, "", orientation="horizontal")
        gui.button(box0, self, "Calculate Flux", callback=self.calculate_flux, height=45)

        tabs_setting = oasysgui.tabWidget(self.controlArea)
        tabs_setting.setFixedHeight(440)
        tabs_setting.setFixedWidth(self.CONTROL_AREA_WIDTH-8)

        tab_out = oasysgui.createTabPage(tabs_setting, "Flux Calculation Results")
        tab_usa = oasysgui.createTabPage(tabs_setting, "Use of the Widget")
        tab_usa.setStyleSheet("background-color: white;")

        self.text = oasysgui.textArea(width=self.CONTROL_AREA_WIDTH-22, height=400)

        tab_out.layout().addWidget(self.text)

        usage_box = oasysgui.widgetBox(tab_usa, "", addSpace=True, orientation="horizontal")

        label = QLabel("")
        label.setAlignment(Qt.AlignCenter)
        label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        label.setPixmap(QPixmap(self.usage_path))

        usage_box.layout().addWidget(label)





        gui.rubber(self.controlArea)

    def setBeam(self, beam):
        try:
            if ShadowCongruence.checkEmptyBeam(beam):
                if ShadowCongruence.checkGoodBeam(beam):
                    self.input_beam = beam

                    if self.is_automatic_run: self.calculate_flux()
        except Exception as exception:
            QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

            if self.IS_DEVELOP: raise exception

    def setSpectrumData(self, data):
        if not data is None:
            try:
                if data.get_program_name() == "XOPPY":
                    if data.get_widget_name() == "UNDULATOR_FLUX" or data.get_widget_name() == "XWIGGLER" or data.get_widget_name() == "WS":
                        self.flux_index = 1
                    elif data.get_widget_name() == "BM":
                        self.flux_index = 5
                    else:
                        raise Exception("Connect to one of the following XOPPY widgets: Undulator Spectrum, BM, XWIGGLER, WS")

                    self.input_spectrum = data.get_content('xoppy_data')
                elif data.get_program_name() == "SRW":
                    if data.get_widget_name() == "UNDULATOR_SPECTRUM":
                        self.flux_index = 1
                    else:
                        raise Exception("Connect to one of the following SRW widgets: Undulator Spectrum")

                    self.input_spectrum = data.get_content('srw_data')
                else:
                    raise ValueError("Widget accept data from the following Add-ons: XOPPY, SRW")

                if self.is_automatic_run: self.calculate_flux()
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

    def calculate_flux(self):
        if not self.input_beam is None and not self.input_spectrum is None:
            try:
                flux_factor, resolving_power, energy, ttext = calculate_flux_factor_and_resolving_power(self.input_beam)

                total_text = ttext

                flux_at_sample, ttext = calculate_flux_at_sample(self.input_spectrum, self.flux_index, flux_factor, energy)

                total_text += "\n" + ttext

                total_text += "\n\n ---> Flux at Image Plane : %g"%flux_at_sample + " ph/s"
                total_text += "\n ---> Resolving Power: %g"%resolving_power

                self.text.clear()
                self.text.setText(total_text)

                self.send("Beam", self.input_beam)
            except Exception as exception:
                QMessageBox.critical(self, "Error", str(exception), QMessageBox.Ok)

                if self.IS_DEVELOP: raise exception

def calculate_flux_factor_and_resolving_power(beam):
    ticket = beam._beam.histo1(11, nbins=2, nolost=1)

    energy_min = ticket['xrange'][0]
    energy_max = ticket['xrange'][-1]

    Denergy_source = numpy.abs(energy_max - energy_min)
    energy = numpy.average([energy_min, energy_max])

    if Denergy_source == 0.0:
        raise ValueError("This calculation is not possibile for a single energy value")

    ticket = beam._beam.histo1(11, nbins=200, nolost=1, ref=23)

    initial_intensity = len(beam._beam.rays)
    final_intensity = ticket['intensity']
    efficiency = final_intensity/initial_intensity
    bandwidth = ticket['fwhm']

    if bandwidth == 0.0:
        raise ValueError("Bandwidth is 0.0: calculation not possible")

    resolving_power = energy/bandwidth

    if Denergy_source < 4*bandwidth:
        raise ValueError("Source \u0394E (" + str(round(Denergy_source, 2)) + " eV) should be at least 4 times bigger than the bandwidth (" + str(round(bandwidth, 3)) + " eV)")

    text = "\n# SOURCE ---------\n"
    text += "\n Source Central Energy: %g"%round(energy, 2) + " eV"
    text += "\n Source Energy Range  : %g - %g"%(round(energy_min, 2), round(energy_max, 2)) + " eV"
    text += "\n Source \u0394E: %g"%round(Denergy_source, 2) + " eV"

    text += "\n\n# BEAMLINE ---------\n"
    text += "\n Shadow Intensity (Initial): %g"%initial_intensity
    text += "\n Shadow Intensity (Final)  : %g"%final_intensity
    text += "\n"
    text += "\n Efficiency: %g"%round(100*efficiency, 3) + "%"
    text += "\n Bandwidth (at the Image Plane): %g"%round(bandwidth, 3) + " eV"

    beamline_bandwidth = Denergy_source * efficiency

    flux_factor = beamline_bandwidth / (1e-3*energy)

    return flux_factor, resolving_power, energy, text

def calculate_flux_at_sample(spectrum, flux_index, flux_factor, energy):
    index_up = numpy.where(spectrum[:, 0] >= energy)
    index_down = numpy.where(spectrum[:, 0] < energy)

    flux_up = spectrum[index_up, flux_index][0, 0]
    flux_down = spectrum[index_down, flux_index][0, -1]

    interpolated_flux = (flux_up + flux_down)/2

    text = "\n# FLUX INTERPOLATION ---------\n"
    text += "\n Energy range: %g - %g"%(spectrum[index_down, 0][0, -1], spectrum[index_up, 0][0, 0]) + " eV"
    text += "\n Spectral Flux Density: %g"%interpolated_flux + " ph/s/0.1%bw"

    return interpolated_flux*flux_factor, text


if __name__ == "__main__":
    a = QtGui.QApplication(sys.argv)
    ow = FluxCalculator()
    ow.show()
    a.exec_()
    ow.saveSettings()


