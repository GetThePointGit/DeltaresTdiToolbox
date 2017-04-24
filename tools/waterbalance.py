import os.path
import logging

from PyQt4.QtCore import Qt

# Import the code for the DockWidget
from DeltaresTdiToolbox.views.waterbalance_widget import WaterBalanceWidget
from qgis.core import QgsFeatureRequest, QgsPoint

log = logging.getLogger('DeltaresTdi.' + __name__)


class WaterBalanceCalculation(object):

    def __init__(self, ts_datasource):
        self.ts_datasource = ts_datasource

    def get_incoming_and_outcoming_link_ids(self, wb_polygon):

        log.info('polygon of wb area: %s', wb_polygon.exportToWkt())

        flow_lines = {
            '1d_in': [],
            '1d_out': [],
            '2d_in': [],
            '2d_out': [],
        }

        lines, points, pumps = self.ts_datasource.rows[0].get_result_layers()

        # use bounding box and spatial index to prefilter lines
        request_filter = QgsFeatureRequest().setFilterRect(wb_polygon.geometry().boundingBox())
        for line in lines.getFeatures(request_filter):
            # test if lines are crossing boundary of polygon
            if line.geometry().crosses(wb_polygon):
                geom = line.geometry().asPolyline()
                # check if flow is in or out by testing if startpoint is inside polygon --> out
                if wb_polygon.contains(QgsPoint(geom[0])):
                    if line['type'] in ['1d', 'v2_pipe']:
                        flow_lines['1d_out'].append(line['id'])
                    elif line['type'] == '2d':
                        flow_lines['2d_out'].append(line['id'])
                    else:
                        log.warning('line type not supported. type is %s.', line['type'])

                # check if flow is in or out by testing if endpoint is inside polygon --> in
                if wb_polygon.contains(QgsPoint(geom[-1])):
                    if line['type'] in ['1d', 'v2_pipe']:
                        flow_lines['1d_in'].append(line['id'])
                    elif line['type'] == '2d':
                        flow_lines['2d_in'].append(line['id'])
                    else:
                        log.warning('line type not supported. type is %s.', line['type'])

        # todo: if link is incoming and outgoing, remove from flow_lines

        return flow_lines

    def get_aggregated_flows(self, link_ids):

        ds = self.ts_datasource.rows[0].datasource()

        param = 'q'

        # # get range to read from netCDF for processing
        # minimum = min(min(link_ids['2d_in']),  min(link_ids['2d_out']))
        # maximum = max(max(link_ids['2d_in']),  max(link_ids['2d_out']))

        ids = sorted(link_ids['2d_in'] + link_ids['2d_out'])

        ts = ds.get_timestamps(parameter=param)
        dt = ts[1] - ts[0]

        for ts_idx, t in enumerate(ts):
            # todo: reduce read by reading only slice between minimum and maximum slice
            values = self.ds.get_values_by_timestamp(param, ts_idx, ids)



        timestep = ds.get_values_by_timestep_nr('q', 2)


class WaterBalanceTool:
    """QGIS Plugin Implementation."""

    def __init__(self, iface, ts_datasource):
        """Constructor.
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        self.ts_datasource = ts_datasource

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        self.icon_path = ':/plugins/DeltaresTdiToolbox/media/icon_toolbox.png'
        self.menu_text = u'Example Tool'

        self.plugin_is_active = False
        self.widget = None

        self.toolbox = None

    def on_unload(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        if self.widget is not None:
            self.widget.close()

    def on_close_child_widget(self):
        """Cleanup necessary items here when plugin widget is closed"""
        self.widget.closingWidget.disconnect(self.on_close_child_widget)
        self.widget = None
        self.plugin_is_active = False

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.plugin_is_active:
            self.plugin_is_active = True

            if self.widget is None:
                # Create the widget (after translation) and keep reference
                self.widget = WaterBalanceWidget(iface=self.iface,
                                                ts_datasource=self.ts_datasource,
                                                wb_calc=WaterBalanceCalculation(self.ts_datasource))

            # connect to provide cleanup on closing of widget
            self.widget.closingWidget.connect(self.on_close_child_widget)

            # show the #widget
            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self.widget)

            self.widget.show()
