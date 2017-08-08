import logging
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainterPath, QColor
import pyqtgraph as pg
import numpy as np
from OpenGL import GL

from graphitems import *
from fitparameters import *



__all__ = ['DraggablePointItem', 'LineItem', 'CircleItem', 'PlotCurveItem']



class FitGraphItemBase(GraphItemBase):
  def addParam(self, name, param):
    setattr(self, name, param)
    param.valueChanged.connect(self.paramChanged)

  def paramChanged(self):
    self.prepareGeometryChange()
    self.invalidateBoundingRect()
    self.update()



class CircleItemBase(FitGraphItemBase):
  def __init__(self, cx, cy, radius, view):
    super().__init__(view)
    self.addParam('cx', cx)
    self.addParam('cy', cy)
    self.addParam('radius', radius)

  def paint_(self, painter):
    painter.drawEllipse(self.calcRect())

  def paintGL(self):
    rx, ry = self.view.pixelRatio
    cx, cy, r = self.cx.value(), self.cy.value(), self.radius.value()
    theta = np.linspace(0, np.pi*2, 40)
    x, y = cx + r*np.cos(theta)*rx, cy + r*np.sin(theta)*ry
    if self.brush:
      self.GL_drawPath(x, y, GL.GL_TRIANGLE_FAN)

    if self.pen:
      if self.pen.style() == Qt.DashLine:
        theta = np.linspace(0, np.pi*2, 40)
        x, y = cx + r*np.cos(theta)*rx, cy + r*np.sin(theta)*ry
        mode = GL.GL_LINES
      else:
        mode = GL.GL_LINE_STRIP
      self.GL_drawPath(x, y, mode)

  def calcRect(self, margin=0):
    rx, ry = self.view.pixelRatio
    cx, cy, r = self.cx.value(), self.cy.value(), self.radius.value()
    w, h = (r+margin)*rx, (r+margin)*ry
    return QRectF(cx-w, cy-h, w*2, h*2)

  def boundingRect_(self):
    return self.calcRect(4)

  def shape(self):
    path = QPainterPath()
    path.addEllipse(self.calcRect(4))
    return path



class DraggablePointItem(CircleItemBase):
  touchable = True

  def __init__(self, x, y, view, color, xyfilter=None):
    super().__init__(x, y, FitParam('radius', 4), view)
    self.xyfilter = xyfilter
    self.setFlag(self.ItemIsFocusable, True)
    self.drag = None

    self.pen = pg.mkPen(color, width=2)
    self.brush = pg.mkBrush('#fff')
    self.setZValue(1)
    self.setAcceptHoverEvents(True)

  def focusInEvent(self, ev):
    super().focusInEvent(ev)
    self.brush.setColor(self.pen.color())
    self.update()

  def focusOutEvent(self, ev):
    super().focusOutEvent(ev)
    self.brush.setColor(QColor(255, 255, 255))
    self.update()

  def keyPressEvent(self, ev):
    dx, dy = ({
      Qt.Key_Left:  (-1, 0),
      Qt.Key_Right: (+1, 0),
      Qt.Key_Up:    (0, +1),
      Qt.Key_Down:  (0, -1)
    }).get(ev.key(), (0, 0))

    if dx == 0 and dy == 0:
      return

    mod = int(ev.modifiers())
    if mod == 0:
      pass
    elif mod == Qt.ShiftModifier:
      dx *= 10
      dy *= 10
    elif mod == Qt.ControlModifier:
      dx *= .2
      dy *= .2
    else:
      return

    logging.debug('Move: %+d,%+d px' % (dx, dy))

    rx, ry = self.view.pixelRatio
    if dx: self.cx.setValue(self.cx.value() + dx*rx)
    if dy: self.cy.setValue(self.cy.value() + dy*ry)

  def move(self, x, y):
    if self.xyfilter:
      x, y = self.xyfilter(x, y)
    self.cx.setValue(x)
    self.cy.setValue(y)

  def hoverEvent(self, ev):
    if self.drag:
      return

    super().hoverEvent(ev)
    if ev.enter:
      self.radius.setValue(6)
    elif ev.exit:
      self.radius.setValue(4)

  def mouseDragEvent(self, ev):
    if ev.button() != Qt.LeftButton:
      ev.ignore()
      return

    if ev.isStart():
      pos = ev.buttonDownPos()
      self.drag = pos, self.cx.value(), self.cy.value()

    elif ev.isFinish():
      self.drag = None

    else:
      if self.drag is None:
        ev.ignore()
        return

      spos, x, y = self.drag
      off = ev.pos() - spos

      rx, ry = self.view.pixelRatio
      dpx, dpy = off.x()/rx, off.y()/ry

      if ev.modifiers() == Qt.ControlModifier:
        if abs(dpx) > abs(dpy):
          dpy = 0
        else:
          dpx = 0

      x_, y_ = x + dpx*rx, y + dpy*ry
      self.move(x_, y_)

    ev.accept()



class CircleItem(CircleItemBase):
  def __init__(self, cx, cy, r, view, color):
    CircleItemBase.__init__(self, cx, cy, r, view)
    self.pen = pg.mkPen(color, width=1, style=Qt.DashLine)



class LineItem(PathItem):
  def __init__(self, x1, y1, x2, y2, view, color):
    super().__init__(view, color)
    self.addParam('x1', x1)
    self.addParam('y1', y1)
    self.addParam('x2', x2)
    self.addParam('y2', y2)
    self.paramChanged()

  def paramChanged(self):
    super().paramChanged()
    self.setXY(*self.getArray())

  def getArray(self):
    return (np.array([self.x1.value(), self.x2.value()]),
            np.array([self.y1.value(), self.y2.value()]))

  def dataBounds(self, ax, frac, orthoRange=None):
    return None
