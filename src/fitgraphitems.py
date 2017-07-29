from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QGraphicsLineItem
import pyqtgraph as pg



__all__ = ['PointItem', 'LineItem']



class PointItem(pg.GraphItem):
  def __init__(self, x, y, xyfilter=None):
    super().__init__()
    self.x = x
    self.y = y
    self.size = 8
    self.pen = pg.mkPen('#000', width=2)
    self.brush = pg.mkBrush('#fff')
    self.applyParams()
    self.drag = None
    self.xyfilter = xyfilter

    x.valueChanged.connect(self.applyParams)
    y.valueChanged.connect(self.applyParams)

  def move(self, x, y):
    if self.xyfilter:
      x, y = self.xyfilter(x, y)
    self.x.setValue(x)
    self.y.setValue(y)

  def setSize(self, size):
    self.size = size
    self.applyParams()

  def applyParams(self):
    self.setData(
      pos=[(self.x.value(), self.y.value())],
      symbol=['o'], size=[self.size],
      symbolPen=[self.pen], symbolBrush=[self.brush]
    )

  def hoverEvent(self, ev):
    if ev.enter:
      self.setSize(10)
    elif ev.exit:
      self.setSize(8)

  def mouseDragEvent(self, ev):
    if ev.button() != Qt.LeftButton:
      ev.ignore()
      return

    if ev.isStart():
      pos = ev.buttonDownPos()
      self.drag = pos, self.x.value(), self.y.value()

    elif ev.isFinish():
      self.drag = None

    else:
      if self.drag is None:
        ev.ignore()
        return

      spos, x, y = self.drag
      off = ev.pos() - spos
      x_, y_ = x + off.x(), y + off.y()
      self.move(x_, y_)

    ev.accept()


class LineItem(QGraphicsLineItem):
  def __init__(self, x1, y1, x2, y2):
    super().__init__()
    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2
    self.setPen(pg.mkPen('#000', width=2))
    self.applyParams()

    x1.valueChanged.connect(self.applyParams)
    y1.valueChanged.connect(self.applyParams)
    x2.valueChanged.connect(self.applyParams)
    y2.valueChanged.connect(self.applyParams)

  def applyParams(self):
    self.setLine(*[v.value() for v in (self.x1, self.y1, self.x2, self.y2)])
