import os, numpy

from PyQt5.QtWidgets import QWidget, QVBoxLayout

from oasys.widgets import gui as oasysgui

class HistogramData(object):
    scan_value = 0.0
    histogram = None
    bins = None
    offset = 0.0
    xrange = None
    fwhm = 0.0
    sigma = 0.0
    peak_intensity = 0.0

    def __init__(self, histogram=None, bins=None, offset=0.0, xrange=None, fwhm=0.0, sigma=0.0, peak_intensity=0.0, scan_value=0.0):
        self.histogram = histogram
        self.bins = bins
        self.offset = offset
        self.xrange = xrange
        self.fwhm = fwhm
        self.sigma = sigma
        self.peak_intensity = peak_intensity
        self.scan_value = scan_value

    def get_centroid(self):
        return self.xrange[0] + (self.xrange[1] - self.xrange[0])*0.5

class HistogramDataCollection(object):

    data = None

    def __init__(self, histo_data=None):
        super().__init__()

        if not histo_data is None:
            self.add_reference_data(histo_data)

    def add_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]])
        else:
            self.data = self.data.flatten()
            self.data = numpy.insert(self.data, [0, int(len(self.data)/3), int(2*len(self.data)/3)], [[histo_data.scan_value]*len(histo_data.bins), histo_data.bins, histo_data.histogram])
            self.data = self.data.reshape(3, int(len(self.data)/3))

    def replace_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]])
        else:
            self.data[0, 0] = [histo_data.scan_value]*len(histo_data.bins)
            self.data[1, 0] = histo_data.bins
            self.data[2, 0] = histo_data.histogram

    def add_histogram_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]])
        else:
            self.data = numpy.append(self.data, numpy.array([[[histo_data.scan_value]*len(histo_data.bins)], [histo_data.bins], [histo_data.histogram]]), axis=1)

    def get_scan_values(self):
        return self.data[0, :][:, 0]

    def get_positions(self):
        return self.data[1, :]

    def get_intensities(self):
        return self.data[2, :]

    def get_histogram_data_number(self):
        return self.data.shape()[1]

    def get_scan_value(self, index):
        return self.data[0, index][0]

    def get_position(self, index):
        return self.data[1, index]

    def get_intensity(self, index):
        return self.data[2, index]

class StatisticalDataCollection(object):

    data = None

    def __init__(self, histo_data=None):
        super().__init__()

        if not histo_data is None:
            self.add_reference_data(histo_data)

    def add_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity]])
        else:
            self.data = self.data.flatten()
            self.data = numpy.insert(self.data,
                                     [0, int(len(self.data)/4), int(2*len(self.data)/4), int(3*len(self.data)/4)],
                                     [histo_data.scan_value, histo_data.fwhm, histo_data.sigma, histo_data.peak_intensity])
            self.data = self.data.reshape(4, int(len(self.data)/4))

    def replace_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity]])
        else:
            self.data[0, 0] = histo_data.scan_value
            self.data[1, 0] = histo_data.fwhm
            self.data[2, 0] = histo_data.sigma
            self.data[3, 0] = histo_data.peak_intensity

    def add_statistical_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity]])
        else:
            self.data = numpy.append(self.data, numpy.array([[histo_data.scan_value], [histo_data.fwhm], [histo_data.sigma], [histo_data.peak_intensity]]), axis=1)

    def get_scan_values(self):
        return self.data[0, :]

    def get_fwhms(self):
        return self.data[1, :]

    def get_sigmas(self):
        return self.data[2, :]

    def get_relative_intensities(self):
        return self.data[3, :]/self.data[3, 0]

    def get_stats_data_number(self):
        return self.data.shape()[1]

    def get_scan_value(self, index):
        return self.data[0, index]

    def get_fwhm(self, index):
        return self.data[1, index]

    def get_sigma(self, index):
        return self.data[2, index]

    def get_relative_intensity(self, index):
        return self.data[3, index]/self.data[3, 0]



class DoublePlotWidget(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent=parent)

        self.plot_canvas = oasysgui.plotWindow(roi=False, control=False, position=True, logScale=False)
        self.plot_canvas.setFixedWidth(700)
        self.plot_canvas.setFixedHeight(520)

        self.plot_canvas.setDefaultPlotLines(True)
        self.plot_canvas.setDefaultPlotPoints(True)

        self.ax2 = self.plot_canvas._backend.ax.twinx()

        layout = QVBoxLayout()

        layout.addWidget(self.plot_canvas)

        self.setLayout(layout)

    def plotCurves(self, x, y1, y2, title, xlabel, ylabel1, ylabel2):
        self.plot_canvas._backend.ax.clear()
        self.ax2.clear()

        self.plot_canvas.addCurve(x, y1, replace=False, color="b", symbol=".", ylabel=ylabel1, linewidth=1.5)
        self.plot_canvas.setGraphXLabel(xlabel)
        self.plot_canvas.setGraphTitle(title)
        self.plot_canvas._backend.ax.set_ylabel(ylabel1, color="b")

        self.ax2.plot(x, y2, "r.-")
        self.ax2.set_ylabel(ylabel2, color="r")


def write_histo_and_stats_file(histo_data=HistogramDataCollection(),
                               stats=StatisticalDataCollection(),
                               suffix="",
                               output_folder=""):
    for scan_value, positions, intensities in zip(histo_data.get_scan_values(), histo_data.get_positions(), histo_data.get_intensities()):

        file = open(os.path.join(output_folder, "histogram_" + str(scan_value) + suffix + ".dat"), "w")

        for position, intensity in zip(positions, intensities):
            file.write(str(position) + "   " + str(intensity) + "\n")

        file.flush()
        file.close()

    file_fwhm = open(os.path.join(output_folder, "fwhm" + suffix + ".dat"), "w")
    file_sigma = open(os.path.join(output_folder, "sigma" + suffix + ".dat"), "w")
    file_peak_intensity = open(os.path.join(output_folder, "relative_intensity" + suffix + ".dat"), "w")

    for scan_value, fwhm, sigma, peak_intensity in zip(stats.get_scan_values(),
                                                       stats.get_fwhms(),
                                                       stats.get_sigmas(),
                                                       stats.get_relative_intensities()):
        file_fwhm.write(str(scan_value) + "   " + str(fwhm) + "\n")
        file_sigma.write(str(scan_value) + "   " + str(sigma) + "\n")
        file_peak_intensity.write(str(scan_value) + "   " + str(peak_intensity) + "\n")

    file_fwhm.flush()
    file_sigma.flush()
    file_peak_intensity.flush()

    file_fwhm.close()
    file_sigma.close()
    file_peak_intensity.close()

def get_sigma(histogram, bins):
    total = numpy.sum(histogram)
    average = numpy.sum(histogram*bins)/total

    return numpy.sqrt(numpy.sum(histogram*((bins-average)**2))/total)



if __name__=="__main__":
    pass
