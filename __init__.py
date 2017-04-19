# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load main tool class
    :param iface: QgsInterface. A QGIS interface instance.
    """

    from .qgistools_plugin import DeltaresTdiToolbox
    from .utils.qlogging import setup_logging

    setup_logging(iface)

    return DeltaresTdiToolbox(iface)
