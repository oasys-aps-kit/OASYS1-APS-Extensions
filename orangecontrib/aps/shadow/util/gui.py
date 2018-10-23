import sys, os, numpy

from PyQt5.QtGui import QImage, QPixmap,  QPalette, QFont, QColor, QTextCursor
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtCore import Qt

from matplotlib import cm, rcParams
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.collections import PolyCollection, LineCollection
from matplotlib.colors import colorConverter, ListedColormap

from oasys.widgets import gui as oasysgui

from orangecontrib.shadow.util.shadow_util import ShadowPlot

try:
    from mpl_toolkits.mplot3d import Axes3D  # mandatory to load 3D plot
except:
    pass

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


class AbstractScanHistoWidget(QWidget):

    def __init__(self, workspace_units_to_cm):
        super(AbstractScanHistoWidget, self).__init__()

        self.workspace_units_to_cm=workspace_units_to_cm

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
                   xrange=None,
                   show_reference=True,
                   add_labels=True,
                   has_colormap=True,
                   colormap=cm.rainbow):
        raise NotImplementedError("this methid is abstract")


class Scan3DHistoWidget(AbstractScanHistoWidget):
    class PlotType:
        LINES = 0
        SURFACE = 1

    def __init__(self, workspace_units_to_cm, image_height=645, image_width=860, type=PlotType.LINES):
        super(Scan3DHistoWidget, self).__init__(workspace_units_to_cm)

        self.figure = Figure(figsize=(image_height, image_width))
        self.figure.patch.set_facecolor('white')

        self.axis = self.figure.add_subplot(111, projection='3d')
        self.axis.set_title("")
        self.axis.clear()

        self.colorbar = None

        self.plot_canvas = FigureCanvasQTAgg(self.figure)

        layout = QVBoxLayout()

        layout.addWidget(self.plot_canvas)

        self.setLayout(layout)

        self.xx = None
        self.yy = None
        self.zz = None

        self.title = ""
        self.xlabel = ""
        self.ylabel = ""
        self.zlabel = ""

        self.__type=type
        self.__cc = lambda arg: colorConverter.to_rgba(arg, alpha=0.5)

    def clear(self):
        self.reset_plot()
        try:
            self.plot_canvas.draw()
        except:
            pass

    def reset_plot(self):
        self.xx = None
        self.yy = None
        self.zz = None
        self.axis.set_title("")
        self.axis.clear()

    def set_labels(self, title, xlabel, ylabel, zlabel):
        self.title = title
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.zlabel = zlabel

    def restore_labels(self):
        self.axis.set_title(self.title)
        self.axis.set_xlabel(self.xlabel)
        self.axis.set_ylabel(self.ylabel)
        self.axis.set_zlabel(self.zlabel)

    def set_xrange(self, xrange):
            self.xx = xrange


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
                   xrange=None,
                   show_reference=True,
                   add_labels=True,
                   has_colormap=True,
                   colormap=cm.rainbow):
        factor=ShadowPlot.get_factor(col, conv=self.workspace_units_to_cm)

        if histo_index==0 and xrange is None:
            ticket = beam._beam.histo1(col, xrange=None, nbins=nbins, nolost=1, ref=23)

            fwhm = ticket['fwhm']
            xrange = ticket['xrange']
            centroid = xrange[0] + (xrange[1] - xrange[0])*0.5

            if not fwhm is None:
                xrange = [centroid - 2*fwhm , centroid + 2*fwhm]

        ticket = beam._beam.histo1(col, xrange=xrange, nbins=nbins, nolost=1, ref=23)

        if not ytitle is None:  ytitle = ytitle + ' weighted by ' + ShadowPlot.get_shadow_label(23)

        histogram = ticket['histogram_path']
        bins = ticket['bin_path']*factor

        histogram_stats = ticket['histogram']
        bins_stats = ticket['bin_center']

        fwhm = ticket['fwhm']*factor
        sigma = get_sigma(histogram_stats, bins_stats)*factor

        peak_intensity = numpy.average(histogram_stats[numpy.where(histogram_stats>=numpy.max(histogram_stats)*0.85)])

        rcParams['axes.formatter.useoffset']='False'

        self.set_xrange(bins)
        self.set_labels(title=title, xlabel=xtitle, ylabel=scan_variable_name, zlabel=ytitle)

        self.add_histo(scan_variable_value, histogram, has_colormap, colormap, histo_index)

        return HistogramData(histogram_stats, bins_stats, 0.0, xrange, fwhm, sigma, peak_intensity)

    def add_histo(self, scan_value, intensities, has_colormap, colormap, histo_index):
            if self.xx is None: raise ValueError("Initialize X range first")
            if self.xx.shape != intensities.shape: raise ValueError("Given Histogram has a different binning")

            self.yy = numpy.array([scan_value]) if self.yy is None else numpy.append(self.yy, scan_value)

            if self.zz is None:
                self.zz = numpy.array([intensities])
            else:
                self.zz = numpy.append(self.zz, intensities)

            self.axis.clear()

            self.restore_labels()

            x_to_plot, y_to_plot = numpy.meshgrid(self.xx, self.yy)
            zz_to_plot = self.zz.reshape(len(self.yy), len(self.xx))

            if self.__type==Scan3DHistoWidget.PlotType.SURFACE:
                if has_colormap:
                    self.axis.plot_surface(x_to_plot, y_to_plot, zz_to_plot,
                                           rstride=1, cstride=1, cmap=colormap, linewidth=0.5, antialiased=True)
                else:
                    self.axis.plot_surface(x_to_plot, y_to_plot, zz_to_plot,
                                           rstride=1, cstride=1, color=self.__cc('black'), linewidth=0.5, antialiased=True)

            elif self.__type==Scan3DHistoWidget.PlotType.LINES:

                if has_colormap:
                    self.plot_lines_colormap(x_to_plot, y_to_plot, zz_to_plot, colormap, histo_index)
                else:
                    self.plot_lines_black(x_to_plot, zz_to_plot)

                xmin = numpy.min(self.xx)
                xmax = numpy.max(self.xx)
                ymin = numpy.min(self.yy)
                ymax = numpy.max(self.yy)
                zmin = numpy.min(self.zz)
                zmax = numpy.max(self.zz)

                self.axis.set_xlim(xmin,xmax)
                self.axis.set_ylim(ymin,ymax)
                self.axis.set_zlim(zmin,zmax)

            self.axis.mouse_init()

            try:
                self.plot_canvas.draw()
            except:
                pass

    def add_empty_curve(self, histo_data):
        pass


    def plot_lines_black(self, X, Z):
        verts = []
        for i in range(len(self.yy)):
            verts.append(list(zip(X[i], Z[i, :])))

        self.axis.add_collection3d(LineCollection(verts, colors=[self.__cc('black')]), zs=self.yy, zdir='y')

    def plot_lines_colormap(self, X, Y, Z, colormap, histo_index):

        import matplotlib.pyplot as plt

        # Set normalization to the same values for all plots
        norm = plt.Normalize(numpy.min(self.zz), numpy.max(self.zz))

        # Check sizes to loop always over the smallest dimension
        n,m = Z.shape

        if n>m:
            X=X.T; Y=Y.T; Z=Z.T
            m,n = n,m

        transparent_colormap = colormap(numpy.arange(colormap.N))
        transparent_colormap[:,-1] = 0.5*numpy.ones(colormap.N)
        transparent_colormap = ListedColormap(transparent_colormap)


        for j in range(n):
            # reshape the X,Z into pairs
            points = numpy.array([X[j,:], Z[j,:]]).T.reshape(-1, 1, 2)
            segments = numpy.concatenate([points[:-1], points[1:]], axis=1)
            lc = LineCollection(segments, cmap=transparent_colormap, norm=norm)

            # Set the values used for colormapping
            lc.set_array((Z[j,1:]+Z[j,:-1])/2)
            lc.set_linewidth(2) # set linewidth a little larger to see properly the colormap variation
            self.axis.add_collection3d(lc, zs=(Y[j,1:]+Y[j,:-1])/2,  zdir='y') # add line to axes

        if histo_index==0:
            self.colorbar = self.figure.colorbar(lc) # add colorbar, as the normalization is the same for all,

        self.colorbar.update_normal(lc)
        self.colorbar.draw_all()
        self.colorbar.update_bruteforce(lc)

