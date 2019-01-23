import os

import orangecanvas.resources as resources

try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

from oasys.util.oasys_objects import OasysPreProcessorData, OasysErrorProfileData, OasysSurfaceData
import oasys.util.oasys_util as OU

from orangecontrib.aps.oasys.widgets.error_profile.abstract_multiple_height_profile_simulator_T import OWAbstractMultipleHeightProfileSimulatorT

class OWMultipleHeightProfileSimulatorT(OWAbstractMultipleHeightProfileSimulatorT):
    name = "Multiple Height Profile Simulator (T)"
    id = "height_profile_simulator_t"
    icon = "icons/simulator_T.png"
    description = "Calculation of mirror surface height profile"
    author = "Luca Rebuffi"
    maintainer_email = "lrebuffi@anl.gov"
    priority = 1
    category = ""
    keywords = ["height_profile_simulator"]

    outputs = [{"name": "PreProcessor_Data",
                "type": OasysPreProcessorData,
                "doc": "PreProcessor Data",
                "id": "PreProcessor_Data"},
               {"name":"Files",
                "type":list,
                "doc":"Files",
                "id":"Files"}]

    usage_path = os.path.join(resources.package_dirname("orangecontrib.shadow.widgets.gui"), "misc", "height_error_profile_usage.png")

    def __init__(self):
        super().__init__()

    def get_usage_path(self):
        return self.usage_path

    def write_error_profile_file(self, zz, xx, yy, outFile):
        OU.write_surface_file(zz, xx, yy, outFile)

    def send_data(self, height_profile_file_names, dimension_x, dimension_y):
        self.send("PreProcessor_Data", OasysPreProcessorData(error_profile_data=OasysErrorProfileData(surface_data=OasysSurfaceData(xx=self.xx,
                                                                                                                                    yy=self.yy,
                                                                                                                                    zz=self.zz,
                                                                                                                                    surface_data_file=height_profile_file_names),
                                                                                                      error_profile_x_dim=dimension_x,
                                                                                                      error_profile_y_dim=dimension_y)))


        self.send("Files", height_profile_file_names)
