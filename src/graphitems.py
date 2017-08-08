from PyQt5.QtCore import Qt, pyqtSignal, QRectF, QByteArray, QDataStream
from PyQt5.QtGui import QPainter, QPainterPath, QColor
from PyQt5.QtOpenGL import QGLWidget
from PyQt5.QtWidgets import QGraphicsObject
import pyqtgraph as pg
import numpy as np
import struct
from OpenGL import GL



__all__ = ['GraphItemBase', 'PathItem', 'PlotCurveItem']



class GraphItemBase(QGraphicsObject):
  hoveringChanged = pyqtSignal()
  touchable = False
  label = None

  def __init__(self, view):
    super().__init__()
    self.view = view
    self.view.pixelRatioChanged.connect(self.pixelRatioChanged)
    self.pen = None
    self.brush = None
    self.hovering = False
    self.__boundingRect = None

  def setPenColor(self, color):
    if self.pen:
      self.pen.setColor(QColor(color))

  def pixelRatioChanged(self):
    pass

  def addParam(self, name, param):
    setattr(self, name, param)
    param.valueChanged.connect(self.paramChanged)

  def paramChanged(self):
    self.prepareGeometryChange()
    self.invalidateBoundingRect()
    self.update()

  def paint(self, painter, option, widget):
    if isinstance(widget, QGLWidget):
      painter.beginNativePainting()
      try:
        self.paintGL()
      finally:
        painter.endNativePainting()
    else:
      painter.setRenderHint(QPainter.Antialiasing)
      if self.pen: painter.setPen(self.pen)
      if self.brush: painter.setBrush(self.brush)
      self.paint_(painter)

  def paint_(self, painter):
    pass

  def paintGL(self):
    pass

  def dataBounds(self, ax, frac, orthoRange=None):
    return None

  def boundingRect(self):
    if self.__boundingRect is None:
      self.__boundingRect = self.boundingRect_()
    return self.__boundingRect

  def boundingRect_(self):
    return QRectF()

  def invalidateBoundingRect(self):
    self.__boundingRect = None

  def hoverEvent(self, ev):
    if ev.enter:
      self.hovering = True
    elif ev.exit:
      self.hovering = False
    self.hoveringChanged.emit()

  def GL_drawPath(self, x, y, mode=GL.GL_LINE_STRIP):
    points = np.empty((len(x), 2))
    points[:,0] = x
    points[:,1] = y

    GL.glEnableClientState(GL.GL_VERTEX_ARRAY)
    try:
      GL.glVertexPointerf(points)

      if mode in (GL.GL_LINES, GL.GL_LINE_STRIP, GL.GL_LINE_LOOP):
        GL.glEnable(GL.GL_LINE_SMOOTH)
        GL.glHint(GL.GL_LINE_SMOOTH_HINT, GL.GL_NICEST)
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        color = self.pen.color()
        GL.glLineWidth(self.pen.width())
      elif mode == GL.GL_TRIANGLE_FAN:
        color = self.brush.color()

      GL.glColor3f(color.red()/255, color.green()/255, color.blue()/255)

      GL.glDrawArrays(mode, 0, points.shape[0]);
    finally:
      GL.glDisableClientState(GL.GL_VERTEX_ARRAY);



class PathItem(GraphItemBase):
  maxLineWidth = 2

  def __init__(self, view, color):
    super().__init__(view)
    self.pen = pg.mkPen(color, width=2)

  def paint_(self, painter):
    painter.drawPath(self.path)

  def paintGL(self):
    self.GL_drawPath(self.x, self.y)

  def setXY(self, x, y):
    self.x = x
    self.y = y
    self.updatePath()

    self.prepareGeometryChange()
    self.invalidateBoundingRect()
    self.update()

  def updatePath(self):
    self.path = self.createPath(self.x, self.y)

  @classmethod
  def createPath(cls, x, y, fill=Qt.OddEvenFill):
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

    N = x.shape[0]
    if N == 0:
      return path

    data = np.empty(N+2, dtype=[('type', '<i4'), ('x', '<f8'), ('y', '<f8')])
    data[1]['type'] = 0
    data[2:N+1]['type'] = 1
    data[1:N+1]['x'] = x
    data[1:N+1]['y'] = y

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

  def dataBounds(self, ax, frac, orthoRange=None):
    if ax == 0:
      return min(self.x), max(self.x)
    else:
      return min(self.y), max(self.y)

  def boundingRect_(self):
    rx, ry = self.view.pixelRatio
    x1, x2 = min(self.x), max(self.x)
    y1, y2 = min(self.y), max(self.y)
    mx, my = self.maxLineWidth*rx, self.maxLineWidth*ry
    return QRectF(x1-mx/2, y1-my/2, x2-x1+mx, y2-y1+my)



class PlotCurveItem(PathItem):
  touchable = True
  maxLineWidth = 4

  def __init__(self, x, y, view, color, label=None):
    super().__init__(view, color)
    self.label = label
    self.shapePath = None
    self.setXY(x, y)
    self.setHighlighted(False)
    self.setAcceptHoverEvents(True)

  def pixelRatioChanged(self):
    super().pixelRatioChanged()
    self.shapePath = None

  def updatePath(self):
    super().updatePath()
    self.shapePath = None

  def createShapePath(self):
    rx, ry = self.view.pixelRatio
    w = 8

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
    return stroke

  def shape(self):
    if not self.shapePath:
      self.shapePath = self.createShapePath()
    return self.shapePath

  def setHighlighted(self, highlighted):
    self.update()
    self.pen.setWidth(4 if highlighted else 2)
