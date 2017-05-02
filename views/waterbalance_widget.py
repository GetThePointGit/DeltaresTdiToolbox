import os
import logging

from PyQt4.QtCore import Qt, QSize, QEvent, pyqtSignal, QMetaObject, QVariant
from PyQt4.QtGui import QTableView, QWidget, QVBoxLayout, QHBoxLayout, \
    QSizePolicy, QPushButton, QSpacerItem, QApplication, QTabWidget, \
    QDockWidget, QComboBox, QMessageBox, QColor, QCursor

from PyQt4.QtCore import pyqtSignal

import numpy as np
import pyqtgraph as pg

from qgis.core import QgsGeometry, QgsPoint, QgsFeatureRequest, QgsCoordinateTransform

from DeltaresTdiToolbox.utils.maptools.polygon_draw import PolygonDrawTool


log = logging.getLogger('DeltaresTdi.' + __name__)

try:
    _encoding = QApplication.UnicodeUTF8

    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)



class WaterBalancePlotWidget(pg.PlotWidget):

    def __init__(self, parent=None, name=""):

        super(WaterBalancePlotWidget, self).__init__(parent)
        self.name = name
        self.showGrid(True, True, 0.5)
        self.setLabel("bottom", "tijd", "s")
        self.setLabel("left", "Hoeveelheid", "m3")

        pen = pg.mkPen(color=QColor(0, 0, 200), width=2)
        self.flow_in_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.addItem(self.flow_in_plot)

        pen = pg.mkPen(color=QColor(200, 200, 0), width=2)
        self.flow_out_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.addItem(self.flow_out_plot)

        pen = pg.mkPen(color=QColor(200, 0, 0), width=2)
        self.storage_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.addItem(self.storage_plot)

        pen = pg.mkPen(color=QColor(0, 200, 0), width=2)
        self.error_plot = pg.PlotDataItem(np.array([(0.0, np.nan)]), pen=pen)
        self.addItem(self.error_plot)

    def set_timeseries(self, ts, total_timeseries):


        self.flow_in_plot.setData(x=ts, y=total_timeseries[:, 0], connect='finite')
        self.flow_out_plot.setData(x=ts, y=total_timeseries[:, 1], connect='finite')
        self.storage_plot.setData(x=ts, y=total_timeseries[:, 2], connect='finite')
        self.error_plot.setData(x=ts, y=total_timeseries[:, 3], connect='finite')

        self.autoRange()



