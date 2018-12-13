import os, numpy

from PyQt5 import QtGui, QtWidgets
from orangewidget import gui
from orangewidget.settings import Setting
from oasys.widgets import gui as oasysgui, congruence
from oasys.widgets import widget as oasyswidget

from orangecontrib.shadow.util.shadow_util import ShadowCongruence
from orangecontrib.shadow.util.shadow_objects import ShadowBeam, ShadowOpticalElement, ShadowOEHistoryItem


class FootprintFileReader(oasyswidget.OWWidget):
    name = "Footprint File Reader"
    description = "Utility: Footprint File Reader"
    icon = "icons/beam_file_reader.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "Utility"
    keywords = ["data", "file", "load", "read"]

    want_main_area = 0

    beam_file_name = None
    input_beam = None

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    outputs = [{"name": "Beam",
                "type": ShadowBeam,
                "doc": "Shadow Beam",
                "id": "beam"}, ]

    kind_of_power = Setting(0)

    def __init__(self):
        super().__init__()

        self.setFixedWidth(590)
        self.setFixedHeight(150)

        left_box_1 = oasysgui.widgetBox(self.controlArea, "Footprint Settings", addSpace=True, orientation="vertical",
                                         width=570, height=120)

        self.le_beam_file_name = oasysgui.lineEdit(left_box_1, self, "beam_file_name", "Shadow File Name", labelWidth=120, valueType=str, orientation="horizontal")
        self.le_beam_file_name.setReadOnly(True)
        font = QtGui.QFont(self.le_beam_file_name.font())
        font.setBold(True)
        self.le_beam_file_name.setFont(font)
        palette = QtGui.QPalette(self.le_beam_file_name.palette()) # make a copy of the palette
        palette.setColor(QtGui.QPalette.Text, QtGui.QColor('dark blue'))
        palette.setColor(QtGui.QPalette.Base, QtGui.QColor(243, 240, 160))
        self.le_beam_file_name.setPalette(palette)

        gui.comboBox(left_box_1, self, "kind_of_power", label="Kind Of Power",
                     items=["Incident", "Absorbed", "Transmitted"], labelWidth=260, sendSelectedValue=False, orientation="horizontal")


        gui.rubber(self.controlArea)

    def setBeam(self, beam):
        if ShadowCongruence.checkEmptyBeam(beam) and ShadowCongruence.checkGoodBeam(beam):
            if beam.scanned_variable_data and beam.scanned_variable_data.has_additional_parameter("total_power"):
                self.input_beam = beam

                self.beam_file_name = "mirr." + (str(beam._oe_number) if beam._oe_number > 9 else "0" + str(beam._oe_number))

                self.read_file()

    def read_file(self):
        self.setStatusMessage("")

        try:
            if congruence.checkFileName(self.beam_file_name):
                beam_out = ShadowBeam()
                beam_out.loadFromFile(self.beam_file_name)
                beam_out.history.append(ShadowOEHistoryItem()) # fake Source
                beam_out._oe_number = 0

                # just to create a safe history for possible re-tracing
                beam_out.traceFromOE(beam_out, self.create_dummy_oe(), history=True)

                path, file_name = os.path.split(self.beam_file_name)

                self.setStatusMessage("Current: " + file_name)

                total_power = self.input_beam.scanned_variable_data.get_additional_parameter("total_power")

                additional_parameters = {}
                additional_parameters["total_power"]        = total_power
                additional_parameters["photon_energy_step"] = self.input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")
                additional_parameters["is_footprint"] = True

                n_rays = len(beam_out._beam.rays[:, 0]) # lost and good!

                history_entry =  self.input_beam.getOEHistory(self.input_beam._oe_number)

                incident_beam = history_entry._input_beam

                ticket = incident_beam._beam.histo2(2, 1, nbins=100, xrange=None, yrange=None, nolost=1, ref=23)
                ticket['histogram'] *= (total_power/n_rays) # power

                additional_parameters["incident_power"] = ticket['histogram'].sum()

                if self.kind_of_power == 0: # incident
                    beam_out._beam.rays[:, 6]  = incident_beam._beam.rays[:, 6]
                    beam_out._beam.rays[:, 7]  = incident_beam._beam.rays[:, 7]
                    beam_out._beam.rays[:, 8]  = incident_beam._beam.rays[:, 8]
                    beam_out._beam.rays[:, 15] = incident_beam._beam.rays[:, 15]
                    beam_out._beam.rays[:, 16] = incident_beam._beam.rays[:, 16]
                    beam_out._beam.rays[:, 17] = incident_beam._beam.rays[:, 17]
                elif self.kind_of_power == 1: # absorbed
                    # need a trick: put the whole intensity of one single component
                    
                    incident_intensity = incident_beam._beam.rays[:, 6]**2 + incident_beam._beam.rays[:, 7]**2 + incident_beam._beam.rays[:, 8]**2 +\
                                         incident_beam._beam.rays[:, 15]**2 + incident_beam._beam.rays[:, 16]**2 + incident_beam._beam.rays[:, 17]**2
                    transmitted_intensity = beam_out._beam.rays[:, 6]**2 + beam_out._beam.rays[:, 7]**2 + beam_out._beam.rays[:, 8]**2 +\
                                            beam_out._beam.rays[:, 15]**2 + beam_out._beam.rays[:, 16]**2 + beam_out._beam.rays[:, 17]**2

                    electric_field = numpy.sqrt(incident_intensity - transmitted_intensity)

                    electric_field[numpy.where(electric_field == numpy.nan)] = 0.0

                    beam_out._beam.rays[:, 6]  = electric_field
                    beam_out._beam.rays[:, 7]  = 0.0
                    beam_out._beam.rays[:, 8]  = 0.0
                    beam_out._beam.rays[:, 15] = 0.0
                    beam_out._beam.rays[:, 16] = 0.0
                    beam_out._beam.rays[:, 17] = 0.0

                beam_out.setScanningData(ShadowBeam.ScanningData(self.input_beam.scanned_variable_data.get_scanned_variable_name(),
                                                                 self.input_beam.scanned_variable_data.get_scanned_variable_value(),
                                                                 self.input_beam.scanned_variable_data.get_scanned_variable_display_name(),
                                                                 self.input_beam.scanned_variable_data.get_scanned_variable_um(),
                                                                 additional_parameters))
                self.send("Beam", beam_out)
        except Exception as exception:
            QtWidgets.QMessageBox.critical(self, "Error",
                                       str(exception), QtWidgets.QMessageBox.Ok)


    def create_dummy_oe(self):
        empty_element = ShadowOpticalElement.create_empty_oe()

        empty_element._oe.DUMMY = self.workspace_units_to_cm

        empty_element._oe.T_SOURCE     = 0.0
        empty_element._oe.T_IMAGE = 0.0
        empty_element._oe.T_INCIDENCE  = 0.0
        empty_element._oe.T_REFLECTION = 180.0
        empty_element._oe.ALPHA        = 0.0

        empty_element._oe.FWRITE = 3
        empty_element._oe.F_ANGLE = 0

        return empty_element
