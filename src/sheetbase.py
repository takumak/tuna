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

    self.formulacache = {}
    self.evalcache = {}

  def validate(self, formula):
    self.parseFormula(formula)
    return QValidator.Acceptable, 'OK'

  def getColumn(self, c):
    return [self.getValue(r, c) for r in range(self.rowCount())]

  def colCount(self):
    raise NotImplementedError()

  def rowCount(self):
    raise NotImplementedError()

  def getValue(self, r, c):
    raise NotImplementedError()

  def xValues(self):
    return np.array(list(zip(*self.evalFormula(self.xFormula.strValue()))))

  def yValues(self, withError=False):
    return np.array(list(zip(*self.evalFormula(self.yFormula.strValue(), withError))))

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

      variables = []
      for sym in expr.free_symbols:
        if not re.match(r'\A[A-Z]+\Z', sym.name):
          raise InvalidFormulaError('Invalid variable: %s' % sym.name)
        c = parseTableColumnLabel(sym.name)
        if c >= self.colCount():
          raise InvalidFormulaError('The sheet does not have such a column: %s' % sym.name)
        variables.append((sym, c))

      ret.append((expr, variables))

    self.formulacache[formula] = ret
    return ret

  def evalFormula(self, formula, withError=False):
    cachekey = formula, withError
    if cachekey in self.evalcache:
      return self.evalcache[cachekey]

    exprs = self.parseFormula(formula)
    rows = []
    for r in range(self.rowCount()):
      cols = []
      for expr, variables in exprs:
        cols.append(self.evalRowExpr(r, expr, variables, withError))
      rows.append(cols)

    self.evalcache[cachekey] = rows
    return rows

  def evalRowExpr(self, row, expr, variables, withError=False):
    try:
      vals = {}
      errs = {}
      for sym, c in variables:
        v = self.getValue(row, c)
        try:
          v = float(v)
        except ValueError:
          return (None, None) if withError else None
        vals[sym] = v
        if withError:
          errexpr, errvars = self.parseFormula(self.errors[c])[0]
          errs[sym] = self.evalRowExpr(row, errexpr, errvars, False) or 0

      val = expr.evalf(subs=vals)
      if not withError: return val

      err = []
      for sym, v in vals.items():
        grad = expr.diff(sym).evalf(subs=vals)
        sigma = errs[sym]
        err.append((grad*sigma)**2)
      return val, np.sum(err)**.5

    except:
      log.warnException()
      return (None, None) if withError else None
