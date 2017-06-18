import os
import re
import xlrd
from PyQt5.QtCore import QMimeDatabase


from log import log


class FileLoaderBase:

  class Sheet:
    def __init__(self, name):
      self.name = name

    def getColumn(self, c):
      return [self.getValue(r, c) for r in range(self.rowCount())]

    def colCount(self):
      raise NotImplementedError()

    def rowCount(self):
      raise NotImplementedError()

    def getValue(self, r, c):
      raise NotImplementedError()

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


  class Sheet(FileLoaderBase.Sheet):
    def __init__(self, filename, delimiter):
      super().__init__(os.path.basename(filename))
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
    log('Load text file: %s' % filename)
    self.sheet = self.Sheet(filename, self.delimiter)

  def sheetCount(self):
    return 1

  def getSheet(self, idx):
    return self.sheet


class FileLoaderCSV(FileLoaderText):
  re_pat = '^text/csv'
  delimiter = r','


class FileLoaderExcel(FileLoaderBase):
  re_pat = r'application/vnd\.(?:openxmlformats-officedocument|ms-excel)\.'


  class Sheet(FileLoaderBase.Sheet):
    def __init__(self, sheet):
      super().__init__(sheet.name)
      self.sheet = sheet

    def colCount(self):
      return self.sheet.ncols

    def rowCount(self):
      return self.sheet.nrows

    def getValue(self, y, x):
      return self.sheet.cell(y, x).value


  def __init__(self, filename):
    import xlrd
    log('Load Excel file: %s' % filename)
    self.sheets = xlrd.open_workbook(filename).sheets()

  def sheetCount(self):
    return len(self.sheets)

  def getSheet(self, idx):
    return self.Sheet(self.sheets[idx])


def load(filename):
  loaders = [FileLoaderText, FileLoaderCSV, FileLoaderExcel]

  t = QMimeDatabase().mimeTypeForFile(filename).name()
  for o in loaders:
    if o.canLoad(t):
      return o(filename)

  return None
