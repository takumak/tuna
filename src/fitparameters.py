import operator
from PyQt5.QtCore import QObject, pyqtSignal
import numpy as np

from functions import blockable
from settingitems import *



__all__ = ['FitParam', 'FitParamConst', 'FitParamFunc', 'FitParamFormula']



class FitParam(QObject):
  valueChanged = pyqtSignal()
  plotModes = [
    ('absolute', 'Absolute values'),
    ('diff', 'Differences'),
    ('ratio', 'Differences in ratio')
  ]

  def __init__(self, name, default, hidden=False, plotMode='absolute'):
    super().__init__()
    self.name = name
    self.value_ = default
    self.hidden = hidden
    self.plotMode = plotMode

    self.min_ = None
    self.max_ = None

    self.readOnly = False

  def value(self):
    return self.value_

  def checkValue(self, value):
    from numbers import Number
    if not isinstance(value, Number):
      raise TypeError('Fit parameter value must be a number, but got %s' % value)

    if self.max_ is not None and value > self.max_: value = self.max_
    if self.min_ is not None and value < self.min_: value = self.min_

    return value

  def setValue(self, value):
    value = self.checkValue(value)
    if value != self.value_:
      self.value_ = value
      self.valueChanged.emit()

  def plotValues(self, values):
    fname = 'plotValues_%s' % self.plotMode
    if not hasattr(self, fname):
      raise RuntimeError('Invalid plot mode - %s' % self.plotMode)
    return getattr(self, fname)(np.array(values))

  def plotValues_absolute(self, values):
    return values

  def plotValues_diff(self, values):
    return values - values[0]

  def plotValues_ratio(self, values):
    return (values - values[0])/values[0]



class FitParamConst(FitParam):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.readOnly = True

  def setValue(self, value):
    pass



class FitParamFunc(FitParam):
  def __init__(self, name, get_, set_, refargs, **kwargs):
    self.get_ = get_
    self.set_ = set_
    super().__init__(name, self.value(), **kwargs)

    if set_ is None:
      self.readOnly = True

    for a in refargs:
      a.valueChanged.connect(lambda: self.valueChanged.emit())

  def value(self):
    return self.get_()

  def setValue(self, value):
    if self.set_:
      self.set_(value)



class FitParamFormula(FitParamFunc):
  def __init__(self, name, formula, setArg, refargs, **kwargs):
    from sympy.parsing.sympy_parser import parse_expr
    from sympy.solvers import solve
    from sympy import Symbol, Eq, lambdify

    expr = parse_expr(formula)
    args = list(expr.free_symbols)
    func = lambdify(args, expr, 'numpy')

    params = dict([(a.name, a) for a in refargs])
    refargs = [params[a.name] for a in args]

    if setArg:
      expr_i = solve(Eq(expr, Symbol('__')), Symbol(setArg.name))
      if len(expr_i) != 1:
        raise RuntimeError('Could not determine the inverse function of "y=%s"' % formula)
      expr_i = expr_i[0]
      args_i = list(expr_i.free_symbols)
      func_i = lambdify(args_i, expr_i, 'numpy')
    else:
      func_i = None

    get_ = lambda: func(*[params[a.name].value() for a in args])

    if setArg:
      tosetval = lambda v: func_i(*[
        (v if a.name == '__' else params[a.name].value()) for a in args_i])
      set_ = lambda v: setArg.setValue(tosetval(v))
    else:
      set_ = None

    super().__init__(name, get_, set_, refargs, **kwargs)
