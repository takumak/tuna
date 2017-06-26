from PyQt5.QtCore import Qt, QObject, pyqtSignal
import pyqtgraph as pg
import numpy as np
import operator
import logging


class FitParameter(QObject):
  changed = pyqtSignal(name='changed')

  def __init__(self, *args):
    super().__init__()
    if len(args) == 1 and isinstance(args[0], FitParameter):
      self.parent = args[0]
      self.parent.changed.connect(lambda: self.changed.emit())
    else:
      self.parent = None
      self.name, self.value_ = args

  def value(self):
    if self.parent:
      return self.parent.value()

    return self.value_

  def setValue(self, value):
    if self.parent:
      self.parent.setValue(value)
      return

    if value != self.value_:
      self.value_ = value
      self.changed.emit()

  def const(self):
    return FitParameterConst(self)

  def isConst(self):
    return False


  def __add__(self, b):
    return FitParameterOp(operator.add, '+', self, b)

  def __sub__(self, b):
    return FitParameterOp(operator.sub, '-', self, b)

  def __mul__(self, b):
    return FitParameterOp(operator.mul, '*', self, b)

  def __truediv__(self, b):
    return FitParameterOp(operator.truediv, '/', self, b)


class FitParameterConst(FitParameter):
  def setValue(self, value):
    pass

  def isConst(self):
    return True


# class FitParameterFunc(FitParameter):
#   def __init__(self, func, func_i, *args):
#     super().__init__(*args)
#     self.func = func
#     self.func_i = func_i

#   def value(self):
#     return self.func(super().value())

#   def setValue(self, value):
#     super().setValue(self.func_i(value))


class FitParameterOp(FitParameter):
  def __init__(self, op, opname, a, b):
    if not isinstance(a, FitParameter):
      a = FitParameterConst(repr(a), a)
    if not isinstance(b, FitParameter):
      b = FitParameterConst(repr(b), b)

    super().__init__('(%s%s%s)' % (a.name, opname, b.name), 0)

    self.op = op
    self.a  = a
    self.b  = b

    a.changed.connect(lambda: self.changed.emit())
    b.changed.connect(lambda: self.changed.emit())

  def value(self):
    return self.op(self.a.value(), self.b.value())

  def isConst(self):
    return (self.a.isConst() or self.b.isConst()) and not (self.a.isConst() and self.b.isConst())


class PointHandle(pg.GraphItem):
  def __init__(self, x, y, xyfilter=None):
    super().__init__()
    self.x = x
    self.y = y
    self.size = 6
    self.pen = pg.mkPen('#000', width=2)
    self.brush = pg.mkBrush('#fff')
    self.applyParams()
    self.drag = None
    self.xyfilter = xyfilter

    x.changed.connect(self.applyParams)
    y.changed.connect(self.applyParams)

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
      if len(self.scatter.pointsAt(pos)) == 0:
        ev.ignore()
        return
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


class FitHandleBase:
  def getGraphItems(self):
    raise NotImplementedError()


class FitHandlePosition(FitHandleBase):
  def __init__(self, x, y):
    self.x = x
    self.y = y

  def getGraphItems(self):
    return [PointHandle(self.x, self.y)]


class FitHandleLength(FitHandleBase):
  def __init__(self, cx, cy, theta, length):
    self.cx = cx
    self.cy = cy
    self.theta = theta
    self.length = length

    self.x = FitParameter('x', self.getX())
    self.y = FitParameter('y', self.getY())

    cx.changed.connect(self.updateXY)
    cy.changed.connect(self.updateXY)

  def updateXY(self):
    self.x.setValue(self.getX())
    self.y.setValue(self.getY())

  def getX(self):
    return self.cx.value() + self.length.value()*np.cos(self.theta.value())

  def getY(self):
    return self.cy.value() + self.length.value()*np.sin(self.theta.value())

  def xyfilter(self, x, y):
    x_, y_ = x - self.cx.value(), y - self.cy.value()
    theta = np.arctan(y_/x_)
    length = np.sqrt(x_**2 + y_**2)
    self.theta.setValue(theta)
    self.length.setValue(length)
    return self.getX(), self.getY()

  def getGraphItems(self):
    return [PointHandle(self.x, self.y, self.xyfilter)]


class FitFunctionBase(QObject):
  parameterChanged = pyqtSignal(name='parameterChanged')

  def __init__(self, lines):
    super().__init__()

    self.params = []
    self.paramsNameMap = {}
    self.handles = []

    self.plotCurveItem = None

  def __getattr__(self, name):
    if name in self.paramsNameMap:
      return self.paramsNameMap[name]
    raise AttributeError()

  def y(self, x):
    raise NotImplementedError()

  def addParam(self, param):
    self.params.append(param)
    self.paramsNameMap[param.name] = param
    param.changed.connect(self.paramChanged)

  def paramChanged(self):
    self.parameterChanged.emit()

  def addHandle(self, handle):
    self.handles.append(handle)

  def getXrange(self, lines):
    if len(lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getXrange() for l in lines])
    return min(l1), max(l2)

  def getYrange(self, lines):
    if len(lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getYrange() for l in lines])
    return min(l1), max(l2)

  def getWidth(self, lines):
    if len(lines) == 0: return 1
    x1, x2 = self.getXrange(lines)
    return x2 - x1

  def getHeight(self, lines):
    if len(lines) == 0: return 1
    y1, y2 = self.getYrange(lines)
    return y2 - y1

  def getGraphItems(self, x, **opts):
    self.plotCurveItem = pg.PlotCurveItem(
      x=x, y=self.y(x),
      antialias=True,
      name=self.name,
      **opts
    )
    return [self.plotCurveItem] + sum([h.getGraphItems() for h in self.handles], [])


class FitFuncGaussian(FitFunctionBase):
  name = 'Gaussian'
  desc = 'a*exp[-(x-b)^2/2c^2]'

  def __init__(self, lines):
    super().__init__(lines)

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParameter('a', self.getHeight(lines)*0.6))
    self.addParam(FitParameter('b', (x1 + x2)/2))
    self.addParam(FitParameter('c', (x2 - x1)*0.1))

    theta = FitParameterConst('theta', 0)
    self.addHandle(FitHandlePosition(self.b, self.a))
    self.addHandle(FitHandleLength(self.b, self.a*np.exp(-1/2), theta, self.c))

  def y(self, x):
    return self.a.value()*np.exp(-(x-self.b.value())**2/(2*self.c.value()**2))

  def paramChanged(self):
    if self.plotCurveItem:
      x, y = self.plotCurveItem.getData()
      self.plotCurveItem.setData(x=x, y=self.y(x))
