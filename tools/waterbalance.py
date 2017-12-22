import logging
import os.path

import numpy as np
from PyQt4.QtCore import Qt
from qgis.core import QgsFeatureRequest, QgsPoint
# Import the code for the DockWidget
from zDeltaresTdiToolbox.views.waterbalance_widget import WaterBalanceWidget

log = logging.getLogger('DeltaresTdi.' + __name__)


class WaterBalanceCalculation(object):
    def __init__(self, ts_datasource):
        self.ts_datasource = ts_datasource

    def get_incoming_and_outcoming_link_ids(self, wb_polygon, model_part):
        # todo: implement model_part

        log.info('polygon of wb area: %s', wb_polygon.exportToWkt())

        flow_lines = {
            '1d_in': [],
            '1d_out': [],
            '1d_bound_in': [],
            '1d_bound_out': [],
            '2d_in': [],
            '2d_out': [],
            '2d_bound_in': [],
            '2d_bound_out': [],
            '1d_2d_in': [],
            '1d_2d_out': [],
            '1d_2d': [],  # direction is always from 2d to 1d
        }
        pump_selection = {
            'in': [],
            'out': []
        }

        lines, points, pumps = self.ts_datasource.rows[0].get_result_layers()

        # all links in and out
        # use bounding box and spatial index to prefilter lines
        request_filter = QgsFeatureRequest().setFilterRect(wb_polygon.geometry().boundingBox())
        for line in lines.getFeatures(request_filter):

            # test if lines are crossing boundary of polygon
            if line.geometry().crosses(wb_polygon):
                geom = line.geometry().asPolyline()
                # check if flow is in or out by testing if startpoint is inside polygon --> out
                outgoing = wb_polygon.contains(QgsPoint(geom[0]))
                # check if flow is in or out by testing if endpoint is inside polygon --> in
                incoming = wb_polygon.contains(QgsPoint(geom[-1]))

                if incoming and outgoing:
                    # skip
                    pass
                elif outgoing:
                    if line['type'] in ['1d', 'v2_pipe', 'v2_channel', 'v2_culvert', 'v2_orifice', 'v2_weir']:
                        flow_lines['1d_out'].append(line['id'])
                    elif line['type'] in ['2d']:
                        flow_lines['2d_out'].append(line['id'])
                    elif line['type'] in ['1d_2d']:
                        flow_lines['1d_2d_out'].append(line['id'])
                    else:
                        log.warning('line type not supported. type is %s.', line['type'])
                elif incoming:
                    if line['type'] in ['1d', 'v2_pipe', 'v2_channel', 'v2_culvert', 'v2_orifice', 'v2_weir']:
                        flow_lines['1d_in'].append(line['id'])
                    elif line['type'] == '2d':
                        flow_lines['2d_in'].append(line['id'])
                    elif line['type'] in ['1d_2d']:
                        flow_lines['1d_2d_in'].append(line['id'])
                    else:
                        log.warning('line type not supported. type is %s.', line['type'])

            elif line['type'] == '1d_2d' and line.geometry().within(wb_polygon):
                flow_lines['1d_2d'].append(line['id'])

        # find boundaries in polygon
        request_filter = QgsFeatureRequest().setFilterRect(
            wb_polygon.geometry().boundingBox()
        ).setFilterExpression(u'"type" = \'1d_bound\' or "type" = \'2d_bound\'')

        # all boundaries in polygon
        for bound in points.getFeatures(request_filter):
            if wb_polygon.contains(QgsPoint(bound.geometry().asPoint())):
                # find link connected to boundary
                request_filter_bound = QgsFeatureRequest().setFilterExpression \
                    (u'"start_node_idx" = \'{idx}\' or "end_node_idx" = \'{idx}\''.format(idx=bound['id']))
                bound_lines = lines.getFeatures(request_filter_bound)
                for bound_line in bound_lines:
                    if bound_line['start_node_idx'] == bound['id']:
                        if bound['type'] == '1d_bound':
                            flow_lines['1d_bound_in'].append(bound_line['id'])
                        else:  # 2d
                            flow_lines['2d_bound_in'].append(bound_line['id'])
                    else:  # out
                        if bound['type'] == '1d_bound':
                            flow_lines['1d_bound_out'].append(bound_line['id'])
                        else:  # 2d
                            flow_lines['2d_bound_out'].append(bound_line['id'])

        # pumps
        # use bounding box and spatial index to prefilter pumps
        request_filter = QgsFeatureRequest().setFilterRect(wb_polygon.geometry().boundingBox())

        for pump in pumps.getFeatures(request_filter):
            # test if lines are crossing boundary of polygon
            if pump.geometry().crosses(wb_polygon):
                geom = pump.geometry().asPolyline()
                # check if flow is in or out by testing if startpoint is inside polygon --> out
                outgoing = wb_polygon.contains(QgsPoint(geom[0]))
                # check if flow is in or out by testing if endpoint is inside polygon --> in
                incoming = wb_polygon.contains(QgsPoint(geom[-1]))

                if incoming and outgoing:
                    # skip
                    pass
                elif outgoing:
                    pump_selection['out'].append(pump['id'])
                elif incoming:
                    pump_selection['in'].append(pump['id'])

        log.info(str(flow_lines))

        return flow_lines, pump_selection

    def get_nodes(self, wb_polygon, model_part):

        log.info('polygon of wb area: %s', wb_polygon.exportToWkt())

        nodes = {
            '1d': [],
            '2d': []
        }

        lines, points, pumps = self.ts_datasource.rows[0].get_result_layers()

        # use bounding box and spatial index to prefilter lines
        request_filter = QgsFeatureRequest().setFilterRect(wb_polygon.geometry().boundingBox())
        if model_part == '1d':
            request_filter.setFilterExpression(u'"type" = \'1d\'')
        elif model_part == '2d':
            request_filter.setFilterExpression(u'"type" = \'2d\'')
        else:
            request_filter.setFilterExpression(u'"type" = \'1d\' or "type" = \'2d\'')
        # todo: check if boundary nodes could not have rain, infiltration, etc.

        for point in points.getFeatures(request_filter):
            # test if lines are crossing boundary of polygon
            if wb_polygon.contains(point.geometry()):
                nodes[point['type']].append(point['id'])

        return nodes

    def get_aggregated_flows(self, link_ids, pump_ids, node_ids, model_part, source_nc):

        ds = self.ts_datasource.rows[0].datasource()

        # create numpy table with flowlink information
        tlink = []  # id, 1d or 2d, in or out
        for idx in link_ids['2d_in']:
            tlink.append((idx, 20, 1))
        for idx in link_ids['2d_out']:
            tlink.append((idx, 20, -1))

        for idx in link_ids['2d_bound_in']:
            tlink.append((idx, 21, 1))
        for idx in link_ids['2d_bound_out']:
            tlink.append((idx, 21, -1))

        for idx in link_ids['1d_in']:
            tlink.append((idx, 10, 1))
        for idx in link_ids['1d_out']:
            tlink.append((idx, 10, -1))

        for idx in link_ids['1d_bound_in']:
            tlink.append((idx, 11, 1))
        for idx in link_ids['1d_bound_out']:
            tlink.append((idx, 11, -1))

        # todo: these settings are strange- this is not what you expect from the direction of the lines
        for idx in link_ids['1d_2d_in']:
            tlink.append((idx, 31, -1))
        for idx in link_ids['1d_2d_out']:
            tlink.append((idx, 31, 1))

        for idx in link_ids['1d_2d']:
            tlink.append((idx, 30, 1))

        np_link = np.array(tlink, dtype=[('id', int), ('ntype', int), ('dir', int)])
        # sort for faster reading of netcdf
        np_link.sort(axis=0)

        # create masks
        mask_2d = np_link['ntype'] != 20
        mask_1d = np_link['ntype'] != 10
        mask_2d_bound = np_link['ntype'] != 21
        mask_1d_bound = np_link['ntype'] != 11
        mask_1d_2d_in_out = np_link['ntype'] != 31
        mask_1d_2d = np_link['ntype'] != 30

        tpump = []
        for idx in pump_ids['in']:
            tpump.append((idx, 1))
        for idx in pump_ids['out']:
            tpump.append((idx, -1))
        np_pump = np.array(tpump, dtype=[('id', int), ('dir', int)])
        np_pump.sort(axis=0)

        # doe the same for node information
        tnode = []  # id, 1d or 2d, in or out
        for idx in node_ids['2d']:
            tnode.append((idx, 20))
        for idx in node_ids['1d']:
            tnode.append((idx, 10))

        np_node = np.array(tnode, dtype=[('id', int), ('ntype', int)])
        np_node.sort(axis=0)

        mask_2d_nodes = np_node['ntype'] != 20
        mask_1d_nodes = np_node['ntype'] != 10

        # get all flows through incoming and outgoing flows
        if source_nc == 'aggregation':
            ts = ds.get_agg_var_timestamps('q_cum')
        else:
            ts = ds.get_timestamps(parameter='q')

        total_time = np.zeros(shape=(np.size(ts, 0), 23))
        # total_location = np.zeros(shape=(np.size(np_link, 0), 2))

        # links
        pos_pref = 0
        neg_pref = 0

        if np_link.size > 0:
            for ts_idx, t in enumerate(ts):
                # (1) inflow and outflow through 1d and 2d
                # vol = ds.get_values_by_timestep_nr('q', ts_idx, np_link['id']) * np_link['dir']  # * dt

                if source_nc == 'aggregation':
                    flow_pos = ds.get_values_by_timestep_nr('q_cum_positive', ts_idx, np_link['id']) * np_link[
                        'dir']
                    flow_neg = ds.get_values_by_timestep_nr('q_cum_negative', ts_idx, np_link['id']) * np_link[
                        'dir'] * -1

                    in_sum = flow_pos - pos_pref
                    out_sum = flow_neg - neg_pref

                    pos_pref = flow_pos
                    neg_pref = flow_neg

                else:
                    flow = ds.get_values_by_timestep_nr('q', ts_idx, np_link['id']) * np_link['dir']
                    # todo: check unit
                    in_sum = flow.clip(min=0)
                    out_sum = flow.clip(max=0)

                total_time[ts_idx, 0] = np.ma.masked_array(in_sum, mask=mask_2d).sum()
                total_time[ts_idx, 1] = np.ma.masked_array(out_sum, mask=mask_2d).sum()
                total_time[ts_idx, 2] = np.ma.masked_array(in_sum, mask=mask_1d).sum()
                total_time[ts_idx, 3] = np.ma.masked_array(out_sum, mask=mask_1d).sum()
                total_time[ts_idx, 4] = np.ma.masked_array(in_sum, mask=mask_2d_bound).sum()
                total_time[ts_idx, 5] = np.ma.masked_array(out_sum, mask=mask_2d_bound).sum()
                total_time[ts_idx, 6] = np.ma.masked_array(in_sum, mask=mask_1d_bound).sum()
                total_time[ts_idx, 7] = np.ma.masked_array(out_sum, mask=mask_1d_bound).sum()
                total_time[ts_idx, 8] = np.ma.masked_array(in_sum, mask=mask_1d_2d_in_out).sum()
                total_time[ts_idx, 9] = np.ma.masked_array(out_sum, mask=mask_1d_2d_in_out).sum()
                total_time[ts_idx, 10] = np.ma.masked_array(in_sum, mask=mask_1d_2d).sum()
                total_time[ts_idx, 11] = np.ma.masked_array(out_sum, mask=mask_1d_2d).sum()

        if np_pump.size > 0:
            # pumps
            pump_pref = 0
            for ts_idx, t in enumerate(ts):
                # (2) inflow and outflow through pumps
                if source_nc == 'aggregation':
                    pump_flow = ds.get_values_by_timestep_nr('q_pump_cum', ts_idx, np_pump['id']) * np_pump['dir']

                    flow_dt = pump_flow - pump_pref
                    pump_pref = pump_flow

                    in_sum = flow_dt.clip(min=0)
                    out_sum = flow_dt.clip(max=0)
                else:
                    flow = ds.get_values_by_timestep_nr('q_pump', ts_idx, np_pump['id']) * np_pump['dir']
                    # todo: check unit
                    in_sum = flow.clip(min=0)
                    out_sum = flow.clip(max=0)

                total_time[ts_idx, 12] = in_sum.sum()
                total_time[ts_idx, 13] = out_sum.sum()

        np_2d_node = np.ma.masked_array(np_node['id'], mask=mask_2d_nodes).compressed()

        for parameter, node, pnr, factor in [
            ('rain', np_2d_node, 14, 1),
            ('infiltration_rate', np_2d_node, 15, -1),
            ('qlat', np_node, 16, 1)]:

            if node.size > 0:
                skip = False
                if source_nc == 'aggregation':
                    if parameter + '_cum' not in ds.get_available_variables():
                        skip = True
                        log.warning('%s_cum niet beschikbaar! overslaan', parameter)
                        # todo: fallback on not aggregated version
                else:
                    if parameter not in ds.get_available_variables():
                        skip = True
                        log.warning('%s_cum niet beschikbaar! overslaan', parameter)
                if not skip:
                    values_pref = 0
                    for ts_idx, t in enumerate(ts):
                        if source_nc == 'aggregation':
                            values = ds.get_values_by_timestep_nr(
                                parameter + '_cum',
                                ts_idx,
                                node).sum()  # * dt
                            values_dt = values - values_pref
                            values_pref = values
                        else:
                            values_dt = ds.get_values_by_timestep_nr(
                                parameter,
                                ts_idx,
                                node).sum()  # * dt

                        if parameter == 'qlat':
                            total_time[ts_idx, pnr] = np.ma.masked_array(values_dt, mask=mask_2d_nodes).sum()
                            total_time[ts_idx, pnr + 1] = np.ma.masked_array(values_dt, mask=mask_1d_nodes).sum()
                        else:
                            total_time[ts_idx, pnr] = values_dt * factor

        if source_nc == 'aggregation':
            t_pref = 0

            for ts_idx, t in enumerate(ts):
                if ts_idx == 0:
                    # just to make sure machine precision distortion is reduced for the first timestamp (everything
                    # should be 0
                    total_time[ts_idx] = total_time[ts_idx] / (ts[1] - t)
                else:
                    total_time[ts_idx] = total_time[ts_idx] / (t - t_pref)
                    t_pref = t

        if np_node.size > 0:
            # delta volume
            t_pref = 0
            vol_pref = 0
            for ts_idx, t in enumerate(ts):
                # delta volume
                if ts_idx == 0:

                    total_time[ts_idx, 18] = 0
                    total_time[ts_idx, 19] = 0
                    vol = ds.get_values_by_timestep_nr('vol', ts_idx, np_node['id'])

                    td_vol_pref = np.ma.masked_array(vol, mask=mask_2d_nodes).sum()
                    od_vol_pref = np.ma.masked_array(vol, mask=mask_1d_nodes).sum()

                    t_pref = t

                else:
                    vol_ts_idx = ts_idx
                    if source_nc == 'aggregation':
                        # get timestep of corresponding with the aggregation
                        ts_normal = ds.get_timestamps(parameter='q')
                        vol_ts_idx = np.nonzero(ts_normal == t)[0]
                    vol = ds.get_values_by_timestep_nr('vol', vol_ts_idx, np_node['id'])

                    td_vol = np.ma.masked_array(vol, mask=mask_2d_nodes).sum()
                    od_vol = np.ma.masked_array(vol, mask=mask_1d_nodes).sum()

                    # todo: remove in case unit is m3 instead of m3/s
                    total_time[ts_idx, 18] = -1 * (td_vol - td_vol_pref) / (t - t_pref)
                    total_time[ts_idx, 19] = -1 * (od_vol - od_vol_pref) / (t - t_pref)

                    td_vol_pref = td_vol
                    od_vol_pref = od_vol
                    t_pref = t

        total_time = np.nan_to_num(total_time)

        # calculate error 2d
        total_time[:, 20] = -1 * total_time[:,
                                 (0, 1, 4, 5, 9, 10, 11, 14, 15, 16, 18)].sum(axis=1)
        # calculate error 1d
        total_time[:, 21] = -1 * total_time[:, (2, 3, 6, 7, 8, 12, 13, 17, 19)].sum(axis=1) + \
                            total_time[:, (10, 11)].sum(axis=1)

        # calculate error 1d-2d
        total_time[:, 22] = -1 * total_time[:,
                                 (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19)].sum(axis=1)

        return ts, total_time


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

        self.icon_path = ':/plugins/zDeltaresTdiToolbox/media/weight-scale-deltares.png'
        self.menu_text = u'Water Balance Tool'

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
