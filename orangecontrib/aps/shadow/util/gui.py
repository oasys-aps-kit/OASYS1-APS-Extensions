import os, numpy

from PyQt5.QtGui import QImage, QPixmap,  QPalette, QFont, QColor, QTextCursor
from PyQt5.QtWidgets import QLabel, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt

from oasys.widgets import gui as oasysgui

from orangecontrib.shadow.util.shadow_util import ShadowPlot

class HistogramData(object):
    scan_value = 0.0
    histogram = None
    bins = None
    offset = 0.0
    xrange = None
    sigma = 0.0
    peak_intensity = 0.0

    def __init__(self, histogram=None, bins=None, offset=0.0, xrange=None, sigma=0.0, peak_intensity=0.0, scan_value=0.0):
        self.histogram = histogram
        self.bins = bins
        self.offset = offset
        self.xrange = xrange
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
            self.data = numpy.array([[histo_data.scan_value], [histo_data.sigma], [histo_data.peak_intensity]])
        else:
            self.data = self.data.flatten()
            self.data = numpy.insert(self.data, [0, int(len(self.data)/3), int(2*len(self.data)/3)], [histo_data.scan_value, histo_data.sigma, histo_data.peak_intensity])
            self.data = self.data.reshape(3, int(len(self.data)/3))

    def replace_reference_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.sigma], [histo_data.peak_intensity]])
        else:
            self.data[0, 0] = histo_data.scan_value
            self.data[1, 0] = histo_data.sigma
            self.data[2, 0] = histo_data.peak_intensity

    def add_statistical_data(self, histo_data=HistogramData()):
        if self.data is None:
            self.data = numpy.array([[histo_data.scan_value], [histo_data.sigma], [histo_data.peak_intensity]])
        else:
            self.data = numpy.append(self.data, numpy.array([[histo_data.scan_value], [histo_data.sigma], [histo_data.peak_intensity]]), axis=1)

    def get_scan_values(self):
        return self.data[0, :]

    def get_sigmas(self):
        return self.data[1, :]

    def get_relative_intensities(self):
        return self.data[2, :]/self.data[2, 0]

    def get_stats_data_number(self):
        return self.data.shape()[1]

    def get_scan_value(self, index):
        return self.data[0, index]

    def get_sigma(self, index):
        return self.data[1, index]

    def get_relative_intensity(self, index):
        return self.data[2, index]/self.data[2, 0]

class ScanHistoWidget(QWidget):

    def __init__(self, workspace_units_to_cm):
        super(ScanHistoWidget, self).__init__()

        self.workspace_units_to_cm=workspace_units_to_cm

        self.plot_canvas = oasysgui.plotWindow(parent=None,
                                               backend=None,
                                               resetzoom=True,
                                               autoScale=False,
                                               logScale=False,
                                               grid=True,
                                               curveStyle=True,
                                               colormap=False,
                                               aspectRatio=False,
                                               yInverted=False,
                                               copy=True,
                                               save=True,
                                               print_=True,
                                               control=True,
                                               position=True,
                                               roi=False,
                                               mask=False,
                                               fit=False)

        layout = QVBoxLayout()

        layout.addWidget(self.plot_canvas)

        self.setLayout(layout)

    def plot_histo(self,
                   beam,
                   col,
                   nbins=100,
                   title="",
                   xtitle="",
                   ytitle="",
                   histo_index=0,
                   scan_variable_name="Variable",
                   scan_variable_value=0,
                   offset=0.0,
                   xrange=None):

        factor=ShadowPlot.get_factor(col, conv=self.workspace_units_to_cm)

        if histo_index==0:
            ticket = beam._beam.histo1(col, xrange=None, nbins=nbins, nolost=1, ref=23)

            fwhm = ticket['fwhm']
            xrange = ticket['xrange']
            centroid = xrange[0] + (xrange[1] - xrange[0])*0.5
            xrange = [centroid - 2*fwhm , centroid + 2*fwhm]

        ticket = beam._beam.histo1(col, xrange=xrange, nbins=nbins, nolost=1, ref=23)

        if not ytitle is None:  ytitle = ytitle + ' weighted by ' + ShadowPlot.get_shadow_label(23)

        histogram = ticket['histogram_path']
        bins = ticket['bin_path']*factor

        histogram_stats = ticket['histogram']
        bins_stats = ticket['bin_center']

        sigma =  numpy.average(ticket['histogram_sigma'])
        peak_intensity = numpy.average(histogram_stats[numpy.where(histogram_stats>=numpy.max(histogram_stats)*0.85)])

        if histo_index==0:
            h_title = "Reference"
        else:
            h_title = scan_variable_name + ": " + str(scan_variable_value)

        color="#000000"

        import matplotlib
        matplotlib.rcParams['axes.formatter.useoffset']='False'

        if histo_index== 0:
            offset = int(peak_intensity*0.3)

        self.plot_canvas.addCurve(bins, histogram + offset*histo_index, h_title, symbol='', color=color, xlabel=xtitle, ylabel=ytitle, replace=False) #'+', '^', ','

        self.plot_canvas._backend.ax.text(xrange[0]*factor*1.05, offset*histo_index*1.05, h_title)

        if not xtitle is None: self.plot_canvas.setGraphXLabel(xtitle)
        if not ytitle is None: self.plot_canvas.setGraphYLabel(ytitle)
        if not title is None:  self.plot_canvas.setGraphTitle(title)

        for label in self.plot_canvas._backend.ax.yaxis.get_ticklabels():
            label.set_color('white')
            label.set_fontsize(1)

        self.plot_canvas.setActiveCurveColor(color="#00008B")

        self.plot_canvas.setDrawModeEnabled(True, 'rectangle')
        self.plot_canvas.setInteractiveMode('zoom',color='orange')
        self.plot_canvas.resetZoom()
        self.plot_canvas.replot()

        self.plot_canvas.setGraphXLimits(xrange[0]*factor, xrange[1]*factor)

        self.plot_canvas.setActiveCurve(h_title)

        self.plot_canvas.setDefaultPlotLines(True)
        self.plot_canvas.setDefaultPlotPoints(False)

        self.plot_canvas.getLegendsDockWidget().setFixedHeight(510)
        self.plot_canvas.getLegendsDockWidget().setVisible(True)

        self.plot_canvas.addDockWidget(Qt.RightDockWidgetArea, self.plot_canvas.getLegendsDockWidget())

        return HistogramData(histogram_stats, bins_stats, offset, xrange, sigma, peak_intensity)

    def add_empty_curve(self, histo_data):
        self.plot_canvas.addCurve(numpy.array([histo_data.get_centroid()]),
                                  numpy.zeros(1),
                                 "Click on curve to highlight it",
                                  xlabel="",
                                  ylabel="",
                                  symbol='',
                                  color='white')

        self.plot_canvas.setActiveCurve("Click on curve to highlight it")

