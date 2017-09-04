import copy
import logging

import numpy as np
import pyqtgraph as pg
from PyQt4.QtCore import Qt, QSize, QEvent, QMetaObject
from PyQt4.QtCore import pyqtSignal
from PyQt4.QtGui import QTableView, QWidget, QVBoxLayout, QHBoxLayout, \
    QSizePolicy, QPushButton, QSpacerItem, QApplication, QDockWidget, QComboBox, QColor
from qgis.core import QgsGeometry, QgsCoordinateTransform
from zDeltaresTdiToolbox.config.waterbalance.sum_configs import serie_settings
from zDeltaresTdiToolbox.models.wb_item import WaterbalanceItemModel
from zDeltaresTdiToolbox.utils.maptools.polygon_draw import PolygonDrawTool

log = logging.getLogger('DeltaresTdi.' + __name__)

try:
    _encoding = QApplication.UnicodeUTF8


    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QApplication.translate(context, text, disambig)


serie_settings = {s['name']: s for s in serie_settings}


class WaterbalanceItemTable(QTableView):
    hoverExitRow = pyqtSignal(int)
    hoverExitAllRows = pyqtSignal()  # exit the whole widget
    hoverEnterRow = pyqtSignal(str)

    def __init__(self, parent=None):
        super(WaterbalanceItemTable, self).__init__(parent)
        self.setStyleSheet("QTreeView::item:hover{background-color:#FFFF00;}")
        self.setMouseTracking(True)
        self.model = None

        self._last_hovered_row = None
        self.viewport().installEventFilter(self)

    def on_close(self):
        """
        unloading widget and remove all required stuff
        :return:
        """
        self.setMouseTracking(False)
        self.viewport().removeEventFilter(self)

    def closeEvent(self, event):
        """
        overwrite of QDockWidget class to emit signal
        :param event: QEvent
        """
        self.on_close()
        event.accept()

    def eventFilter(self, widget, event):
        if widget is self.viewport():

            if event.type() == QEvent.MouseMove:
                row = self.indexAt(event.pos()).row()
                if row == 0 and self.model and row > self.model.rowCount():
                    row = None

            elif event.type() == QEvent.Leave:
                row = None
                self.hoverExitAllRows.emit()
            else:
                row = self._last_hovered_row

            if row != self._last_hovered_row:
                if self._last_hovered_row is not None:
                    try:
                        self.hover_exit(self._last_hovered_row)
                    except IndexError:
                        log("Hover row index %s out of range" %
                            self._last_hovered_row, level='WARNING')
                        # self.hoverExitRow.emit(self._last_hovered_row)
                # self.hoverEnterRow.emit(row)
                if row is not None:
                    try:
                        self.hover_enter(row)
                    except IndexError:
                        log("Hover row index %s out of range" % row,
                            level='WARNING')
                self._last_hovered_row = row
                pass
        return QTableView.eventFilter(self, widget, event)

    def hover_exit(self, row_nr):
        if row_nr >= 0:
            item = self.model.rows[row_nr]
            item.hover.value = False

    def hover_enter(self, row_nr):
        if row_nr >= 0:
            item = self.model.rows[row_nr]
            name = item.name.value
            self.hoverEnterRow.emit(name)
            item.hover.value = True

    def setModel(self, model):
        super(WaterbalanceItemTable, self).setModel(model)

        self.model = model

        self.resizeColumnsToContents()
        self.model.set_column_sizes_on_view(self)


