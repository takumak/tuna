import math
import logging
import numpy as np
from xlsxwriter.utility import \
  xl_rowcol_to_cell, xl_range, xl_range_abs



class XlsxChart:
  def __init__(self, range_, chart):
    self.range = range_
    self.chart = chart

  def add(self, x, y):
    if y.width() > 1:
      for c in range(y.width()):
        self.add(x, y[:,c])
      return

    self.chart.add_series({
      'name':       "=%s" % y[0,0].cellName(True),
      'categories': "=%s" % x[1:,:].rangeName(True),
      'values':     "=%s" % y[1:,:].rangeName(True),
      'line':       {'width': 1}
    })

  def complete(self, row=3, col=0):
    self.range.sheet.insert_chart(self.range[row,col].cellName(), self.chart)




class XlsxRange:
  def __init__(self, book, sheet, rows, cols):
    self.book = book
    self.sheet = sheet
    self.rows = rows
    self.cols = cols
    self.xLabels = {'source': 'Energy (eV)'}
    self.yLabels = {'source': 'Intensity (a.u.)'}

  def setXlabel(self, name, label):
    self.xLabels[name] = label

  def setYlabel(self, name, label):
    self.yLabels[name] = label

  def addChart(self, name, row=3, col=0):
    chart = self.book.add_chart({'type': 'scatter', 'subtype': 'straight'})
    chart.set_title({'none': True})
    chart.set_x_axis({
      'name': self.xLabels.get(name),
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })
    chart.set_y_axis({
      'name': self.yLabels.get(name),
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside'
    })
    return XlsxChart(self, chart)

  def width(self):
    if self.cols.stop is None:
      return math.inf
    return self.cols.stop - self.cols.start

  def height(self):
    if self.rows.stop is None:
      return math.inf
    return self.rows.stop - self.rows.start

  @classmethod
  def resolveRelativeSlice(self, rel_slice, curr_slice):
    if isinstance(rel_slice, int):
      rel_slice = slice(rel_slice, rel_slice+1)
    elif isinstance(rel_slice, slice):
      pass
    else:
      raise KeyError('Index key must be an int or a slice')

    start = (rel_slice.start or 0) + curr_slice.start
    stop = rel_slice.stop

    if stop is None:
      stop = curr_slice.stop
    else:
      stop += curr_slice.start

    if curr_slice.stop is not None:
      if start >= curr_slice.stop:
        raise KeyError('Start index must be less than %d' % curr_slice.stop)
      if stop is not None and stop > curr_slice.stop:
        raise KeyError('Stop index must be less than %d' % (curr_slice.stop - curr_slice.start - 1))

    return slice(start, stop)

  @classmethod
  def isList(self, val):
    return isinstance(val, (list, tuple, np.ndarray))

  def __getitem__(self, key):
    if not isinstance(key, tuple) or len(key) != 2:
      raise KeyError('You must specify columns and rows, such as: XlsxRange[1:,2:]')

    rows, cols = key
    rows = self.resolveRelativeSlice(rows, self.rows)
    cols = self.resolveRelativeSlice(cols, self.cols)

    return XlsxRange(self.book, self.sheet, rows, cols)

  def write(self, val):
    if self.isList(val):
      self.writeVertical(val)
    else:
      self.writeConst(val)

  def writeConst(self, val):
    for r in range(self.rows.start, self.rows.stop):
      for c in range(self.cols.start, self.cols.stop):
        self.sheet.write(xl_rowcol_to_cell(r, c), val)

  def writeVertical(self, vals):
    for r, val in enumerate(vals):
      self[r,:].writeHorizontal(val)

  def writeHorizontal(self, vals):
    if not self.isList(vals):
      vals = [vals]
      if self.cols.stop is not None:
        vals = vals*self.width()
    for c, val in enumerate(vals):
      self.sheet.write(xl_rowcol_to_cell(self.rows.start, self.cols.start+c), val)

  def merge(self, val):
    r1, r2 = self.rows.start, self.rows.stop - 1
    c1, c2 = self.cols.start, self.cols.stop - 1
    self.sheet.merge_range(r1, c1, r2, c2, val)

  def below(self):
    return XlsxRange(self.book, self.sheet,
                     slice(self.rows.stop, None),
                     slice(self.cols.start, self.cols.stop))

  def right(self):
    return XlsxRange(self.book, self.sheet,
                     slice(self.rows.start, self.rows.stop),
                     slice(self.cols.stop, None))

  def prependSheetName(self, name, do):
    if do:
      return "'%s'!%s" % (self.sheet.name, name)
    else:
      return name

  def cellName(self, sheetName=False):
    return self.prependSheetName(xl_rowcol_to_cell(self.rows.start, self.cols.start), sheetName)

  def rangeName(self, sheetName=False):
    return self.prependSheetName(xl_range(self.rows.start, self.cols.start,
                                          self.rows.stop-1, self.cols.stop-1),
                                 sheetName)

  def cellNames(self):
    rows = []
    if self.width() == 1:
      for r in range(self.rows.start, self.rows.stop):
        rows.append(xl_rowcol_to_cell(r, self.cols.start))
    else:
      for r in range(self.rows.start, self.rows.stop):
        cols = []
        rows.append(cols)
        for c in range(self.cols.start, self.cols.stop):
          cols.append(xl_rowcol_to_cell(r, c))
    return rows

  def format(self, fmt, **kwargs):
    kwargs['sheet'] = self.sheet.name
    return self.format_(fmt, self.cellNames(), **kwargs)

  def format_(self, fmt, names, fmtname='n', **kwargs):
    vals = []
    for name in names:
      if self.isList(name):
        vals.append(self.format_(fmt, name, kwargs))
      else:
        kwargs[fmtname] = name
        kwargs[fmtname.upper()] = "'%s'!%s" % (self.sheet.name, name)
        vals.append(fmt % kwargs)
    return vals

  def rowRanges(self):
    return [self[r,:] for r in range(self.height())]



class XlsxExporter:
  recalcMsg = 'Press F9 (for Excel) or Ctrl+Shift+F9 (for LibreOffice) to re-calculate cell formulae'

  def write(self, book):
    self.book = book
    self.sheets = {}

  def addSheet(self, name):
    sheet = self.book.add_worksheet(name)
    sheet = XlsxRange(self.book, sheet, slice(0, None), slice(0, None))
    sheet[0,0].write(self.recalcMsg)
    sheet = sheet[1:,:]
    self.sheets[name] = sheet
    return sheet

  def __getitem__(self, name):
    if name not in self.sheets:
      raise KeyError('Invalid sheet name: %s' % repr(name))
    return self.sheets[name]

  def __getattr__(self, name):
    return self[name]
