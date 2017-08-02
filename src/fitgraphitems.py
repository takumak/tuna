import logging
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPainterPath
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem
import pyqtgraph as pg

from fitparameters import *



__all__ = ['PointItem', 'LineItem', 'CircleItem']



class CircleItemBase(QGraphicsEllipseItem):
  def __init__(self, cx, cy, radius, view):
    super().__init__()
    self.cx = cx
    self.cy = cy
    self.radius = radius
    self.view = view

    cx.valueChanged.connect(self.updateGeometry)
    cy.valueChanged.connect(self.updateGeometry)
    radius.valueChanged.connect(self.updateGeometry)
    self.view.pixelRatioChanged.connect(self.updateGeometry)
    self.updateGeometry()

  def paint(self, p, *args):
    p.setRenderHint(QPainter.Antialiasing)
    super().paint(p, *args)

  def calcRect(self, margin=0):
    rx, ry = self.view.pixelRatio
    cx, cy, r = self.cx.value(), self.cy.value(), self.radius.value()
    w, h = (r+margin)*rx, (r+margin)*ry
    return QRectF(cx-w, cy-h, w*2, h*2)

  def updateGeometry(self):
    self.setRect(self.calcRect())

  def dataBounds(self, ax, frac, orthoRange=None):
    if ax == 0:
      x = self.cx.value()
      return x, x
    else:
      y = self.cy.value()
      return y, y

  def boundingRect(self):
    return self.calcRect(4)

  def shape(self):
    path = QPainterPath()
    path.addEllipse(self.boundingRect())
    return path



class PointItem(CircleItemBase):
  def __init__(self, x, y, view, color, xyfilter=None):
    super().__init__(x, y, FitParam('radius', 4), view)
    self.setPen(pg.mkPen(color, width=2))
    self.setBrush(pg.mkBrush('#fff'))
    self.drag = None
    self.xyfilter = xyfilter
    self.setFlag(self.ItemIsFocusable, True)

  def focusInEvent(self, ev):
    super().focusInEvent(ev)
    self.setBrush(pg.mkBrush('#000'))
    pass

  def focusOutEvent(self, ev):
    super().focusOutEvent(ev)
    self.setBrush(pg.mkBrush('#fff'))

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



class LineItem(QGraphicsLineItem):
  def __init__(self, x1, y1, x2, y2, color):
    super().__init__()

    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2

    self.setPen(pg.mkPen(color, width=2))

    x1.valueChanged.connect(self.applyParams)
    y1.valueChanged.connect(self.applyParams)
    x2.valueChanged.connect(self.applyParams)
    y2.valueChanged.connect(self.applyParams)
    self.applyParams()

  def paint(self, p, *args):
    p.setRenderHint(QPainter.Antialiasing)
    super().paint(p, *args)

  def applyParams(self):
    self.setLine(*[v.value() for v in (self.x1, self.y1, self.x2, self.y2)])

  def dataBounds(self, ax, frac, orthoRange=None):
    if ax == 0:
      v = self.x1.value(), self.x2.value()
    else:
      v = self.y1.value(), self.y2.value()
    return [min(v), max(v)]



class CircleItem(CircleItemBase):
  def __init__(self, cx, cy, r, view, color):
    CircleItemBase.__init__(self, cx, cy, r, view)
    self.setPen(pg.mkPen(color, width=1, style=Qt.DashLine))