class ScanHistoWidget(AbstractScanHistoWidget):

    def __init__(self, workspace_units_to_cm):
        super(ScanHistoWidget, self).__init__(workspace_units_to_cm)

        self.plot_canvas = oasysgui.plotWindow(parent=None,
                                               backend=None,
                                               resetzoom=True,
                                               autoScale=True,
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
                                               fit=True)

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
                   xrange=None,
                   show_reference=True,
                   add_labels=True,
                   has_colormap=True,
                   colormap=cm.rainbow):

        factor=ShadowPlot.get_factor(col, conv=self.workspace_units_to_cm)

        if histo_index==0 and xrange is None:
            ticket = beam._beam.histo1(col, xrange=None, nbins=nbins, nolost=1, ref=23)

            fwhm = ticket['fwhm']
            xrange = ticket['xrange']
            centroid = xrange[0] + (xrange[1] - xrange[0])*0.5

            if not fwhm is None:
                xrange = [centroid - 2*fwhm , centroid + 2*fwhm]

        ticket = beam._beam.histo1(col, xrange=xrange, nbins=nbins, nolost=1, ref=23)

        if not ytitle is None:  ytitle = ytitle + ' weighted by ' + ShadowPlot.get_shadow_label(23)

        histogram = ticket['histogram_path']
        bins = ticket['bin_path']*factor

        histogram_stats = ticket['histogram']
        bins_stats = ticket['bin_center']

        fwhm = ticket['fwhm']*factor
        sigma = get_sigma(histogram_stats, bins_stats)*factor

        peak_intensity = numpy.average(histogram_stats[numpy.where(histogram_stats>=numpy.max(histogram_stats)*0.85)])

        if histo_index==0 and show_reference:
            h_title = "Reference"
        else:
            h_title = scan_variable_name + ": " + str(scan_variable_value)

        color="#000000"

        import matplotlib
        matplotlib.rcParams['axes.formatter.useoffset']='False'

        if histo_index== 0:
            offset = int(peak_intensity*0.3)

        self.plot_canvas.addCurve(bins, histogram + offset*histo_index, h_title, symbol='', color=color, xlabel=xtitle, ylabel=ytitle, replace=False) #'+', '^', ','

        if add_labels: self.plot_canvas._backend.ax.text(xrange[0]*factor*1.05, offset*histo_index*1.05, h_title)

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

        return HistogramData(histogram_stats, bins_stats, offset, xrange, fwhm, sigma, peak_intensity)

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

    if False:
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

    if False:

        app = QApplication(sys.argv)

        window = Scan3DHistoWidget(workspace_units_to_cm=0.1, type=Scan3DHistoWidget.PlotType.LINES)
        window.setFixedWidth(700)
        window.setFixedHeight(700)

        xrange = numpy.arange(-5, 5, 0.1)

        y_values = numpy.arange(10, 30, 0.5)

        window.set_xrange(xrange)
        window.set_labels("Prova", "X", "Y", "Z")

        import time

        for y in y_values:
            z = numpy.random.normal(size=10000)
            histo, bins = numpy.histogram(z, xrange)
            histo = numpy.append(histo, 0)

            window.add_histo(y, histo)

            #time.sleep(1)

            window.show()
        app.exec()
