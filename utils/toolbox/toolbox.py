import os.path
import logging

from PyQt4.QtCore import Qt
from PyQt4 import QtGui

# Import the code for the DockWidget
from .toolbox_dockwidget import ToolboxDockwidget
from .toolbox_model import ToolboxModel

log = logging.getLogger(__name__)


class Toolbox:
    """QGIS Plugin Implementation."""

    def __init__(self, iface, toolbox_path):
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

        self.icon_path = 'todo'
        self.menu_text = u'todo'

        self.plugin_is_active = False
        self.dockwidget = None
        self.toolbox_path = None

        self.toolbox = None

    def on_unload(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""

        if self.dockwidget:
            self.dockwidget.close()

    def on_close_child_widget(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        self.dockwidget.treeView.doubleClicked.disconnect(self.run_script)
        self.dockwidget.closingWidget.disconnect(self.on_close_child_widget)

        self.dock_widget = None
        self.plugin_is_active = False

    def run(self):
        """Run method that loads and starts the plugin"""

        if not self.plugin_is_active:
            self.plugin_is_active = True

            if self.dockwidget is None:
                # Create the dockwidget (after translation) and keep reference
                self.dockwidget = ToolboxDockwidget()

            # connect to provide cleanup on closing of dockwidget
            self.dockwidget.closingWidget.connect(self.on_close_child_widget)

            # show the dockwidget
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
            self.add_tools()

    @staticmethod
    def is_leaf(q_model_index):
        """Check if QModelIndex is a leaf, i.e., has no children."""
        return (q_model_index.isValid() and
                not q_model_index.child(0, 0).isValid())

    @staticmethod
    def leaf_path(q_model_index):
        if not q_model_index.parent().isValid():
            return [q_model_index.data()]
        else:
            return Toolbox.leaf_path(q_model_index.parent()) + \
                   [q_model_index.data()]

    def run_script(self, qm_idx):
        """Dynamically import and run the selected script from the tree view.
        Args:
            qm_idx: the clicked QModelIndex
        """
        # We're only interested in leaves of the tree:

        if self.is_leaf(qm_idx):

            filename = qm_idx.data()
            item = self.toolboxmodel.item(qm_idx.row(), qm_idx.column())
            path = self.leaf_path(qm_idx)

            curr_dir = os.path.dirname(__file__)
            module_path = os.path.join(curr_dir, 'commands', *path)
            name, ext = os.path.splitext(path[-1])
            if ext != '.py':
                log.error("Not a Python script")
                return
            log.debug(module_path)
            log.debug(name)
            import imp
            mod = imp.load_source(name, module_path)
            log.debug(str(mod))

            self.command = mod.CustomCommand(
                iface=self.iface, ts_datasource=self.ts_datasource)
            self.command.run()

    def add_tools(self):
        self.toolbox_model = ToolboxModel()
        self.dockwidget.treeView.setModel(self.toolbox_model)
        self.dockwidget.treeView.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        self.dockwidget.treeView.doubleClicked.connect(self.run_script)

class Toolbox():

    @staticmethod
    def is_leaf(q_model_index):
        """Check if QModelIndex is a leaf, i.e., has no children."""
        return (q_model_index.isValid() and
                not q_model_index.child(0, 0).isValid())

    @staticmethod
    def leaf_path(q_model_index):
        if not q_model_index.parent().isValid():
            return [q_model_index.data()]
        else:
            return Toolbox.leaf_path(q_model_index.parent()) + \
                [q_model_index.data()]

    def run_script(self, qm_idx):
        """Dynamically import and run the selected script from the tree view.
        Args:
            qm_idx: the clicked QModelIndex
        """
        # We're only interested in leaves of the tree:

        if self.is_leaf(qm_idx):

            filename = qm_idx.data()
            item = self.toolboxmodel.item(qm_idx.row(), qm_idx.column())
            path = self.leaf_path(qm_idx)

            curr_dir = os.path.dirname(__file__)
            module_path = os.path.join(curr_dir, 'commands', *path)
            name, ext = os.path.splitext(path[-1])
            if ext != '.py':
                log.error("Not a Python script")
                return
            log.debug(module_path)
            log.debug(name)
            import imp
            mod = imp.load_source(name, module_path)
            log.debug(str(mod))

            self.command = mod.CustomCommand(
                iface=self.iface, ts_datasource=self.ts_datasource)
            self.command.run()

    def add_tools(self):
        self.toolbox_model = ToolboxModel()
        self.dockwidget.treeView.setModel(self.toolbox_model)
        self.dockwidget.treeView.setEditTriggers(
            QtGui.QAbstractItemView.NoEditTriggers)
        self.dockwidget.treeView.doubleClicked.connect(self.run_script)