class DoublePlotWidget(QWidget):

    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent=parent)

        self.plot_canvas = oasysgui.plotWindow(parent=None,
                                               backend=None,
                                               resetzoom=False,
                                               autoScale=False,
                                               logScale=False,
                                               grid=True,
                                               curveStyle=False,
                                               colormap=False,
                                               aspectRatio=False,
                                               yInverted=False,
                                               copy=False,
                                               save=True,
                                               print_=True,
                                               control=True,
                                               position=False,
                                               roi=False,
                                               mask=False,
                                               fit=False)
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

    file_sigma = open(os.path.join(output_folder, "sigma" + suffix + ".dat"), "w")
    file_peak_intensity = open(os.path.join(output_folder, "relative_intensity" + suffix + ".dat"), "w")

    for histogram_number, sigma, peak_intensity in zip(stats.get_scan_values(),
                                                       stats.get_sigmas(),
                                                       stats.get_relative_intensities()):
        file_sigma.write(str(histogram_number) + "   " + str(sigma) + "\n")
        file_peak_intensity.write(str(histogram_number) + "   " + str(peak_intensity) + "\n")

    file_sigma.flush()
    file_peak_intensity.close()


if __name__=="__main__":
    stats = StatisticalDataCollection()

    stats.add_statistical_data(HistogramData(scan_value=1, sigma=1, peak_intensity=10))
    stats.add_statistical_data(HistogramData(scan_value=2, sigma=2, peak_intensity=20))
    stats.add_statistical_data(HistogramData(scan_value=3, sigma=3, peak_intensity=30))
    stats.add_statistical_data(HistogramData(scan_value=4, sigma=4, peak_intensity=40))

    print(stats.get_scan_values())
    print(stats.get_sigmas())
    print(stats.get_relative_intensities())

    stats.add_reference_data(HistogramData(scan_value=0, sigma=0, peak_intensity=1))

    print(stats.get_scan_values())
    print(stats.get_sigmas())
    print(stats.get_relative_intensities())

    stats.add_statistical_data(HistogramData(scan_value=5, sigma=5, peak_intensity=50))
    stats.add_statistical_data(HistogramData(scan_value=6, sigma=6, peak_intensity=60))

    print(stats.get_scan_values())
    print(stats.get_sigmas())
    print(stats.get_relative_intensities())

    stats.replace_reference_data(HistogramData(scan_value=0, sigma=0, peak_intensity=2))

    print(stats.get_scan_values())
    print(stats.get_sigmas())
    print(stats.get_relative_intensities())

    histos = HistogramDataCollection()

    histos.add_histogram_data(HistogramData(scan_value=1, bins=[1, 2, 3], histogram=[10, 20, 30]))
    histos.add_histogram_data(HistogramData(scan_value=2, bins=[1, 2, 3], histogram=[10, 20, 30]))
    histos.add_histogram_data(HistogramData(scan_value=3, bins=[1, 2, 3], histogram=[10, 20, 30]))
    histos.add_histogram_data(HistogramData(scan_value=4, bins=[1, 2, 3], histogram=[10, 20, 30]))

    print(histos.get_scan_values())
    print(histos.get_positions())
    print(histos.get_intensities())


