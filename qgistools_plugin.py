import logging
import os.path

from PyQt4.QtCore import (QSettings, QTranslator, qVersion, QCoreApplication,
                          QObject)
from PyQt4.QtGui import QAction, QIcon
# Import the code of the tools
from zDeltaresTdiToolbox.tools.waterbalance import WaterBalanceTool

import resources  # NoQa

# Initialize Qt resources from file resources.py

log = logging.getLogger('DeltaresTdi.' + __name__)


class DeltaresTdiToolbox(QObject):
    """Main Plugin Class which register toolbar and menu and tools """

    def __init__(self, iface):
        """Constructor.
        iface(QgsInterface): An interface instance which provides the hook to
        manipulate the QGIS application at run time.
        """
        log.debug('DeltaresTdToolbox init')

        super(DeltaresTdiToolbox, self).__init__(iface)

        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.join(
            os.path.dirname(__file__),
            os.path.pardir)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'DeltaresTdiToolbox_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.
        We implement this ourselves since we do not inherit QObject.
        :param message: String for translation.
        :type message: str, QString
        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('DeltaresTdiToolbox', message)

    def add_action(
        self,
        tool_instance,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.
        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str
        :param text: Text that should be shown in menu items for this action.
        :type text: str
        :param callback: Function to be called when the action is triggered.
        :type callback: function
        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool
        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool
        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool
        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str
        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget
        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.
        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        setattr(tool_instance, 'action_icon', action)
        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        # try:
        #     # load optional settings for remote debugging for development purposes
        #     # add file remote_debugger_settings.py in main directory to use debugger
        #     import remote_debugger_settings
        # except ImportError:
        #     pass

        # get link to active threedi plugin
        log.debug('DeltaresTdiToolbox initGui')
        try:
            from ThreeDiToolbox.threedi_tools import active_tdi_plugin

        except:
            raise ImportError("For water balance tool the ThreeDiToolbox plugin must be installed, "
                              "version xxx or higher")

        # make reference to other 3di plugin for getting loaded results, etc.
        if len(active_tdi_plugin) < 1:
            log.debug('active_tdi_plugin is empty: %s', active_tdi_plugin)
            raise ValueError('ThreeDiToolbox plugin is not active, please activate first')
        else:
            tdi_plugin = active_tdi_plugin[0]

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'Deltares 3di toolbox')

        # Set toolbar and init a few toolbar widgets
        self.toolbar = self.iface.addToolBar(u'DeltaresTdiToolbox')
        self.toolbar.setObjectName(u'DeltaresTdiToolbox')

        # Init tools
        self.wb_tool = WaterBalanceTool(self.iface, tdi_plugin.ts_datasource)

        self.tools = []
        self.tools.append(self.wb_tool)

        self.group_layer_name = '3di lagen'
        self.group_layer = None

        try:
            import remote_debugger_settings
        except:
            log.info('no remote debugger activated')
            pass

        for tool in self.tools:
            self.add_action(
                tool,
                tool.icon_path,
                text=self.tr(tool.menu_text),
                callback=tool.run,
                parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""

        log.debug('DeltaresTdiToolbox unload')


        for action in self.actions:
            self.iface.removePluginMenu(
                self.menu,
                action)
            self.iface.removeToolBarIcon(action)

            for tool in self.tools:
                tool.on_unload()

        # remove the toolbar
        try:
            del self.toolbar
        except AttributeError:
            print("Error, toolbar already removed?")
