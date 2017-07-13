import sys, os
import re
import logging

import log


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

  def getColumn(self, c):
    return [self.getValue(r, c) for r in range(self.rowCount())]

  def colCount(self):
    raise NotImplementedError()

  def rowCount(self):
    raise NotImplementedError()

  def getValue(self, r, c):
    raise NotImplementedError()

  def freeFunctions(self, expr):
    from sympy.core.function import UndefinedFunction
    ret = set()
    if expr.is_Atom:
      return ret
    if expr.is_Function and isinstance(type(expr), UndefinedFunction):
      ret.add(expr)
    return ret.union(*(self.freeFunctions(a) for a in expr.args))

  def parseFormula(self, formula):
    from functions import parseTableColumnLabel
    from sympy.parsing.sympy_parser import parse_expr

    exprs = parse_expr(formula)
    if not isinstance(exprs, tuple):
      exprs = exprs,

    ret = []
    for expr in exprs:
      freefunc = self.freeFunctions(expr)
      if freefunc:
        raise InvalidFormulaError('Undefined functions: %s' % ','.join(freefunc))

      variables = []
      for sym in expr.free_symbols:
        if not re.match(r'\A[A-Z]+\Z', sym.name):
          raise InvalidFormulaError('Invalid variable: %s' % sym.name)
        c = parseTableColumnLabel(sym.name)
        if c >= self.colCount():
          raise InvalidFormulaError('The sheet does not have such a column: %s' % sym.name)
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
          subs = dict([(sym, float(self.getValue(r, c))) for sym, c in variables])
          val = expr.evalf(subs=subs)
        except ValueError:
          val = None
        except:
          log.excepthook(*sys.exc_info())
          print(formula)
          val = None
        cols.append(val)
      rows.append(cols)
    return rows


class FileLoaderBase:

  class Iterator:
    def __init__(self, loader):
      self.loader = loader
      self.i = 0

    def __next__(self):
      if self.i == len(self.loader):
        raise StopIteration()
      s = self.loader[self.i]
      self.i += 1
      return s


  def __iter__(self):
    return self.Iterator(self)

  def __len__(self):
    return self.sheetCount()

  def __getitem__(self, i):
    return self.getSheet(i)


  def sheetCount(self):
    raise NotImplementedError()

  def getSheet(self, idx):
    raise NotImplementedError()


  @classmethod
  def canLoad(cls, mimetype):
    pat = getattr(cls, 're_pat', None)
    if pat:
      return re.search(pat, mimetype)
    raise NotImplementedError()


class FileLoaderText(FileLoaderBase):
  re_pat = '^text/plain'
  delimiter = r'\s+'


  class Sheet(SheetBase):
    def __init__(self, filename, delimiter):
      super().__init__(filename, 0, os.path.basename(filename))
      text = open(filename).read()

      self.rows = []
      for l in text.split('\n'):
        if l.startswith('#@ '): l = l[3:]
        l = l.strip()
        if l == '' or l.startswith('#'): continue
        self.rows.append(list(map(str.strip, re.split(delimiter, l))))

      self.ncols = max(map(len, self.rows))

    def colCount(self):
      return self.ncols

    def rowCount(self):
      return len(self.rows)

    def getValue(self, r, c):
      r = self.rows[r]
      return r[c] if c < len(r) else ''


  def __init__(self, filename):
    logging.info('Load text file: %s' % filename)
    self.sheet = self.Sheet(filename, self.delimiter)

  def sheetCount(self):
    return 1

  def getSheet(self, idx):
    return self.sheet


class FileLoaderCSV(FileLoaderText):
  re_pat = '^text/csv'
  delimiter = r','


class FileLoaderExcel(FileLoaderBase):
  re_pat = r'^application/vnd\.(?:openxmlformats-officedocument\.|ms-excel\.|oasis\.opendocument\.spreadsheet)'


  class Sheet(SheetBase):
    def __init__(self, filename, idx, sheet):
      super().__init__(filename, idx, sheet.name)
      self.sheet = sheet

    def colCount(self):
      return self.sheet.number_of_columns()

    def rowCount(self):
      return self.sheet.number_of_rows()

    def getValue(self, y, x):
      return self.sheet.cell_value(y, x)


  def __init__(self, filename):
    import pyexcel
    logging.info('Trying to load by pyexcel: %s' % filename)
    self.filename = filename
    self.book = pyexcel.get_book(file_name=filename)

  def sheetCount(self):
    return self.book.number_of_sheets()

  def getSheet(self, idx):
    return self.Sheet(self.filename, idx, self.book[idx])

  @classmethod
  def canLoad(cls, mimetype):
    return True


def load(filename):
  from PyQt5.QtCore import QMimeDatabase
  try:
    from pyexcel.exceptions import FileTypeNotSupported
  except ModuleNotFoundError:
    from pyexcel.sources.factory import FileTypeNotSupported
  loaders = [FileLoaderText, FileLoaderCSV, FileLoaderExcel]

  t = QMimeDatabase().mimeTypeForFile(filename).name()
  for o in loaders:
    if o.canLoad(t):
      try:
        return o(filename)
      except FileTypeNotSupported:
        pass

  raise UnsupportedFileException(filename, t)
