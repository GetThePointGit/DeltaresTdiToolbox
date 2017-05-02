import os.path
import logging
import numpy as np

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

    def get_nodes(self, wb_polygon):

        log.info('polygon of wb area: %s', wb_polygon.exportToWkt())

        nodes = {
            '1d': [],
            '2d': []
        }

        lines, points, pumps = self.ts_datasource.rows[0].get_result_layers()

        # use bounding box and spatial index to prefilter lines
        request_filter = QgsFeatureRequest().setFilterRect(wb_polygon.geometry().boundingBox())
        for point in points.getFeatures(request_filter):
            # test if lines are crossing boundary of polygon
            if wb_polygon.contains(point.geometry()):
                if point['type'] == '1d':
                    nodes['1d'].append(point['id'])
                else:
                    nodes['2d'].append(point['id'])

        return nodes

    def get_aggregated_flows(self, link_ids, node_ids):

        ds = self.ts_datasource.rows[0].datasource()

        # create numpy table with flowlink information
        tnp_link = []  # id, 1d or 2d, in or out
        for l in link_ids['2d_in']:
            tnp_link.append((l, 2, 1))
        for l in link_ids['2d_out']:
            tnp_link.append((l, 2, -1))
        for l in link_ids['1d_in']:
            tnp_link.append((l, 1, 1))
        for l in link_ids['1d_out']:
            tnp_link.append((l, 1, -1))
        np_link = np.array(tnp_link, dtype=[('id', int), ('ntype', int), ('dir', int)])
        np_link.sort(axis=0)

        # create numpy table with node information
        tnp_node = []  # id, 1d or 2d, in or out
        for l in node_ids['2d']:
            tnp_node.append((l, 2))
        for l in node_ids['1d']:
            tnp_node.append((l, 1))

        np_node = np.array(tnp_node, dtype=[('id', int), ('ntype', int)])
        np_node.sort(axis=0)

        # # get range to read from netCDF for processing
        # minimum = min(min(link_ids['2d_in']),  min(link_ids['2d_out']))
        # maximum = max(max(link_ids['2d_in']),  max(link_ids['2d_out']))

        param = 'q'

        ts = ds.get_timestamps(parameter=param)
        dt = ts[1] - ts[0]

        total_time = np.zeros(shape=(np.size(ts, 0), 4))
        total_location = np.zeros(shape=(np.size(np_link, 0), 2))

        t_pref = 0
        vol_pref = 0

        for ts_idx, t in enumerate(ts):

            # inflow and outflow through 1d and 2d
            # todo: split 1d and 2d flows
            vol = ds.get_values_by_timestep_nr('q', ts_idx, np_link['id']) * np_link['dir']  # * dt

            pos = vol.clip(min=0)
            neg = vol.clip(max=0)

            total_time[ts_idx, 0] = pos.sum()
            total_time[ts_idx, 1] = neg.sum()

            total_location[:, 0] += pos
            total_location[:, 1] += neg

            # delta volume
            if ts_idx == 0:
                total_time[ts_idx, 2] = 0
                vol = ds.get_values_by_timestep_nr('vol', ts_idx, np_node['id'])
                vol_pref = vol.sum()
                t_pref = t
            else:

                vol = ds.get_values_by_timestep_nr('vol', ts_idx, np_node['id'])  # * dt
                tot_vol = vol.sum()

                total_time[ts_idx, 2] = -1 * (tot_vol - vol_pref) / (t - t_pref)

                vol_pref = tot_vol
                t_pref = t

        # calculate error
        total_time[:, 3] = -1 * total_time[:, 0:3].sum(axis=1)

        return ts, total_time, total_location


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
