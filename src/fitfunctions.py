import logging
import uuid
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QObject, pyqtSignal

from fitparameters import *
from fithandles import *



__all__ = ['FitFuncGaussian', 'FitFuncTwoLines']



class FitFunctionBase(QObject):
  parameterChanged = pyqtSignal(name='parameterChanged')

  def __init__(self):
    super().__init__()
    self.id = str(uuid.uuid4())
    self.params = []
    self.paramsNameMap = {}
    self.handles = []

    self.plotCurveItem = None

  def editableParams(self):
    return [p for p in self.params if not p.hidden]

  def __getattr__(self, name):
    if name in self.paramsNameMap:
      return self.paramsNameMap[name]
    raise AttributeError()

  def y(self, x):
    raise NotImplementedError()

  def getParams(self):
    return dict([(p.name, p.value()) for p in self.params])

  def setParams(self, params):
    self.blockSignals(True)
    for p in self.params:
      if p.name in params:
        p.setValue(params[p.name])
    self.blockSignals(False)
    self.paramChanged()

  def addParam(self, param):
    self.params.append(param)
    self.paramsNameMap[param.name] = param
    param.valueChanged.connect(self.paramChanged)

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

  def getGraphItems(self, x, color, **opts):
    self.plotCurveItem = pg.PlotCurveItem(
      x=x, y=self.y(x),
      antialias=True,
      name=self.name,
      pen=pg.mkPen(color=color, width=2),
      **opts
    )
    return [self.plotCurveItem] + sum([h.getGraphItems(color) for h in self.handles], [])

  def eval(self, name, formula, setArg):
    return FitParamFormula(name, formula, setArg, self.params)

  def lambdify(self, params):
    paramNames = [p.name for p in params]

    from sympy.parsing.sympy_parser import parse_expr
    from sympy import Symbol, lambdify
    expr = parse_expr(self.expr)
    # expr = expr.subs([(Symbol(p.name), p.value()) for p in self.params if p not in args])
    # args = [Symbol('x')]+[Symbol(a.name) for a in args]
    fixed = [s.name for s in expr.free_symbols if s.name != 'x' and s.name not in paramNames]
    args = ['x'] + paramNames + fixed
    func = lambdify([Symbol(a) for a in args], expr, 'numpy')

    def wrap(x, *vals):
      return func(x, *(list(vals) + [self.paramsNameMap[n].value() for n in fixed]))

    return wrap

  def y(self, x):
    from sympy.parsing.sympy_parser import parse_expr
    from sympy import Symbol, lambdify
    expr = parse_expr(self.expr)
    args = [Symbol('x')]+[Symbol(p.name) for p in self.params]
    func = lambdify(args, expr, 'numpy')

    # from sympy.utilities.lambdify import lambdastr
    # logging.debug(lambdastr(args, expr))

    y = lambda x: func(x, *[p.value() for p in self.params])
    self.y = y
    return y(x)



class FitFuncGaussian(FitFunctionBase):
  name = 'gaussian'
  label = 'Gaussian'
  expr = 'a*exp(-(x-b)**2/(2*c**2))'

  def __init__(self, lines, view):
    super().__init__()

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParam('a', self.getHeight(lines)*0.6))
    self.addParam(FitParam('b', (x1 + x2)/2))
    self.addParam(FitParam('c', (x2 - x1)*0.1))

    half = self.eval('half', 'a/2', None)
    HWHM = self.eval('HWHM', 'b+c*sqrt(2*log(2))', self.c)
    self.addHandle(FitHandlePosition(view, self.b, self.a))
    self.addHandle(FitHandleLine(view, self.b, half, HWHM, half))



class FitFuncTwoLines(FitFunctionBase):
  name = 'twoline'
  label = 'TwoLines'
  expr = '(a1*x+b1)/(1+exp((x-x0)/dx)) + (a2*x+b2)*(1-1/(1+exp((x-x0)/dx)))'

  def __init__(self, lines, view):
    super().__init__()

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParam('a1', 0))
    self.addParam(FitParam('b1', 0))
    self.addParam(FitParam('a2', 0))
    self.addParam(FitParam('b2', self.getHeight(lines)*0.8))
    self.addParam(FitParam('x0', (x1+x2)/2))
    self.addParam(FitParam('dx', 1))


    y0 = '(a1*x0+b1)/2 + (a2*x0+b2)/2'
    y0 = self.eval('y0', y0, None)
    x1 = self.eval('x1', 'x0+2*dx', self.dx)
    self.addHandle(FitHandleLine(view, self.x0, y0, x1, y0))
    self.addHandle(FitHandlePosition(view, self.x0, y0))


    theta1 = self.eval('theta1', 'atan(a1)+pi', self.a1)
    theta1.setValue(-np.pi)
    theta1.min_ = np.pi/2
    theta1.max_ = np.pi*3/2
    self.addParam(FitParam('cx1', self.x0.value(), hidden=True))
    self.addParam(FitParam('cy1', self.b1.value(), hidden=True))
    def setb1():
      b1 = self.cy1.value() - np.tan(self.a1.value())*self.cx1.value()
      self.b1.blockSignals(True)
      self.b1.setValue(b1)
      self.b1.blockSignals(False)
    def setcy1():
      cy1 = self.a1.value()*self.cx1.value()+self.b1.value()
      self.cy1.blockSignals(True)
      self.cy1.setValue(cy1)
      self.cy1.blockSignals(False)
    self.a1.valueChanged.connect(setb1)
    self.b1.valueChanged.connect(setcy1)
    self.cx1.valueChanged.connect(setb1)
    self.cy1.valueChanged.connect(setb1)
    self.addHandle(FitHandleTheta(view, self.cx1, self.cy1, theta1, 50))
    self.addHandle(FitHandlePosition(view, self.cx1, self.cy1))


    theta2 = self.eval('theta2', 'atan(a2)', self.a2)
    theta2.setValue(0)
    theta2.min_ = -np.pi/2
    theta2.max_ = np.pi/2
    self.addParam(FitParam('cx2', self.x0.value(), hidden=True))
    self.addParam(FitParam('cy2', self.b1.value(), hidden=True))
    def setb2():
      b2 = self.cy2.value() - np.tan(self.a2.value())*self.cx2.value()
      self.b2.blockSignals(True)
      self.b2.setValue(b2)
      self.b2.blockSignals(False)
    def setcy2():
      cy2 = self.a2.value()*self.cx2.value()+self.b2.value()
      self.cy2.blockSignals(True)
      self.cy2.setValue(cy2)
      self.cy2.blockSignals(False)
    self.a2.valueChanged.connect(setb2)
    self.b2.valueChanged.connect(setcy2)
    self.cx2.valueChanged.connect(setb2)
    self.cy2.valueChanged.connect(setb2)
    self.addHandle(FitHandleTheta(view, self.cx2, self.cy2, theta2, 50))
    self.addHandle(FitHandlePosition(view, self.cx2, self.cy2))
