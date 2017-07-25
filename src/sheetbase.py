import re
import numpy as np
from PyQt5.QtGui import QValidator

import log
from methodbase import ParamStr



class UnsupportedFileException(Exception):
  def __init__(self, filename, mimetype):
    super().__init__()
    self.filename = filename
    self.mimetype = mimetype

class InvalidFormulaError(Exception): pass

class SheetBase:
  def __init__(self, filename, idx, name):
    self.filename = filename
    self.idx = idx
    self.name = name
    self.xFormula = ParamStr('xformula', 'X', 'A', self.validate)
    self.yFormula = ParamStr('yformula', 'Y', 'B', self.validate)

    from functions import getTableColumnLabel
    self.errors = ['sqrt(%s)' % getTableColumnLabel(c) for c in range(self.colCount())]

    self.columncache = {}
    self.formulacache = {}
    self.formulaerrcache = {}
    self.evalcache = {}
    self.evalerrcache = {}

  def validate(self, formula):
    self.parseFormula(formula)
    return QValidator.Acceptable, 'OK'

  def getColumnValuesF(self, c):
    if c not in self.columncache:
      values = []
      for r in range(self.rowCount()):
        v = self.getValue(r, c)
        try:
          v = float(v)
        except:
          v = np.nan
        values.append(v)
      self.columncache[c] = np.array(values)
    return self.columncache[c]

  def colCount(self):
    raise NotImplementedError()

  def rowCount(self):
    raise NotImplementedError()

  def getValue(self, r, c):
    raise NotImplementedError()

  def xValues(self):
    return self.evalFormula(self.xFormula.strValue())

  def yValues(self):
    return self.evalFormula(self.yFormula.strValue())

  def yErrors(self):
    return self.evalFormulaError(self.yFormula.strValue())

  def setError(self, col, formula):
    self.errors[col] = formula
    self.formulacache.clear()
    self.evalcache.clear()

  def freeFunctions(self, expr):
    from sympy.core.function import UndefinedFunction
    ret = set()
    if expr.is_Atom:
      return ret
    if expr.is_Function and isinstance(type(expr), UndefinedFunction):
      ret.add(expr)
    return ret.union(*(self.freeFunctions(a) for a in expr.args))

  def parseFormula(self, formula):
    if formula in self.formulacache:
      return self.formulacache[formula]

    from functions import parseTableColumnLabel
    import sympy
    from sympy import lambdify
    from sympy.parsing.sympy_parser import parse_expr
    from sympy.core.function import FunctionClass

    global_dict = {}
    for n in dir(sympy):
      if len(n) == 1 and n in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ': continue
      v = getattr(sympy, n)
      if isinstance(v, FunctionClass) or callable(v):
        global_dict[n] = v

    exprs = parse_expr(formula, global_dict=global_dict)
    if not isinstance(exprs, tuple):
      exprs = exprs,

    ret = []
    for expr in exprs:
      freefunc = self.freeFunctions(expr)
      if freefunc:
        raise InvalidFormulaError('Undefined functions: %s' % ','.join(map(str, freefunc)))

      args = []
      args_c = []
      for sym in expr.free_symbols:
        if not re.match(r'\A[A-Z]+\Z', sym.name):
          raise InvalidFormulaError('Invalid variable: %s' % sym.name)
        c = parseTableColumnLabel(sym.name)
        if c >= self.colCount():
          raise InvalidFormulaError('The sheet does not have such a column: %s' % sym.name)
        args.append(sym)
        args_c.append(c)

      f = lambdify(args, expr, 'numpy')
      ret.append((f, expr, args, args_c))

    self.formulacache[formula] = ret
    return ret

  def getErrorFunc(self, formula):
    if formula in self.formulaerrcache:
      return self.formulaerrcache[formula]

    import sympy

    exprs = self.parseFormula(formula)
    ret = []

    for f, expr, args, args_c in exprs:
      errs = [self.parseFormula(self.errors[c])[0] for c in args_c]
      errexprs = [e for f, e, a, c in errs]

      expr_ = sympy.sqrt(sum([expr.diff(a)**2*(e**2) for a, e in zip(args, errexprs)]))
      errargs = sum([a for f, e, a, c in errs], [])
      errargs_c = sum([c for f, e, a, c in errs], [])
      args_ = set([(a, c) for a, c in zip(args+errargs, args_c+errargs_c)])
      args = [a for a, c in args_]
      args_c = [c for a, c in args_]

      f_ = sympy.lambdify(args, expr_, 'numpy')
      ret.append((f_, expr_, args, args_c))

    self.formulaerrcache[formula] = ret
    return ret

  def valuesOfRowCount(self, vals):
    try:
      i = iter(vals)
    except TypeError:
      return np.array([vals]*self.rowCount())

    if len(vals) != self.rowCount():
      raise RuntimeError('Invalid value count')

    return vals

  def evalFormula(self, formula):
    if formula in self.evalcache:
      return self.evalcache[formula]

    from sympy import lambdify

    exprs = self.parseFormula(formula)
    cols = []
    for f, expr, args, args_c in exprs:
      cols.append(self.valuesOfRowCount(
        f(*[self.getColumnValuesF(c) for c in args_c])))

    self.evalcache[formula] = cols
    return cols

  def evalFormulaError(self, formula):
    if formula in self.evalerrcache:
      return self.evalerrcache[formula]

    from sympy import lambdify

    exprs = self.getErrorFunc(formula)
    cols = []
    for f, expr, args, args_c in exprs:
      cols.append(self.valuesOfRowCount(
        f(*[self.getColumnValuesF(c) for c in args_c])))

    self.evalerrcache[formula] = cols
    return cols