class WaterBalanceWidget(QDockWidget):
    closingWidget = pyqtSignal()

    def __init__(self, parent=None, iface=None, ts_datasource=None, wb_calc=None):
        """Constructor."""
        super(WaterBalanceWidget, self).__init__(parent)
        self.iface = iface
        self.ts_datasource = ts_datasource
        self.calc = wb_calc

        # setup ui
        self.setup_ui(self)

        # create tool sub classes
        widget = WaterBalancePlotWidget(self)

        self.plot_widget = widget
        self.side_view_tab_widget.addTab(widget, widget.name)

        # link tool
        self.tool = PolygonDrawTool(self.iface.mapCanvas(),
                                    self.select_polygon_button,
                                    self.on_polygon_ready)

        # add listeners
        self.select_polygon_button.toggled.connect(self.toggle_polygon_button)
        self.reset_waterbalans_button.clicked.connect(self.reset_waterbalans)
        self.tool.deactivated.connect(self.update_wb)

    def on_polygon_ready(self, points):
        self.iface.mapCanvas().unsetMapTool(self.tool)

    def reset_waterbalans(self):
        self.tool.reset()

    def toggle_polygon_button(self):

        if self.select_polygon_button.isChecked():
            print 'isChecked'
            self.reset_waterbalans()

            self.iface.mapCanvas().setMapTool(self.tool)

            self.select_polygon_button.setText(_translate(
                "DockWidget", "Klaar", None))
        else:
            print 'isUnChecked'
            self.iface.mapCanvas().unsetMapTool(self.tool)
            self.select_polygon_button.setText(_translate(
                "DockWidget", "Teken gebied", None))

    def update_wb(self):

        ts, total_time = self.calc_wb()
        self.plot_widget.set_timeseries(ts, total_time)



    def calc_wb(self):

        points = self.tool.map_visualisation.points
        wb_polygon = QgsGeometry.fromPolygon([points])

        self.iface.mapCanvas().mapRenderer().destinationCrs()
        lines, points, pumps = self.ts_datasource.rows[0].get_result_layers()
        tr = QgsCoordinateTransform(self.iface.mapCanvas().mapRenderer().destinationCrs(),
                                    lines.crs())
        wb_polygon.transform(tr)

        link_ids = self.calc.get_incoming_and_outcoming_link_ids(wb_polygon)
        print(str(link_ids))
        node_ids = self.calc.get_nodes(wb_polygon)
        print(str(node_ids))

        ts, total_time, total_location = self.calc.get_aggregated_flows(link_ids, node_ids)
        print(total_time[:, 0].sum())
        print(total_time[:, 1].sum())
        print(total_time[:, 2].sum())
        print(total_time[:, 3].sum())

        return ts, total_time

    def unset_tool(self):
        pass

    def accept(self):
        pass

    def reject(self):
        self.close()

    def closeEvent(self, event):
        self.select_polygon_button.toggled.disconnect(self.toggle_polygon_button)
        self.reset_waterbalans_button.clicked.disconnect(self.reset_waterbalans)
        self.tool.deactivated.disconnect(self.update_wb)
        self.tool.close()

        self.closingWidget.emit()
        event.accept()

    def setup_ui(self, dock_widget):
        """
        initiate main Qt building blocks of interface
        :param dock_widget: QDockWidget instance
        """

        dock_widget.setObjectName("dock_widget")
        dock_widget.setAttribute(Qt.WA_DeleteOnClose)

        self.dock_widget_content = QWidget(self)
        self.dock_widget_content.setObjectName("dockWidgetContent")

        self.main_vlayout = QVBoxLayout(self)
        self.dock_widget_content.setLayout(self.main_vlayout)

        # add button to add objects to graphs
        self.button_bar_hlayout = QHBoxLayout(self)
        self.select_polygon_button = QPushButton(self)
        self.select_polygon_button.setCheckable(True)
        self.select_polygon_button.setObjectName("SelectedSideview")
        self.button_bar_hlayout.addWidget(self.select_polygon_button)

        self.reset_waterbalans_button = QPushButton(self)
        self.reset_waterbalans_button.setObjectName("ResetSideview")
        self.button_bar_hlayout.addWidget(self.reset_waterbalans_button)

        spacer_item = QSpacerItem(40,
                                  20,
                                  QSizePolicy.Expanding,
                                  QSizePolicy.Minimum)
        self.button_bar_hlayout.addItem(spacer_item)
        self.main_vlayout.addItem(self.button_bar_hlayout)

        # add tabWidget for graphWidgets
        self.side_view_tab_widget = QTabWidget(self)
        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        size_policy.setHorizontalStretch(6)
        size_policy.setVerticalStretch(0)
        size_policy.setHeightForWidth(
            self.side_view_tab_widget.sizePolicy().hasHeightForWidth())
        self.side_view_tab_widget.setSizePolicy(size_policy)
        self.side_view_tab_widget.setObjectName("sideViewTabWidget")
        self.main_vlayout.addWidget(self.side_view_tab_widget)

        # add dockwidget
        dock_widget.setWidget(self.dock_widget_content)
        self.retranslate_ui(dock_widget)
        QMetaObject.connectSlotsByName(dock_widget)

    def retranslate_ui(self, dock_widget):
        pass
        dock_widget.setWindowTitle(_translate(
           "DockWidget", "3Di waterbalans", None))
        self.select_polygon_button.setText(_translate(
            "DockWidget", "Teken gebied", None))
        self.reset_waterbalans_button.setText(_translate(
            "DockWidget", "Reset waterbalans", None))