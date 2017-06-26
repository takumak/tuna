from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtWidgets import QGraphicsLineItem
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


  def __add__(self, b):
    return FitParameterOp(operator.add, operator.sub, '+', self, b)

  def __radd__(self, b):
    return FitParameterOp(operator.add, operator.sub, '+', self, b)

  def __sub__(self, b):
    return FitParameterOp(operator.sub, lambda v,b: b-v, '-', self, b)

  def __rsub__(self, b):
    return FitParameterOp(lambda s,b: b-s, operator.add, '-', self, b)

  def __mul__(self, b):
    return FitParameterOp(operator.mul, operator.truediv, '*', self, b)

  def __rmul__(self, b):
    return FitParameterOp(operator.mul, operator.truediv, '*', self, b)

  def __truediv__(self, b):
    return FitParameterOp(operator.truediv, operator.mul, '/', self, b)

  def __neg__(self):
    return self*(-1)

  def __pow__(self, b):
    return FitParameterOp(operator.pow, lambda v,b: v**(1/b), '/', self, b)


class FitParameterConst(FitParameter):
  def setValue(self, value):
    pass


class FitParameterFunc(FitParameterConst):
  def __init__(self, name, f, fi, *args):
    self.f = f
    self.fi = fi
    self.args = args
    super().__init__(name, self.value())
    for a in self.args:
      a.changed.connect(lambda: self.changed.emit())

  def value(self):
    return self.f(*[a.value() for a in self.args])

  def setValue(self, value):
    self.args[0].setValue(self.fi(value, *[a.value() for a in self.args[1:]]))


class FitParameterOp(FitParameter):
  def __init__(self, op, opi, opname, a, b):
    if not isinstance(a, FitParameter):
      a = FitParameterConst(repr(a), a)
    if not isinstance(b, FitParameter):
      b = FitParameterConst(repr(b), b)

    super().__init__('(%s%s%s)' % (a.name, opname, b.name), 0)

    self.op  = op
    self.opi = opi
    self.a   = a
    self.b   = b

    a.changed.connect(lambda: self.changed.emit())
    b.changed.connect(lambda: self.changed.emit())

  def value(self):
    return self.op(self.a.value(), self.b.value())

  def setValue(self, value):
    self.a.setValue(self.opi(value, self.b.value()))


class Point(pg.GraphItem):
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


class Line(QGraphicsLineItem):
  def __init__(self, x1, y1, x2, y2):
    super().__init__()
    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2
    self.setPen(pg.mkPen('#000', width=2))
    self.applyParams()

    x1.changed.connect(self.applyParams)
    y1.changed.connect(self.applyParams)
    x2.changed.connect(self.applyParams)
    y2.changed.connect(self.applyParams)

  def applyParams(self):
    self.setLine(*[v.value() for v in (self.x1, self.y1, self.x2, self.y2)])


class FitHandleBase:
  def getGraphItems(self):
    raise NotImplementedError()


class FitHandlePosition(FitHandleBase):
  def __init__(self, x, y):
    self.x = x
    self.y = y

  def getGraphItems(self):
    return [Point(self.x, self.y)]


class FitHandleLine(FitHandleBase):
  def __init__(self, x1, y1, x2, y2):
    self.x1 = x1
    self.y1 = y1
    self.x2 = x2
    self.y2 = y2

  def getGraphItems(self):
    return [Line(self.x1, self.y1, self.x2, self.y2), Point(self.x2, self.y2)]


class FitHandleThetaLength(FitHandleBase):
  def __init__(self, cx, cy, theta, length):
    self.cx = cx
    self.cy = cy
    self.theta = theta
    self.length = length

    self.x = FitParameter('x', self.getX())
    self.y = FitParameter('y', self.getY())

    cx.changed.connect(self.updateXY)
    cy.changed.connect(self.updateXY)
    theta.changed.connect(self.updateXY)
    length.changed.connect(self.updateXY)

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
    return [Line(self.cx, self.cy, self.x, self.y), Point(self.x, self.y, self.xyfilter)]


class FitFunctionBase(QObject):
  parameterChanged = pyqtSignal(name='parameterChanged')

  def __init__(self):
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
    if self.plotCurveItem:
      x, y = self.plotCurveItem.getData()
      self.plotCurveItem.setData(x=x, y=self.y(x))
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
    super().__init__()

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParameter('a', self.getHeight(lines)*0.6))
    self.addParam(FitParameter('b', (x1 + x2)/2))
    self.addParam(FitParameter('c', (x2 - x1)*0.1))

    HWHM = self.c*np.sqrt(2*np.log(2))
    self.addHandle(FitHandlePosition(self.b, self.a))
    self.addHandle(FitHandleThetaLength(self.b, self.a/2, FitParameterConst('theta', 0), HWHM))
    self.addHandle(FitHandleThetaLength(self.b, self.a/2, FitParameterConst('theta', np.pi), HWHM))

  def y(self, x):
    return self.a.value()*np.exp(-(x-self.b.value())**2/(2*self.c.value()**2))


class FitFuncAsym2Sig(FitFunctionBase):
  name = 'Asym2Sig'
  desc = 'A*1/(1+exp(-(x-xc+w1/2)/w2))*(1-1/(1+exp(-(x-xc-w1/2)/w3)))'

  def __init__(self, lines):
    super().__init__()

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParameter('A',  self.getHeight(lines)*0.6))
    self.addParam(FitParameter('xc', (x1 + x2)/2))
    self.addParam(FitParameter('w1', self.getWidth(lines)*0.1))
    self.addParam(FitParameter('w2', self.getWidth(lines)*0.1))
    self.addParam(FitParameter('w3', self.getWidth(lines)*0.1))

    b =     (1+FitParameterFunc('b', np.exp, np.log, -( self.w1/(2*self.w2))))**(-1)
    c = 1 - (1+FitParameterFunc('c', np.exp, np.log, -(-self.w1/(2*self.w3))))**(-1)
    cy = self.A*b*c

    bl = FitParameterFunc('bl', np.exp, np.log, -self.w3**(-1)*self.w1)
    xl = -self.w1/2 + self.xc
    yl = (-(bl+1)**(-1)+1)*self.A/2

    self.addHandle(FitHandlePosition(self.xc, cy))
    self.addHandle(FitHandleThetaLength(self.xc, cy/2, FitParameterConst('theta', 0), self.w3))
    self.addHandle(FitHandleLine(self.xc, cy, xl, yl))

  def y(self, x):
    return (self.A.value()
            *    1/(1+np.exp(-(x-self.xc.value()+self.w1.value()/2)/self.w2.value()))
            * (1-1/(1+np.exp(-(x-self.xc.value()-self.w1.value()/2)/self.w3.value()))))
