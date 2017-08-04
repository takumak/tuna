import logging
import uuid
import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import QObject, pyqtSignal

from functions import blockable
from fitparameters import *
from fithandles import *
from fitgraphitems import *



__all__ = [
  'FitFuncGaussian', 'FitFuncBoltzmann2',
  'FitFuncConstant', 'FitFuncHeaviside',
  'FitFuncRectangularWindow'
]



class FitFunctionBase(QObject):
  parameterChanged = pyqtSignal(QObject, name='parameterChanged')
  highlight = pyqtSignal(QObject, bool)

  def __init__(self, view):
    super().__init__()
    self.view = view
    self.id = str(uuid.uuid4())
    self.params = []
    self.paramsNameMap = {}
    self.handles = []

    self.pathItem = None

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
    self.paramChanged.block()
    for p in self.params:
      if p.name in params:
        p.setValue(params[p.name])
    self.paramChanged.unblock()
    self.paramChanged()

  def addParam(self, param):
    self.params.append(param)
    self.paramsNameMap[param.name] = param
    param.valueChanged.connect(self.paramChanged)

  @blockable
  def paramChanged(self):
    if self.pathItem:
      x = self.pathItem.x
      self.pathItem.setXY(x, y=self.y(x))
    self.parameterChanged.emit(self)

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

  def getGraphItems(self, x, color):
    self.pathItem = PathItem(x, self.y(x), color, self.view)
    self.pathItem.highlight.connect(lambda t: self.highlight.emit(self, t))
    return [self.pathItem] + sum([h.getGraphItems(color) for h in self.handles], [])

  def eval(self, name, formula, setArg):
    return FitParamFormula(name, formula, setArg, self.params)

  def parse_expr(self, expr):
    from sympy.parsing.sympy_parser import parse_expr
    from sympy import Symbol
    expr = parse_expr(expr)
    if 'x' not in [s.name for s in expr.free_symbols]:
      expr = expr+Symbol('x')*0
    return expr

  def lambdify(self, params):
    paramNames = [p.name for p in params]

    from sympy import Symbol, lambdify
    expr = self.parse_expr(self.expr)
    fixed = [s.name for s in expr.free_symbols if s.name != 'x' and s.name not in paramNames]
    args = ['x'] + paramNames + fixed
    func = lambdify([Symbol(a) for a in args], expr, 'numpy')

    return lambda x, *vals: func(x, *(list(vals) + [self.paramsNameMap[n].value() for n in fixed]))

  def y(self, x):
    from sympy import Symbol, lambdify
    expr = self.parse_expr(self.expr)
    args = [Symbol('x')]+[Symbol(p.name) for p in self.params]
    func = lambdify(args, expr, 'numpy')

    y = lambda x: func(x, *[p.value() for p in self.params])
    self.y = y
    return y(x)

  def setHighlighted(self, highlighted):
    if self.pathItem:
      self.pathItem.setHighlighted(highlighted)



class FitFuncGaussian(FitFunctionBase):
  name = 'gaussian'
  label = 'Gaussian'
  expr = 'a*exp(-(x-b)**2/(2*c**2))'

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', y2*0.6))
    self.addParam(FitParam('b', (x1 + x2)/2))
    self.addParam(FitParam('c', (x2 - x1)*0.1))
    self.addParam(self.eval('I', 'sqrt(2*pi)*a*c', None))

    half = self.eval('half', 'a/2', None)
    HWHM = self.eval('HWHM', 'b+c*sqrt(2*log(2))', self.c)
    self.addHandle(FitHandlePosition(view, self.b, self.a))
    self.addHandle(FitHandleLine(view, self.b, half, HWHM, half))



