
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QColor, QCursor

from qgis.core import QGis
from qgis.gui import QgsRubberBand, QgsMapTool


class PolygonDrawMapVisualisation(object):

    def __init__(self, canvas):

        self.canvas = canvas
        self.points = []

        # temp layer for side profile trac
        self.rb = QgsRubberBand(self.canvas, QGis.Polygon)
        self.rb.setColor(Qt.red)
        self.rb.setFillColor(QColor(255, 0, 0, 128))
        self.rb.setLineStyle(Qt.DashLine)
        self.rb.setWidth(2)
        self.reset()

    def close(self):
        self.points = []
        self.reset()

    def show(self):
        self.rb.show()

    def hide(self):
        self.rb.hide()

    def add_point(self, point):
        self.points.append(point)
        self.rb.addPoint(point, True)
        self.rb.show()

    def reset(self):
        self.points = []
        self.rb.reset(QGis.Polygon)


class PolygonDrawTool(QgsMapTool):
    def __init__(self, canvas, button, callback_on_draw_finish):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.callback_on_draw_finish = callback_on_draw_finish

        self.isEmittingPoint = False

        self.map_visualisation = PolygonDrawMapVisualisation(self.canvas)
        self.setButton(button)

    def activate(self):
        super(PolygonDrawTool, self).activate()
        self.canvas.setCursor(QCursor(Qt.CrossCursor))

    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.map_visualisation.reset()

    def canvasDoubleClickEvent(self, e):
        self.callback_on_draw_finish(self.map_visualisation.points)

    def canvasPressEvent(self, e):
        point = self.toMapCoordinates(e.pos())
        self.isEmittingPoint = True

    def canvasReleaseEvent(self, e):
        point = self.toMapCoordinates(e.pos())
        self.map_visualisation.add_point(point)
        self.isEmittingPoint = False

    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return

    def deactivate(self):
        super(PolygonDrawTool, self).deactivate()
        self.canvas.setCursor(QCursor(Qt.ArrowCursor))

    def close(self):
        self.deactivate()
        self.map_visualisation.close()


    # def activate(self):
    #     self.canvas.setCursor(QCursor(Qt.CrossCursor))
    #
    # def deactivate(self):
    #     self.deactivated.emit()
    #     self.canvas.setCursor(QCursor(Qt.ArrowCursor))
    #
    # def isZoomTool(self):
    #     return False
    #
    # def isTransient(self):
    #     return False
    #
    # def isEditTool(self):
    #     return False