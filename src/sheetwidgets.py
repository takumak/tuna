import re
from PyQt5.QtCore import Qt, QVariant, pyqtSignal
from PyQt5.QtGui import QBrush
from PyQt5.QtWidgets import QTableWidgetItem

from commonwidgets import TableWidget
from functions import getTableColumnLabel


class SheetWidget(TableWidget):
  class InvalidFormulaError(Exception): pass

  useColumnRequested = pyqtSignal(int, str, bool, name='useColumnRequested')

  def __init__(self, sheet):
    super().__init__()
    self.sheet = sheet
    self.setColumnCount(sheet.colCount())
    self.setRowCount(sheet.rowCount())

    for c in range(sheet.colCount()):
      self.setHorizontalHeaderItem(c, QTableWidgetItem(getTableColumnLabel(c)))
      for r in range(sheet.rowCount()):
        self.setItem(r, c, QTableWidgetItem(str(self.sheet.getValue(r, c))))

  def freeFunctions(self, expr):
    from sympy.core.function import UndefinedFunction
    ret = set()
    if expr.is_Atom:
      return ret
    if expr.is_Function and isinstance(type(expr), UndefinedFunction):
      ret.add(expr)
    return ret.union(*(self.free_functions(a) for a in expr.args))

  def parseFormula(self, formula):
    from functions import parseTableColumnLabel
    from sympy.parsing.sympy_parser import parse_expr

    exprs = parse_expr(formula)
    if not isinstance(expr, tuple):
      exprs = exprs,

    ret = []
    for expr in exprs:
      freefunc = self.freeFunctions(expr)
      if freefunc:
        raise self.InvalidFormulaError('Undefined functions: %s' % ','.join(freefunc))

      variables = []
      for sym in expr.free_symbols:
        if not re.match(r'\A[A-Z]+\Z', sym.name):
          raise self.InvalidFormulaError('Invalid variable: %s' % sym.name)
        c = parseTableColumnLabel(sym.name)
        if c >= self.sheet.colCount():
          raise self.InvalidFormulaError('The sheet does not have such a column: %s' % sym.name)
        variables.append((sym, c))

      ret.append((expr, variables))

    return ret

  def evalFormula(self, formula):
    exprs = self.parseFormula(formula)
    rows = []
    for r in range(self.rowCount()):
      cols = []
      for expr, variables in exprs:
        try:
          subs = dict([(sym, sheet.getValue(r, c)) for sym, c in variables])
          val = expr.evalf(**subs)
        except:
          val = None
        cols.append(val)
      rows.append(cols)
    return rows
