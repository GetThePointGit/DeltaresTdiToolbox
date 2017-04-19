import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__),
    'toolbox_dockwidget.ui'))


class ToolboxDockwidget(QtGui.QDockWidget, FORM_CLASS):
    closingWidget = pyqtSignal()

    def __init__(self, parent=None):
        """Constructor."""
        super(ToolboxDockwidget, self).__init__(parent)
        # Set up the user interface from Designer.
        self.setupUi(self)

    def closeEvent(self, event):
        self.closingWidget.emit()
        event.accept()