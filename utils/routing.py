import logging

logger = logging.getLogger('DeltaresTdi.' + __name__)

try:
    # First import view to set correct API versions of QString, etc.
    import qgis  # pylint: disable=W0611  # NOQA

    from PyQt4 import QtCore
    from PyQt4 import QtGui
    from qgis.gui import *
    from qgis.core import *

except ImportError, e:
    logger.warning('Not able to import QGIS and/ or PyQt files. Message: {0)'.format(e))
