import operator

from settingitems import *



__all__ = ['FitParam', 'FitParamConst', 'FitParamFunc', 'FitParamFormula']



class FitParam(SettingItemFloat):
  def __init__(self, name, default, hidden=False):
    super().__init__(name, name, default)
    self.hidden = hidden

  def setValue(self, value):
    if self.max_ is not None and value > self.max_: value = self.max_
    if self.min_ is not None and value < self.min_: value = self.min_

    from numbers import Number
    if not isinstance(value, Number):
      raise TypeError('Fit parameter value must be a number, but got %s' % value)

    super().setStrValue(str(value))



class FitParamConst(FitParam):
  def setValue(self, value):
    pass



class FitParamFunc(FitParam):
  def __init__(self, name, get_, set_, refargs):
    self.get_ = get_
    self.set_ = set_
    super().__init__(name, self.value())
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
    params.update(kwargs)
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
      set_ = lambda v: setArg.setValue(func_i(*[
        (v if a.name == '__' else params[a.name].value()) for a in args_i]))
    else:
      set_ = None

    super().__init__(name, get_, set_, refargs)