class WaterBalancePlotWidget(pg.PlotWidget):
    def __init__(self, parent=None, name=""):

        super(WaterBalancePlotWidget, self).__init__(parent)
        self.name = name
        self.showGrid(True, True, 0.5)
        self.setLabel("bottom", "tijd", "s")
        self.setLabel("left", "Hoeveelheid", "m3/s")

        self.series = {}

    def setModel(self, model):
        self.model = model
        self.model.dataChanged.connect(self.data_changed)
        self.model.rowsInserted.connect(self.on_insert)
        self.model.rowsAboutToBeRemoved.connect(
            self.on_remove)

    def on_remove(self):
        self.draw_timeseries()

    def on_insert(self):
        self.draw_timeseries()

    def draw_timeseries(self):
        self.clear()

        ts = self.model.ts

        zeros = np.zeros(shape=(np.size(ts, 0),))
        zero_serie = pg.PlotDataItem(
            x=ts,
            y=zeros,
            connect='finite',
            pen=pg.mkPen(color=QColor(0, 0, 0, 255), width=1))
        self.addItem(zero_serie)

        for dir in ['in', 'out']:
            prev_serie = zeros
            prev_pldi = zero_serie
            for item in self.model.rows:
                if item.active.value:
                    cum_serie = prev_serie + item.ts_series.value[dir]
                    plot_item = pg.PlotDataItem(
                        x=ts,
                        y=cum_serie,
                        connect='finite',
                        pen=pg.mkPen(color=item.color.qvalue, width=2))

                    color = item.color.value + [128]
                    fill = pg.FillBetweenItem(prev_pldi,
                                              plot_item,
                                              pg.mkBrush(*color))

                    # keep reference
                    item._plots[dir] = plot_item
                    item._plots[dir + 'fill'] = fill
                    prev_serie = cum_serie
                    prev_pldi = plot_item

        for dir in ['in', 'out']:
            for item in reversed(self.model.rows):
                if item.active.value:
                    self.addItem(item._plots[dir])
                    self.addItem(item._plots[dir + 'fill'])

        self.autoRange()

    def data_changed(self, index):
        """
        change graphs based on changes in locations
        :param index: index of changed field
        """
        if self.model.columns[index.column()].name == 'active':
            self.draw_timeseries()

        elif self.model.columns[index.column()].name == 'hover':
            item = self.model.rows[index.row()]
            if item.hover.value:
                if item.active.value:
                    if 'in' in item._plots:
                        item._plots['in'].setPen(color=item.color.qvalue,
                                                 width=3)
                        item._plots['infill'].setBrush(
                            pg.mkBrush(item.color.value + [200]))
                    if 'out' in item._plots:
                        item._plots['out'].setPen(color=item.color.qvalue,
                                                  width=5)
                        item._plots['outfill'].setBrush(
                            pg.mkBrush(item.color.value + [200]))
            else:
                if item.active.value:
                    if 'in' in item._plots:
                        item._plots['in'].setPen(color=item.color.qvalue,
                                                 width=2)
                        item._plots['infill'].setBrush(
                            pg.mkBrush(item.color.value + [128]))
                    if 'out' in item._plots:
                        item._plots['out'].setPen(color=item.color.qvalue,
                                                  width=2)
                    item._plots['outfill'].setBrush(
                        pg.mkBrush(item.color.value + [128]))


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

        self.model = WaterbalanceItemModel()
        self.wb_item_table.setModel(self.model)
        self.wb_item_table.setModel(self.model)
        self.plot_widget.setModel(self.model)

        # link tool
        self.polygon_tool = PolygonDrawTool(self.iface.mapCanvas(),
                                            self.select_polygon_button,
                                            self.on_polygon_ready)

        # fill comboboxes with selections
        self.modelpart_combo_box.insertItems(
            0,
            ['1d 2d', '1d', '2d'])
        #  self.modelpart_combo_box.setCurrentIndex(0)
        self.source_nc_combo_box.insertItems(
            0,
            ['normal', 'aggregation'])
        self.sum_type_combo_box.insertItems(
            0,
            serie_settings.keys())

        # add listeners
        self.select_polygon_button.toggled.connect(self.toggle_polygon_button)
        self.reset_waterbalans_button.clicked.connect(self.reset_waterbalans)
        # self.polygon_tool.deactivated.connect(self.update_wb)

        self.modelpart_combo_box.currentIndexChanged.connect(self.update_wb)
        self.source_nc_combo_box.currentIndexChanged.connect(self.update_wb)
        self.sum_type_combo_box.currentIndexChanged.connect(self.update_wb)

        # initially turn on tool
        self.select_polygon_button.toggle()

    def on_polygon_ready(self, points):
        self.iface.mapCanvas().unsetMapTool(self.polygon_tool)

    def reset_waterbalans(self):
        self.polygon_tool.reset()

    def toggle_polygon_button(self):

        if self.select_polygon_button.isChecked():
            print 'isChecked'
            self.reset_waterbalans()

            self.iface.mapCanvas().setMapTool(self.polygon_tool)

            self.select_polygon_button.setText(_translate(
                "DockWidget", "Klaar", None))
        else:
            print 'isUnChecked'
            self.iface.mapCanvas().unsetMapTool(self.polygon_tool)
            self.update_wb()
            self.select_polygon_button.setText(_translate(
                "DockWidget", "Teken gebied", None))

    def redraw_wb(self):
        pass

    def update_wb(self):

        ts, graph_series = self.calc_wb(
            self.modelpart_combo_box.currentText(),
            self.source_nc_combo_box.currentText(),
            serie_settings[self.sum_type_combo_box.currentText()])

        self.model.removeRows(0, len(self.model.rows))

        self.model.ts = ts
        self.model.insertRows(graph_series['items'])

    def calc_wb(self, model_part, source_nc, settings):

        points = self.polygon_tool.map_visualisation.points
        wb_polygon = QgsGeometry.fromPolygon([points])

        self.iface.mapCanvas().mapRenderer().destinationCrs()
        lines, points, pumps = self.ts_datasource.rows[0].get_result_layers()
        tr = QgsCoordinateTransform(self.iface.mapCanvas().mapRenderer().destinationCrs(),
                                    lines.crs())
        wb_polygon.transform(tr)

        link_ids, pump_ids = self.calc.get_incoming_and_outcoming_link_ids(wb_polygon, model_part)
        node_ids = self.calc.get_nodes(wb_polygon, model_part)

        ts, total_time = self.calc.get_aggregated_flows(link_ids, pump_ids, node_ids, model_part, source_nc)

        graph_series = self.make_graph_series(ts, total_time, model_part, settings)

        return ts, graph_series

    def make_graph_series(self, ts, total_time, model_part, settings):

        settings = copy.deepcopy(settings)
        input_series = [
            ('2d_in', 0),
            ('2d_out', 1),
            ('1d_in', 2),
            ('1d_out', 3),
            ('2d_bound_in', 4),
            ('2d_bound_out', 5),
            ('1d_bound_in', 6),
            ('1d_bound_out', 7),
            ('1d_2d_in', 8),
            ('1d_2d_out', 9),
            ('2d_to_1d_pos', 10),
            ('2d_to_1d_neg', 11),
            ('pump_in', 12),
            ('pump_out', 13),
            ('rain', 14),
            ('infiltration_rate', 15),
            ('lat_2d', 16),
            ('lat_1d', 17),
            ('d_2d_vol', 18),
            ('d_1d_vol', 19),
            ('error_2d', 20),
            ('error_1d', 21),
            ('error_1d_2d', 22)
        ]

        if model_part == '1d 2d':
            input_series = dict([input_series[i] for i in
                                 (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 22)])
        elif model_part == '2d':
            input_series = dict([input_series[i] for i in (0, 1, 4, 5, 9, 10, 11, 14, 15, 16, 18, 20)])
            total_time[:, (10, 11)] = total_time[:, (10, 11)] * -1

        elif model_part == '1d':
            input_series = dict([input_series[i] for i in (2, 3, 6, 7, 8, 10, 11, 12, 13, 17, 19, 21)])
            total_time[:, (10, 11)] = total_time[:, (10, 11)] * -1

        for serie_setting in settings.get('items', []):
            serie_setting['active'] = True
            serie_setting['method'] = serie_setting['default_method']
            serie_setting['color'] = [int(c) for c in serie_setting['def_color'].split(',')]
            serie_setting['ts_series'] = {}
            nrs_input_series = []
            for serie in serie_setting['series']:
                if serie not in input_series:
                    # throw good error message
                    print('serie config error: {0} is an unknown serie or is doubled in the config.'.format(serie))
                else:
                    nrs_input_series.append(input_series[serie])
                    del input_series[serie]

            if serie_setting['default_method'] == 'net':
                sum = total_time[:, nrs_input_series].sum(axis=1)
                serie_setting['ts_series']['in'] = sum.clip(min=0)
                serie_setting['ts_series']['out'] = sum.clip(max=0)
            elif serie_setting['default_method'] == 'gross':
                sum_pos = np.zeros(shape=(np.size(ts, 0),))
                sum_neg = np.zeros(shape=(np.size(ts, 0),))
                for nr in nrs_input_series:
                    sum_pos += total_time[:, nr].clip(min=0)
                    sum_neg += total_time[:, nr].clip(max=0)
                serie_setting['ts_series']['in'] = sum_pos
                serie_setting['ts_series']['out'] = sum_neg
            else:
                # throw config error
                print('aggregation method unknown')

        if len(input_series) > 0:

            serie_setting = {
                'name': 'Overige',
                'default_method': settings['remnant_method'],
                'order': 100,
                'color': [int(c) for c in settings['remnant_def_color'].split(',')],
                'def_color': settings['remnant_def_color'],
                'series': [key for key in input_series],
                'ts_series': {}
            }
            for serie in input_series:
                nrs_input_series.append(input_series[serie])

            if serie_setting['default_method'] == 'net':
                sum = total_time[:, nrs_input_series].sum(axis=1)
                serie_setting['ts_series']['in'] = sum.clip(min=0)
                serie_setting['ts_series']['out'] = sum.clip(max=0)
            elif serie_setting['default_method'] == 'gross':
                sum_pos = np.zeros(shape=(np.size(ts, 0),))
                sum_neg = np.zeros(shape=(np.size(ts, 0),))
                for nr in nrs_input_series:
                    sum_pos += total_time[:, nr].clip(min=0)
                    sum_neg += total_time[:, nr].clip(max=0)
                serie_setting['ts_series']['in'] = sum_pos
                serie_setting['ts_series']['out'] = sum_neg
            else:
                # throw config error
                print('aggregation method unknown')

            settings['items'].append(serie_setting)

        if model_part == '1d':
            total_time[:, (10, 11)] = total_time[:, (10, 11)] * -1

        settings['items'] = sorted(settings['items'], key=lambda item: item['order'])

        return settings

    def unset_tool(self):
        pass

    def accept(self):
        pass

    def reject(self):
        self.close()

    def closeEvent(self, event):
        self.select_polygon_button.toggled.disconnect(self.toggle_polygon_button)
        self.reset_waterbalans_button.clicked.disconnect(self.reset_waterbalans)
        # self.polygon_tool.deactivated.disconnect(self.update_wb)
        self.iface.mapCanvas().unsetMapTool(self.polygon_tool)
        self.polygon_tool.close()

        self.modelpart_combo_box.currentIndexChanged.disconnect(self.update_wb)
        self.source_nc_combo_box.currentIndexChanged.disconnect(self.update_wb)
        self.sum_type_combo_box.currentIndexChanged.disconnect(self.update_wb)

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
        self.modelpart_combo_box = QComboBox(self)
        self.button_bar_hlayout.addWidget(self.modelpart_combo_box)
        self.source_nc_combo_box = QComboBox(self)
        self.button_bar_hlayout.addWidget(self.source_nc_combo_box)
        self.sum_type_combo_box = QComboBox(self)
        self.button_bar_hlayout.addWidget(self.sum_type_combo_box)

        spacer_item = QSpacerItem(40,
                                  20,
                                  QSizePolicy.Expanding,
                                  QSizePolicy.Minimum)
        self.button_bar_hlayout.addItem(spacer_item)
        self.main_vlayout.addLayout(self.button_bar_hlayout)

        # add tabWidget for graphWidgets
        self.contentLayout = QHBoxLayout(self)

        # Graph
        self.plot_widget = WaterBalancePlotWidget(self)
        sizePolicy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(1)
        sizePolicy.setVerticalStretch(1)
        sizePolicy.setHeightForWidth(
            self.plot_widget.sizePolicy().hasHeightForWidth())
        self.plot_widget.setSizePolicy(sizePolicy)
        self.plot_widget.setMinimumSize(QSize(250, 250))

        self.contentLayout.addWidget(self.plot_widget)

        # table
        self.wb_item_table = WaterbalanceItemTable(self)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(
            self.wb_item_table.sizePolicy().hasHeightForWidth())
        self.wb_item_table.setSizePolicy(sizePolicy)
        self.wb_item_table.setMinimumSize(QSize(250, 0))

        self.contentLayout.addWidget(self.wb_item_table)

        self.main_vlayout.addLayout(self.contentLayout)

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
