import logging

log = logging.getLogger('DeltaresTdi')
log.setLevel(logging.DEBUG)


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load main tool class
    :param iface: QgsInterface. A QGIS interface instance.
    """
    from zDeltaresTdiToolbox.qgistools_plugin import DeltaresTdiToolbox

    return DeltaresTdiToolbox(iface)
