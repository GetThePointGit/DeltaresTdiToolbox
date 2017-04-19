import logging

try:
    from qgis.core import QgsMessageLog
except ImportError:
    print 'unable to load qgis'


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


def setup_logging(iface=None):

    log = logging.getLogger('')

    ql = QGisHandler(iface)
    ql.setLevel(logging.INFO)

    # fh = logging.FileHandler('plugin_log.log')
    # fh.setLevel(logging.WARNING)

    st = logging.StreamHandler()
    st.setLevel(logging.INFO)

    form = logging.Formatter('%(name)-12s - %(levelname)-8s - %(message)s')
    # fh.setFormatter(form)
    st.setFormatter(form)

    log.addHandler(ql)
    # log.addHandler(fh)
    log.addHandler(st)
