import numpy
import scipy.constants as codata
import srwlib

codata_mee = numpy.array(codata.physical_constants["electron mass energy equivalent in MeV"][0])
m2ev = codata.c * codata.h / codata.e      # lambda(m)  = m2eV / energy(eV)

from oasys.widgets import widget
from oasys.widgets import gui as oasysgui

from orangewidget import gui
from PyQt5 import QtGui
from orangewidget.settings import Setting

from orangecontrib.shadow.util.shadow_objects import ShadowBeam

class LoopPoint(widget.OWWidget):

    name = "Power Calculator"
    description = "Tools: Power Calculator"
    icon = "icons/power_calculator.png"
    maintainer = "Luca Rebuffi"
    maintainer_email = "lrebuffi(@at@)anl.gov"
    priority = 5
    category = "User Defined"
    keywords = ["data", "file", "load", "read"]

    inputs = [("Input Beam", ShadowBeam, "setBeam")]

    outputs = [{"name":"Beam",
                "type":ShadowBeam,
                "doc":"Shadow Beam",
                "id":"beam"}]

    want_main_area = 0

    def __init__(self):
        oasysgui.widgetBox(self.controlArea, "Power Calculation", addSpace=True, orientation="vertical", width=380, height=120)

        gui.rubber(self.controlArea)

    def setBeam(self, input_beam):
        if input_beam.scanned_variable_data:

            photon_energy      = input_beam.scanned_variable_data.get_scanned_variable_value()
            photon_energy_step = input_beam.scanned_variable_data.get_additional_parameter("photon_energy_step")

            if input_beam.scanned_variable_data.has_additional_parameter("intensity_arrays"):
                h_array, v_array, intensity_array = input_beam.scanned_variable_data.get_additional_parameter("intensity_arrays")

                h_array *= self.workspace_units_to_mm
                v_array *= self.workspace_units_to_mm

                power_density_array, total_power = self.calculate_power(h_array,
                                                                        v_array,
                                                                        intensity_array,
                                                                        photon_energy_step)
            else:
                h_array, v_array, intensity_array, power_density_array, total_power = self.calc2d_srw(photon_energy, photon_energy_step, input_beam.scanned_variable_data)

            additional_parameters = {}
            additional_parameters["total_power"] = total_power
            additional_parameters["photon_energy_step"] = photon_energy_step

            input_beam.setScanningData(ShadowBeam.ScanningData(input_beam.scanned_variable_data.get_scanned_variable_name(),
                                                               photon_energy,
                                                               input_beam.scanned_variable_data.get_scanned_variable_display_name(),
                                                               input_beam.scanned_variable_data.get_scanned_variable_um(),
                                                               additional_parameters))

        self.send("Beam", input_beam)

    def calc2d_srw(self, photon_energy, photon_energy_step, scanning_data):

        Kv = scanning_data.get_additional_parameter("Kv")
        Kh = scanning_data.get_additional_parameter("Kh")
        period_id = scanning_data.get_additional_parameter("period_id")
        n_periods = scanning_data.get_additional_parameter("n_periods")

        B0v = Kv/period_id/(codata.e/(2*numpy.pi*codata.electron_mass*codata.c))
        B0h = Kh/period_id/(codata.e/(2*numpy.pi*codata.electron_mass*codata.c))

        eBeam = srwlib.SRWLPartBeam()

        eBeam.Iavg               = scanning_data.get_additional_parameter("electron_current")
        eBeam.partStatMom1.gamma = scanning_data.get_additional_parameter("electron_energy") / (codata_mee * 1e-3)
        eBeam.partStatMom1.relE0 = 1.0
        eBeam.partStatMom1.nq    = -1
        eBeam.partStatMom1.x  = 0.0
        eBeam.partStatMom1.y  = 0.0
        eBeam.partStatMom1.z  = -0.5*period_id*n_periods + 4
        eBeam.partStatMom1.xp = 0.0
        eBeam.partStatMom1.yp = 0.0
        eBeam.arStatMom2[ 0] = scanning_data.get_additional_parameter("electron_beam_size_h") ** 2
        eBeam.arStatMom2[ 1] = 0.0
        eBeam.arStatMom2[ 2] = scanning_data.get_additional_parameter("electron_beam_divergence_h") ** 2
        eBeam.arStatMom2[ 3] = scanning_data.get_additional_parameter("electron_beam_size_v") ** 2
        eBeam.arStatMom2[ 4] = 0.0
        eBeam.arStatMom2[ 5] = scanning_data.get_additional_parameter("electron_beam_divergence_v") ** 2
        eBeam.arStatMom2[10] = scanning_data.get_additional_parameter("electron_energy_spread") ** 2

        gap_h                = scanning_data.get_additional_parameter("gap_h")
        gap_v                = scanning_data.get_additional_parameter("gap_v")

        mesh = srwlib.SRWLRadMesh(photon_energy,
                                  photon_energy,
                                  1,
                                  -gap_h / 2, gap_h / 2, scanning_data.get_additional_parameter("h_slits_points"),
                                  -gap_v / 2, gap_v / 2, scanning_data.get_additional_parameter("v_slits_points"),
                                  scanning_data.get_additional_parameter("distance"))

        srw_magnetic_fields = []
        if B0v > 0: srw_magnetic_fields.append(srwlib.SRWLMagFldH(1, "v", B0v))
        if B0h > 0: srw_magnetic_fields.append(srwlib.SRWLMagFldH(1, "h", B0h))

        magnetic_structure = srwlib.SRWLMagFldC([srwlib.SRWLMagFldU(srw_magnetic_fields, period_id, n_periods)],
                                                srwlib.array("d", [0]), srwlib.array("d", [0]), srwlib.array("d", [0]))

        wfr = srwlib.SRWLWfr()
        wfr.mesh = mesh
        wfr.partBeam = eBeam
        wfr.allocate(mesh.ne, mesh.nx, mesh.ny)

        srwlib.srwl.CalcElecFieldSR(wfr, 0, magnetic_structure, [1, 0.01, 0, 0, 50000, 1, 0])

        mesh_out = wfr.mesh

        h_array=numpy.linspace(mesh_out.xStart, mesh_out.xFin, mesh_out.nx)*1e3 # in mm
        v_array=numpy.linspace(mesh_out.yStart, mesh_out.yFin, mesh_out.ny)*1e3 # in mm

        intensity_array = numpy.zeros((h_array.size, v_array.size,))

        arI0 = srwlib.array("f", [0]*mesh_out.nx*mesh_out.ny) #"flat" array to take 2D intensity data

        srwlib.srwl.CalcIntFromElecField(arI0, wfr, 6, 1, 3, photon_energy, 0, 0)

        data = numpy.ndarray(buffer=arI0, shape=(mesh_out.ny, mesh_out.nx),dtype=arI0.typecode)

        for ix in range(h_array.size):
            for iy in range(v_array.size):
                intensity_array[ix, iy] = data[iy,ix]

        power_density_array, total_power = self.calculate_power(h_array, v_array, intensity_array, photon_energy_step)

        return h_array, v_array, intensity_array, power_density_array, total_power

    def calculate_power(self, h_array, v_array, intensity_array, photon_energy_step):

        # intensity_array = intensity_array * photon_energy_step / (1e-3*photon_energy) -> intensity in the photon energy step (from 01.%BW)
        # power_density_array = intensity_array * photon_energy * codata.e -> power in the photon energy step in Watt

        power_density_array = intensity_array * (1e3 * photon_energy_step * codata.e)

        total_power = 0.0

        dx = h_array[1] - h_array[0]
        dy = v_array[1] - v_array[0]
        for j in range(len(v_array)):
            for i in range(len(h_array)):
                total_power += power_density_array[i, j] * dx * dy

        return power_density_array, total_power
