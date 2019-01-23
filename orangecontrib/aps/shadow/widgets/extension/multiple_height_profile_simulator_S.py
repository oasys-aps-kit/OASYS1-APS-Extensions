import os

import orangecanvas.resources as resources

try:
    from mpl_toolkits.mplot3d import Axes3D  # necessario per caricare i plot 3D
except:
    pass

from orangecontrib.shadow.util.shadow_objects import ShadowPreProcessorData
from Shadow import ShadowTools as ST

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
                "type": ShadowPreProcessorData,
                "doc": "PreProcessor Data",
                "id": "PreProcessor_Data"},
               {"name":"Files",
                "type":list,
                "doc":"Files",
                "id":"Files"}]

    usage_path = os.path.join(resources.package_dirname("orangecontrib.shadow.widgets.gui"), "misc", "height_error_profile_usage.png")

    def __init__(self):
        super().__init__()

    def after_change_workspace_units(self):
        self.si_to_user_units = 1 / self.workspace_units_to_m

        self.axis.set_xlabel("X [" + self.workspace_units_label + "]")
        self.axis.set_ylabel("Y [" + self.workspace_units_label + "]")

        label = self.le_dimension_y.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_step_y.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_correlation_length_y.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

        label = self.le_dimension_x.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_step_x.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_correlation_length_x.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

        label = self.le_conversion_factor_y_x.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Abscissa)")
        label = self.le_conversion_factor_y_y.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Height Profile Values)")
        label = self.le_conversion_factor_x_x.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Abscissa)")
        label = self.le_conversion_factor_x_y.parent().layout().itemAt(0).widget()
        label.setText("Conversion from file to " + self.workspace_units_label + "\n(Height Profile Values)")

        label = self.le_new_length_y_1.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_new_length_y_2.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_new_length_x_1.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")
        label = self.le_new_length_x_2.parent().layout().itemAt(0).widget()
        label.setText(label.text() + " [" + self.workspace_units_label + "]")

    def get_usage_path(self):
        return self.usage_path

    def write_error_profile_file(self, zz, xx, yy, outFile):
        ST.write_shadow_surface(zz, xx, yy, outFile)

    def send_data(self, height_profile_file_names, dimension_x, dimension_y):
        self.send("PreProcessor_Data", ShadowPreProcessorData(error_profile_data_file=height_profile_file_names,
                                                              error_profile_x_dim=dimension_x,
                                                              error_profile_y_dim=dimension_y))

        self.send("Files", height_profile_file_names)

    def get_file_format(self):
        return ".dat"
