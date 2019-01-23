import os

import orangecanvas.resources as resources

try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

from orangecontrib.srw.util.srw_objects import SRWPreProcessorData, SRWErrorProfileData
import orangecontrib.srw.util.srw_util as SU

from orangecontrib.aps.oasys.widgets.error_profile.abstract_multiple_height_profile_simulator_S import OWAbstractMultipleHeightProfileSimulatorS

class OWMultipleHeightProfileSimulatorS(OWAbstractMultipleHeightProfileSimulatorS):
    name = "Multiple Height Profile Simulator (S)"
    id = "height_profile_simulator_s"
    icon = "icons/simulator_S.png"
    description = "Calculation of mirror surface height profile"
    author = "Luca Rebuffi"
    maintainer_email = "lrebuffi@anl.gov"
    priority = 4
    category = ""
    keywords = ["height_profile_simulator"]

    outputs = [{"name": "PreProcessor_Data",
                "type": SRWPreProcessorData,
                "doc": "PreProcessor Data",
                "id": "PreProcessor_Data"},
               {"name":"Files",
                "type":list,
                "doc":"Files",
                "id":"Files"}]

    usage_path = os.path.join(resources.package_dirname("orangecontrib.srw.widgets.gui"), "misc", "height_error_profile_usage.png")

    def __init__(self):
        super().__init__()

    def get_usage_path(self):
        return self.usage_path

    def write_error_profile_file(self, zz, xx, yy, outFile):
        SU.write_error_profile_file(zz, xx, yy, outFile)

    def send_data(self, height_profile_file_names, dimension_x, dimension_y):
        self.send("PreProcessor_Data", SRWPreProcessorData(error_profile_data=SRWErrorProfileData(error_profile_data_file=height_profile_file_names,
                                                                                                  error_profile_x_dim=dimension_x,
                                                                                                  error_profile_y_dim=dimension_y)))
        self.send("Files", height_profile_file_names)

    def get_file_format(self):
        return ".dat"
