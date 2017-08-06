import logging
from PyQt5.QtCore import pyqtSignal, QObject, Qt, QRectF, QByteArray, QDataStream
from PyQt5.QtGui import QPainter, QPainterPath, QPainterPathStroker
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsObject
import pyqtgraph as pg
import numpy as np
import struct

from fitparameters import *



__all__ = ['PointItem', 'LineItem', 'CircleItem', 'PathItem']



class GraphItemBase(QGraphicsObject):
  hoveringChanged = pyqtSignal()
  touchable = False

  def __init__(self, view):
    super().__init__()
    self.view = view
    self.view.pixelRatioChanged.connect(self.pixelRatioChanged)
    self.pen = None
    self.brush = None
    self.hovering = False
    self.setAcceptHoverEvents(True)

  def pixelRatioChanged(self):
    pass

  def addParam(self, name, param):
    setattr(self, name, param)
    param.valueChanged.connect(self.paramChanged)

  def paramChanged(self):
    pass

  def paint(self, p, *args):
    p.setRenderHint(QPainter.Antialiasing)
    if self.pen: p.setPen(self.pen)
    if self.brush: p.setBrush(self.brush)

  def dataBounds(self, ax, frac, orthoRange=None):
    return None

  def hoverEvent(self, ev):
    if ev.enter:
      self.hovering = True
    elif ev.exit:
      self.hovering = False
    self.hoveringChanged.emit()



class CircleItemBase(GraphItemBase):
  def __init__(self, cx, cy, radius, view):
    super().__init__(view)
    self.addParam('cx', cx)
    self.addParam('cy', cy)
    self.addParam('radius', radius)

  def pixelRatioChanged(self):
    super().pixelRatioChanged()
    self.update()

  def paramChanged(self):
    super().paramChanged()
    self.update()

  def paint(self, p, *args):
    super().paint(p, *args)
    cx, cy, r = self.cx.value(), self.cy.value(), self.radius.value()
    p.drawEllipse(self.calcRect())

  def calcRect(self, margin=0):
    rx, ry = self.view.pixelRatio
    cx, cy, r = self.cx.value(), self.cy.value(), self.radius.value()
    w, h = (r+margin)*rx, (r+margin)*ry
    return QRectF(cx-w, cy-h, w*2, h*2)

  def boundingRect(self):
    return self.calcRect(4)

  def shape(self):
    path = QPainterPath()
    path.addEllipse(self.boundingRect())
    return path



class PointItem(CircleItemBase):
  touchable = True

  def __init__(self, x, y, view, color, xyfilter=None):
    super().__init__(x, y, FitParam('radius', 4), view)
    self.xyfilter = xyfilter
    self.setFlag(self.ItemIsFocusable, True)
    self.drag = None

    self.pen = pg.mkPen(color, width=2)
    self.brush = pg.mkBrush('#fff')
    self.setZValue(1)

  def focusInEvent(self, ev):
    super().focusInEvent(ev)
    self.brush = pg.mkBrush('#000')
    self.update()

  def focusOutEvent(self, ev):
    super().focusOutEvent(ev)
    self.brush = pg.mkBrush('#fff')
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



class PathItem(GraphItemBase):
  def __init__(self, view, color):
    super().__init__(view)
    self.hoverWidth = 8
    self.pen = pg.mkPen(color, width=2)

  def pixelRatioChanged(self):
    super().pixelRatioChanged()
    self.createStroke()

  def paint(self, p, *args):
    super().paint(p, *args)
    p.drawPath(self.path)

  def createPath(self, x_, y_, fill=Qt.OddEvenFill):
    # https://code.woboq.org/qt5/qtbase/src/gui/painting/qpainterpath.cpp.html#_ZrsR11QDataStreamR12QPainterPath
    # http://doc.qt.io/qt-5/qpainterpath.html#ElementType-enum
    # http://doc.qt.io/qt-5/qt.html#FillRule-enum

    # QDataStream &QPainterPath::operator>>(QDataStream &s, QPainterPath &p)
    #      offset  size    type  description
    #           0     4   int32  element count (N)
    #           4     4   int32  element type (0 -- 3)
    #           8     8  double  x
    #          16     8  double  y
    #         ...
    #     20*i+ 4     4   int32  element type (0 -- 3)
    #     20*i+ 8     8  double  x
    #     20*i+16     8  double  y
    #         ...
    # 20*(N-1)+ 4     4   int32  element type (0 -- 3)
    # 20*(N-1)+ 8     8  double  x
    # 20*(N-1)+16     8  double  y
    # 20*(N-1)+20     4   int32  next starting i (N-1)
    # 20*(N-1)+24     4   int32  fill rule

    path = QPainterPath()

    N = x_.shape[0]
    if N == 0:
      return path

    data = np.empty(N+2, dtype=[('type', '<i4'), ('x', '<f8'), ('y', '<f8')])
    data[1]['type'] = 0
    data[2:N+1]['type'] = 1
    data[1:N+1]['x'] = x_
    data[1:N+1]['y'] = y_

    fpos = 20*(N+1)

    view = data.view(dtype=np.ubyte)
    view[:16] = 0
    view.data[16:20] = struct.pack('<i', N)
    view.data[fpos:fpos+8] = struct.pack('<ii', N-1, int(fill))

    buf = QByteArray.fromRawData(view.data[16:fpos+8])
    ds = QDataStream(buf)
    ds.setByteOrder(ds.LittleEndian)

    ds >> path
    return path

  def setXY(self, x, y):
    self.x = x
    self.y = y
    self.path = self.createPath(x, y)
    self.createStroke()

  def createStroke(self):
    rx, ry = self.view.pixelRatio
    w = self.hoverWidth

    dx = self.x[1:] - self.x[:-1]
    dy = self.y[1:] - self.y[:-1]
    theta1 = np.arctan2(dx/rx, -dy/ry)
    theta2 = theta1 + np.pi

    dxf = np.cos(theta1)*w/2*rx
    dyf = np.sin(theta1)*w/2*ry
    dxr = np.cos(theta2)*w/2*rx
    dyr = np.sin(theta2)*w/2*ry

    xf = np.array([self.x[:-1]+dxf, self.x[1:]+dxf]).flatten('F')
    yf = np.array([self.y[:-1]+dyf, self.y[1:]+dyf]).flatten('F')
    xr = np.array([self.x[:-1]+dxr, self.x[1:]+dxr]).flatten('F')
    yr = np.array([self.y[:-1]+dyr, self.y[1:]+dyr]).flatten('F')

    stroke = self.createPath(
      np.append(xf, xr[::-1]),
      np.append(yf, yr[::-1]),
      Qt.WindingFill
    )
    stroke.closeSubpath()
    self.stroke = stroke

  def dataBounds(self, ax, frac, orthoRange=None):
    if ax == 0:
      return min(self.x), max(self.x)
    else:
      return min(self.y), max(self.y)

  def boundingRect(self):
    rx, ry = self.view.pixelRatio
    x1, x2 = min(self.x), max(self.x)
    y1, y2 = min(self.y), max(self.y)
    mx = self.hoverWidth*rx
    my = self.hoverWidth*ry
    return QRectF(x1-mx/2, y1-my/2, x2-x1+mx, y2-y1+my)

  def shape(self):
    return self.stroke

  def setHighlighted(self, highlighted):
    self.pen.setWidth(4 if highlighted else 2)
    self.update()



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

  def hoverEvent(self, ev):
    pass

  def dataBounds(self, ax, frac, orthoRange=None):
    return None
