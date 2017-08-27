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

  def complete(self, xoff=None, yoff=None):
    opts = {}
    if xoff is not None: opts['x_offset'] = xoff
    if yoff is not None: opts['y_offset'] = yoff
    self.range.sheet.insert_chart(self.range.cellName(), self.chart, opts)




class XlsxRange:
  chartBorderColor = '#aaaaaa'

  def __init__(self, exporter, sheet, rows, cols):
    self.exporter = exporter
    self.book = exporter.book
    self.sheet = sheet
    self.rows = rows
    self.cols = cols

  def addChart(self, name, title=None,
               xlabel=None, ylabel=None,
               xformat=None, yformat=None,
               width=None, height=None, legend=False,
               markers=False):

    if markers:
      subtype = 'straight_with_markers'
    else:
      subtype = 'straight'

    chart = self.book.add_chart({'type': 'scatter', 'subtype': subtype})
    if title is None:
      chart.set_title({'none': True})
    else:
      chart.set_title({'name': title})

    chart.set_x_axis({
      'name': xlabel or self.exporter.xLabel(name),
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside',
      'line': {'color': self.chartBorderColor},
      'num_format': xformat
    })

    chart.set_y_axis({
      'name': ylabel or self.exporter.yLabel(name),
      'major_gridlines': {'visible': False},
      'major_tick_mark': 'inside',
      'line': {'color': self.chartBorderColor},
      'num_format': yformat
    })

    chart.set_plotarea({
      'border': {'color': self.chartBorderColor}
    })

    if not legend:
      chart.set_legend({'none': True})

    if width is not None or height is not None:
      chart.set_size({'width': width, 'height': height})

    return XlsxChart(self, chart)

  def width(self):
    if self.cols.stop is None:
      return math.inf
    return self.cols.stop - self.cols.start

  def height(self):
    if self.rows.stop is None:
      return math.inf
    return self.rows.stop - self.rows.start

  def setWidth(self, width):
    self.cols = slice(self.cols.start, self.cols.start + width)

  def setHeight(self, height):
    self.rows = slice(self.rows.start, self.rows.start + width)

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

    return XlsxRange(self.exporter, self.sheet, rows, cols)

  def write(self, val, fmt=None):
    if self.isList(val):
      self.writeVertical(val, fmt)
    else:
      self.writeConst(val, fmt)

  def writeConst(self, val, fmt):
    for r in range(self.rows.start, self.rows.stop):
      for c in range(self.cols.start, self.cols.stop):
        self.sheet.write(r, c, val, fmt)

  def writeVertical(self, vals, fmt):
    for r, val in enumerate(vals):
      self[r,:].writeHorizontal(val, fmt)

  def writeHorizontal(self, vals, fmt):
    if not self.isList(vals):
      vals = [vals]
      if self.cols.stop is not None:
        vals = vals*self.width()
    for c, val in enumerate(vals):
      self.sheet.write(self.rows.start, self.cols.start+c, val, fmt)

  def merge(self, val):
    if self.width() == 1 and self.height() == 1:
      self.write(val)
      return

    r1, r2 = self.rows.start, self.rows.stop - 1
    c1, c2 = self.cols.start, self.cols.stop - 1
    self.sheet.merge_range(r1, c1, r2, c2, val)

  def below(self):
    if self.rows.stop is None:
      raise RuntimeError('Right side must be specified')
    return XlsxRange(self.exporter, self.sheet,
                     slice(self.rows.stop, None),
                     slice(self.cols.start, self.cols.stop))

  def right(self):
    if self.cols.stop is None:
      raise RuntimeError('Right side must be specified')
    return XlsxRange(self.exporter, self.sheet,
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

  def __init__(self):
    self.xLabels = {'source': 'Energy (eV)'}
    self.yLabels = {'source': 'Intensity (a.u.)'}
    self.formatCache = {}

  def xLabel(self, name, default=None):
    return self.xLabels.get(name, default)

  def yLabel(self, name, default=None):
    return self.yLabels.get(name, default)

  def setXlabel(self, name, label):
    self.xLabels[name] = label

  def setYlabel(self, name, label):
    self.yLabels[name] = label

  def write(self, book):
    self.book = book
    self.sheets = {}

  def addSheet(self, name):
    sheet = self.book.add_worksheet(name)
    sheet = XlsxRange(self, sheet, slice(0, None), slice(0, None))
    sheet[0,0].write(self.recalcMsg)
    sheet = sheet[1:,:]
    self.sheets[name] = sheet
    setattr(self, name.replace(' ', '_'), sheet)
    return sheet

  def __getitem__(self, name):
    if name not in self.sheets:
      raise KeyError('Invalid sheet name: %s' % repr(name))
    return self.sheets[name]

  def getFormat(self, fmt):
    if fmt in self.formatCache:
      return self.formatCache[fmt]

    fmt_ = self.book.add_format({'num_format': fmt})
    self.formatCache[fmt] = fmt_
    return fmt_
