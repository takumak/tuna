import uuid
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

from functions import blockable
from fitparameters import *
from fitgraphitems import *
from fitfuncdescriptor import FitFuncDescriptor



class FitFunctionBase(QObject):
  parameterChanged = pyqtSignal(QObject, name='parameterChanged')
  highlightChanged = pyqtSignal(QObject, bool)
  expr_excel = None

  def __init__(self, view):
    super().__init__()
    self.view = view
    self.id = str(uuid.uuid4())
    self.params = []
    self.paramsNameMap = {}
    self.handles = []

    self.plotCurveItem = None
    self.highlighted = False

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
    param.func = self
    self.params.append(param)
    self.paramsNameMap[param.name] = param
    param.valueChanged.connect(self.paramChanged)

  @blockable
  def paramChanged(self):
    if self.plotCurveItem:
      x = self.plotCurveItem.x
      self.plotCurveItem.setXY(x, y=self.y(x))
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
    self.plotCurveItem = PlotCurveItem(x, self.y(x), self.view, color)
    items = [self.plotCurveItem] + sum([h.getGraphItems(color) for h in self.handles], [])

    touchables = [item for item in items if item.touchable]
    for item in touchables:
      item.hoveringChanged.connect(lambda: self.setHighlighted(
        True in [item.hovering for item in touchables]))

    return items

  def eval(self, name, formula, setArg, **kwargs):
    return FitParamFormula(name, formula, setArg, self.params, **kwargs)

  def eval2(self, name, formula, setEquations):
    return FitParamFormula2(name, formula, setEquations, self.params)

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
    fixedv = [self.paramsNameMap[n].value() for n in fixed]
    args = ['x'] + paramNames + fixed
    func = lambdify([Symbol(a) for a in args], expr, 'numpy')

    return lambda x, *vals: self.samedim(func(x, *(list(vals) + fixedv)), x)

  @classmethod
  def samedim(cls, y, x):
    try:
      i = iter(y)
    except TypeError:
      return np.full(x.shape, y)
    return y

  def y(self, x):
    from sympy import Symbol, lambdify
    expr = self.parse_expr(self.expr)
    args = [Symbol('x')]+[Symbol(p.name) for p in self.params]
    func = lambdify(args, expr, 'numpy')

    y = lambda x: self.samedim(func(x, *[p.value() for p in self.params]), x)
    self.y = y
    return y(x)

  def setHighlighted(self, highlighted):
    highlighted = bool(highlighted)
    if highlighted != self.highlighted:
      self.highlighted = highlighted
      self.highlightChanged.emit(self, highlighted)
    if self.plotCurveItem:
      self.plotCurveItem.setHighlighted(highlighted)

  @classmethod
  def excelExpr(cls):
    if not cls.expr_excel:
      from sympy.parsing.sympy_parser import parse_expr
      from sympy import Symbol
      expr = parse_expr(cls.expr)
      expr = expr.subs([(s, Symbol('%%(%s)s' % s.name)) for s in expr.free_symbols])
      cls.expr_excel = str(expr)
    return cls.expr_excel

  @classmethod
  def getDescriptorWidget(cls):
    if not hasattr(cls, 'descriptorWidget'):
      cls.descriptorWidget = FitFuncDescriptor(cls)
    return cls.descriptorWidget
