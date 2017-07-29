from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np
import pyqtgraph as pg

from fitparameters import *
from fithandles import *



__all__ = ['FitFuncGaussian', 'FitFuncTwoLines']



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

  def getGraphItems(self, x, **opts):
    self.plotCurveItem = pg.PlotCurveItem(
      x=x, y=self.y(x),
      antialias=True,
      name=self.name,
      **opts
    )
    return [self.plotCurveItem] + sum([h.getGraphItems() for h in self.handles], [])

  def eval(self, name, formula, setArgName, **params):
    from sympy.parsing.sympy_parser import parse_expr
    from sympy.solvers import solve
    from sympy import Symbol, Eq, lambdify
    expr = parse_expr(formula)
    args = list(expr.free_symbols)
    func = lambdify(args, expr, 'numpy')

    params.update(self.paramsNameMap)

    if setArgName:
      expr_i = solve(Eq(expr, Symbol('__')), Symbol(setArgName))
      if len(expr_i) != 1:
        raise RuntimeError('Could not determine the inverse function of "y=%s"' % formula)
      expr_i = expr_i[0]
      args_i = list(expr_i.free_symbols)
      func_i = lambdify(args_i, expr_i, 'numpy')
    else:
      func_i = None

    def wrap(func):
      return lambda: func(*[params[a.name].value() for a in args])

    anames = [a.name for a in args if a.name != setArgName]
    if setArgName:
      anames.insert(0, setArgName)

    return FitParameterFunc(name, func, func_i, *[params[a] for a in anames])



class FitFuncGaussian(FitFunctionBase):
  name = 'gaussian'
  label = 'Gaussian'
  expr = 'a*exp[-(x-b)^2/2c^2]'

  def __init__(self, lines, view):
    super().__init__()

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParameter('a', self.getHeight(lines)*0.6))
    self.addParam(FitParameter('b', (x1 + x2)/2))
    self.addParam(FitParameter('c', (x2 - x1)*0.1))

    HWHM = self.c*np.sqrt(2*np.log(2))
    self.addHandle(FitHandlePosition(view, self.b, self.a))
    # self.addHandle(FitHandleThetaLength(self.b, self.a/2, FitParameterConst('theta', 0), HWHM))
    # self.addHandle(FitHandleThetaLength(self.b, self.a/2, FitParameterConst('theta', np.pi), HWHM))

  def y(self, x):
    return self.a.value()*np.exp(-(x-self.b.value())**2/(2*self.c.value()**2))



class FitFuncTwoLines(FitFunctionBase):
  name = 'twoline'
  label = 'TwoLines'
  expr = '(a1*x+b1)/(1+exp((x-x0)/dx)) + (a2*x+b2)*(1-1/(1+exp((x-x0)/dx)))'

  def __init__(self, lines, view):
    super().__init__()

    x1, x2 = self.getXrange(lines)
    self.addParam(FitParameter('a1', 0))
    self.addParam(FitParameter('b1', 0))
    self.addParam(FitParameter('a2', 0))
    self.addParam(FitParameter('b2', self.getHeight(lines)*0.8))
    self.addParam(FitParameter('x0', (x1+x2)/2))
    self.addParam(FitParameter('dx', 1))

    y0 = '(a1*x0+b1)/2 + (a2*x0+b2)/2'
    y0 = self.eval('y0', y0, None)
    x1 = self.eval('x1', 'x0+dx', 'dx')
    self.addHandle(FitHandleLine(view, self.x0, y0, x1, y0))
    self.addHandle(FitHandlePosition(view, self.x0, y0))


    handlelen = min(self.getWidth(lines), self.getHeight(lines))*0.2
    handlelen = FitParameterConst('len', 10)


    theta1 = self.eval('theta1', 'atan(a1)+pi', 'a1')
    theta1.setValue(-np.pi)
    theta1.min_ = np.pi/2
    theta1.max_ = np.pi*3/2
    cx1 = FitParameter('cx1', self.x0.value())
    cy1 = FitParameter('cy1', self.b1.value())
    def setb1():
      b1 = cy1.value() - np.tan(self.a1.value())*cx1.value()
      self.b1.setValue(b1)
    self.a1.valueChanged.connect(setb1)
    cx1.valueChanged.connect(setb1)
    cy1.valueChanged.connect(setb1)
    self.addHandle(FitHandleTheta(view, cx1, cy1, theta1, 50))
    self.addHandle(FitHandlePosition(view, cx1, cy1))


    theta2 = self.eval('theta2', 'atan(a2)', 'a2')
    theta2.setValue(0)
    theta2.min_ = -np.pi/2
    theta2.max_ = np.pi/2
    cx2 = FitParameter('cx2', self.x0.value())
    cy2 = FitParameter('cy2', self.b2.value())
    def setb2():
      b2 = cy2.value() - np.tan(self.a2.value())*cx2.value()
      self.b2.setValue(b2)
    self.a2.valueChanged.connect(setb2)
    cx2.valueChanged.connect(setb2)
    cy2.valueChanged.connect(setb2)
    self.addHandle(FitHandleTheta(view, cx2, cy2, theta2, 50))
    self.addHandle(FitHandlePosition(view, cx2, cy2))

  def y(self, x):
    r = 1/(1+np.exp((x-self.x0.value())/self.dx.value()))
    l1 = self.a1.value()*x + self.b1.value()
    l2 = self.a2.value()*x + self.b2.value()
    return l1*r + l2*(1-r)
