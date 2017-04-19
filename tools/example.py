import os.path
import logging

from PyQt4.QtCore import Qt
from PyQt4 import QtGui

# Import the code for the DockWidget
from DeltaresTdiToolbox.views.example_widget import ExampleWidget


log = logging.getLogger(__name__)


class ExampleTool:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.
        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

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
                self.widget = ExampleWidget(iface=self.iface)

            # connect to provide cleanup on closing of widget
            self.widget.closingWidget.connect(self.on_close_child_widget)

            # show the #widget
            # self.iface.addWidget(self.widget)
            self.widget.show()