class FitFuncBoltzmann2(FitFunctionBase):
  name = 'boltzmann2'
  label = 'Boltzmann 2'
  expr = '(a1*x+b1)/(1+exp((x-x0)/dx)) + (a2*x+b2)*(1-1/(1+exp((x-x0)/dx)))'

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a1', 0))
    self.addParam(FitParam('b1', 0))
    self.addParam(FitParam('a2', 0))
    self.addParam(FitParam('b2', y2*0.8))
    self.addParam(FitParam('x0', (x1+x2)/2))
    self.addParam(FitParam('dx', 1))


    y0 = '(a1*x0+b1)/2 + (a2*x0+b2)/2'
    y0 = self.eval('y0', y0, None)
    x1 = self.eval('x1', 'x0+2*dx', self.dx)
    self.addHandle(FitHandleLine(view, self.x0, y0, x1, y0))
    self.addHandle(FitHandlePosition(view, self.x0, y0))


    self.addParam(FitParam('cx1', self.x0.value(), hidden=True))
    self.addParam(FitParam('cy1', self.b1.value(), hidden=True))
    self.a1.valueChanged.connect(lambda: self.setB(1))
    self.b1.valueChanged.connect(lambda: self.setcy(1))
    self.cx1.valueChanged.connect(lambda: self.setB(1))
    self.cy1.valueChanged.connect(lambda: self.setB(1))
    self.addHandle(FitHandleGradient(view, self.cx1, self.cy1, self.a1, 50, False))
    self.addHandle(FitHandlePosition(view, self.cx1, self.cy1))

    self.addParam(FitParam('cx2', self.x0.value(), hidden=True))
    self.addParam(FitParam('cy2', self.b2.value(), hidden=True))
    self.a2.valueChanged.connect(lambda: self.setB(2))
    self.b2.valueChanged.connect(lambda: self.setcy(2))
    self.cx2.valueChanged.connect(lambda: self.setB(2))
    self.cy2.valueChanged.connect(lambda: self.setB(2))
    self.addHandle(FitHandleGradient(view, self.cx2, self.cy2, self.a2, 50))
    self.addHandle(FitHandlePosition(view, self.cx2, self.cy2))

  def setB(self, num):
    cx = getattr(self, 'cx%d' % num)
    cy = getattr(self, 'cy%d' % num)
    a = getattr(self, 'a%d' % num)
    b = getattr(self, 'b%d' % num)
    b.setValue(cy.value() - a.value()*cx.value())

  def setcy(self, num):
    cx = getattr(self, 'cx%d' % num)
    cy = getattr(self, 'cy%d' % num)
    a = getattr(self, 'a%d' % num)
    b = getattr(self, 'b%d' % num)
    cy.setValue(a.value()*cx.value()+b.value())



class FitFuncConstant(FitFunctionBase):
  name = 'constant'
  label = 'Constant'
  expr = 'y0'

  def __init__(self, view):
    super().__init__(view)
    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('y0', y2*0.8))
    self.addParam(FitParam('x0', x1, hidden=True))
    self.addHandle(FitHandlePosition(view, self.x0, self.y0))



class FitFuncHeaviside(FitFunctionBase):
  name = 'heaviside'
  label = 'Heaviside'
  expr = 'a*heaviside(x-x0, 1)'

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', y2*0.8))
    self.addParam(FitParam('x0', (x1 + x2)/2))

    self.addHandle(FitHandlePosition(view, self.x0, self.a))



class FitFuncRectangularWindow(FitFunctionBase):
  name = 'rectangularwinow'
  label = 'Rectangular window'
  expr = 'a*heaviside(x-x0, 1)*heaviside(-(x-x1), 1)'

  def __init__(self, view):
    super().__init__(view)

    r = view.viewRect()
    x1, x2, y1, y2 = r.left(), r.right(), r.top(), r.bottom()
    self.addParam(FitParam('a', y2*0.8))
    self.addParam(FitParam('x0', x1 + (x2-x1)*0.2))
    self.addParam(FitParam('x1', x2 - (x2-x1)*0.2))

    self.addHandle(FitHandlePosition(view, self.x0, self.a))
    self.addHandle(FitHandlePosition(view, self.x1, self.a))
