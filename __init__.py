import logging
# from DeltaresTdiToolbox.utils.qlogging import add_qgis_handler, setup_qgis_logging

log = logging.getLogger('DeltaresTdi')
log.setLevel(logging.DEBUG)

try:
    import pydevd
except ImportError:
    import sys
    sys.path.append('C:\\Program Files (x86)\\JetBrains\\PyCharm 2017.1\\debug-eggs\\pycharm-debug.egg')

# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load main tool class
    :param iface: QgsInterface. A QGIS interface instance.
    """
    from DeltaresTdiToolbox.qgistools_plugin import DeltaresTdiToolbox

    # add_qgis_handler(iface)

    return DeltaresTdiToolbox(iface)
