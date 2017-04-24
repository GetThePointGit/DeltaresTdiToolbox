import logging

try:
    from qgis.core import QgsMessageLog
except ImportError:
    print 'unable to load qgis for logging'
    logging.warning('unable to load qgis for logging')


class QGisHandler(logging.Handler):

    def __init__(self, iface, *args, **kwargs):
        super(QGisHandler, self).__init__(*args, **kwargs)
        self.iface = iface

        # add references, because this somehow does not work directly,
        # something with the scope of the emit function (does this exists
        # in Python?)
        self.qgsMessageLog_ref = QgsMessageLog
        self.logging_ref = logging

    def emit(self, record):

        msg = self.format(record)

        if record.levelno >= self.logging_ref.ERROR:
            level = self.qgsMessageLog_ref.CRITICAL
        elif record.levelno >= self.logging_ref.WARNING:
            level = self.qgsMessageLog_ref.WARNING
        else:
            level = self.qgsMessageLog_ref.INFO

        self.qgsMessageLog_ref.logMessage(msg, level=level)

        if (record.levelno >= self.logging_ref.CRITICAL and
                self.iface is not None):

            self.iface.messageBar().pushMessage(
                    record.funcName, msg, level, 0)

def setup_qgis_logging(level=logging.INFO):

    log = logging.getLogger('DeltaresTdi')

    st = logging.StreamHandler()
    st.setLevel(logging.DEBUG)

    form = logging.Formatter('%(name)-12s - %(levelname)-8s - %(message)s')
    st.setFormatter(form)

    log.addHandler(st)
    log.setLevel(level)

    log.debug('stream log handler and loglevel set')

def add_qgis_handler(iface):

    log = logging.getLogger('DeltaresTdi')

    if True in [True for h in log.handlers if type(h) == QGisHandler]:
        log.debug('handlers already set. Skip setup handlers')
        return

    ql = QGisHandler(iface)
    ql.setLevel(logging.DEBUG)
    log.addHandler(ql)
    log.debug('add qgis log handler')
