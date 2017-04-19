import os

from PyQt4 import QtGui, uic
from PyQt4.QtCore import pyqtSignal

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__),
    'ui/layer_selection_with_selected_feature_option.ui'))


class ExampleWidget(QtGui.QDialog, FORM_CLASS):
    closingWidget = pyqtSignal()

    def __init__(self, parent=None, iface=None):
        """Constructor."""
        super(ExampleWidget, self).__init__(parent)
        # Set up the user interface from Designer.
        self.setupUi(self)

        # set events
        # self.button_box.clicked.connect(
        #         self.on_button_click)

        self.iface = iface

        # set combobox list
        layers = [layer.name for layer in self.iface.legendInterface().layers()]

        self.layer_combo_box.addItems(layers)

        # self.layer_combo_box.currentIndexChanged.connect(
        #     self.todo)

    def accept(self):
        pass

    def reject(self):
        self.close()

    def closeEvent(self, event):
        self.closingWidget.emit()
        event.accept()