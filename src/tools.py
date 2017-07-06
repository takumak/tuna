import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QSpinBox
import pyqtgraph as pg


class Line:
  def __init__(self, x, y, name):
    X, Y = [], []
    for _x, _y in zip(x, y):
      try:
        _x = float(_x)
        _y = float(_y)
        X.append(_x)
        Y.append(_y)
      except (ValueError, TypeError):
        pass

    self.x = np.array(X)
    self.y = np.array(Y)
    self.name = name

  def getXrange(self):
    return min(self.x), max(self.x)

  def getYrange(self):
    return min(self.y), max(self.y)

  def weightCenter(self):
    return sum(self.x*self.y)/sum(self.y)

  def integrate(self):
    return sum(self.y[:-1]*(self.x[1:]-self.x[:-1]))

  def normalize(self):
    return self.__class__(self.x, self.y/self.integrate(), self.name)

  def xoff(self, off):
    return self.__class__(self.x + off, self.y, self.name)

  def __sub__(self, other):
    if list(self.x) != list(other.x):
      raise RuntimeError('x is not same')
    return self.__class__(self.x, self.y - other.y, self.name)

  def peak(self):
    return max(zip(self.x, self.y), key=lambda p: p[1])


class InterpBase:
  class ParamBase:
    def __init__(self, name, default):
      self.name = name
      self.default = default
      self.widget = None

    def value(self):
      if hasattr(self, 'value_'):
        return self.value_
      return self.default

    def setValue(self, value):
      if value == self.value():
        return
      self.value_ = value
      self.updateWidgetValue(self.widget, value)

    def getWidget(self):
      if self.widget is None:
        self.widget = self.createWidget()
      return self.widget

  class ParamInt(ParamBase):
    def __init__(self, name, min_, max_, default):
      super().__init__(name, default)
      self.min = min_
      self.max = max_

    def updateWidgetValue(self, widget, value):
      if self.widget:
        self.widget.setValue(value)

    def createWidget(self):
      spin = QSpinBox()
      spin.setMinimum(self.min)
      spin.setMaximum(self.max)
      spin.setValue(self.value())
      spin.valueChanged.connect(self.setValue)
      return spin


  def __init__(self):
    self.params = []
    self.paramsMap = {}
    self.optionsWidget = None

  def do(self, line):
    raise NotImplementedError()

  def addParam(self, param):
    self.params.append(param)
    self.paramsMap[param.name] = param

  def __getattr__(self, name):
    if name in self.paramsMap:
      return self.paramsMap[name]
    raise AttributeError()

  def getOptionsWidget(self):
    if self.optionsWidget is None:
      self.optionsWidget = self.createOptionsWidget()
    return self.optionsWidget

  def createOptionsWidget(self):
    if not self.params:
      return None
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    for r, p in enumerate(self.params):
      grid.addWidget(QLabel(p.name), r, 0)
      grid.addWidget(p.getWidget(), r, 1)

    widget = QWidget()
    widget.setLayout(grid)
    return widget

  def saveState(self):
    return [{'name': p.name, 'value': p.value()} for p in self.params]

  def restoreState(self, state):
    for p in state:
      self.paramsMap[p['name']].setValue(p['value'])



class CubicSpline(InterpBase):
  name  = 'cubic_spline'
  label = 'Cubic spline'

  def __init__(self):
    super().__init__()
    self.addParam(self.ParamInt('N', 1, 999, 9))

  def do(self, line, xrange = None):
    if xrange:
      X1, X2 = xrange
    else:
      X1, X2 = min(line.x), max(line.x)

    n = sum([1 if v >= X1 and v <= X2 else 0 for v in line.x])
    npoints = n * (self.N.value() + 1)

    from scipy import interpolate
    tck = interpolate.splrep(line.x, line.y, s=0)
    dx = (X2 - X1)/npoints
    x2 = np.arange(X1, X2, dx)
    y2 = interpolate.splev(x2, tck, der=0)
    return Line(x2, y2, line.name)



class ToolBase(QObject):
  cleared = pyqtSignal()
  linesUpdated = pyqtSignal(list)

  # https://github.com/LibreOffice/core/blob/master/extras/source/palettes/chart-palettes.soc
  colors = [
    '#004586', '#ff420e', '#ffd320', '#579d1c', '#7e0021', '#83caff',
    '#314004', '#aecf00', '#4b1f6f', '#ff950e', '#c5000b', '#0084d1'
  ]

  def __init__(self):
    super().__init__()
    self.lines = []

  def clear(self):
    self.lines = []
    self.cleared.emit()

  def getLines(self):
    return self.lines

  def setLines(self, lines):
    self.lines = lines
    self.linesUpdated.emit(lines)

  def getColor(self, i):
    return self.colors[i % len(self.colors)]

  def createLineGraphItem(self, line, i):
    return pg.PlotCurveItem(
      x=line.x, y=line.y,
      pen=pg.mkPen(color=self.getColor(i), width=2),
      antialias=True,
      name=line.name)

  def getGraphItems(self):
    items = []
    for i, line in enumerate(self.getLines()):
      item = self.createLineGraphItem(line, i)
      items.append(item)
    return items

  def getXrange(self):
    if len(self.lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getXrange() for l in self.lines])
    return min(l1), max(l2)

  def getYrange(self):
    if len(self.lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getYrange() for l in self.lines])
    return min(l1), max(l2)


class NopTool(ToolBase):
  name = 'Nop'


class IADTool(ToolBase):
  name = 'iad'
  label = 'IAD'
  xoffUpdated = pyqtSignal(name='xoffUpdated')
  iadYUpdated = pyqtSignal(name='iadYUpdated')
  peaksUpdated = pyqtSignal(name='peaksUpdated')

  def __init__(self):
    super().__init__()
    self.mode = 'orig'
    self.base = -1
    self.interp = None
    self.interpEnabled = True
    self.threshold = 1e-10
    self.lines = None

  def calcXoff(self, line, wc):
    line_ = self.interp.do(line)
    line = line_
    xoff = 0
    cnt = 0
    while True:
      wc2 = line.weightCenter()
      dx = wc - wc2
      cnt += 1
      if abs(dx) < self.threshold or cnt > 100:
        return xoff, wc2
      xoff += dx
      line = line_.xoff(xoff)

  def doInterpIfEnabled(self, lines):
    if self.interpEnabled:
      return [self.interp.do(l) for l in lines]
    return lines

  def updatePeaks(self, lines):
    self.peaks = [l.peak() for l in lines]
    self.peaksUpdated.emit()
    return lines

  def getLines(self):
    if not self.lines:
      return []

    if self.mode == 'orig':
      return self.updatePeaks(self.doInterpIfEnabled(self.lines))

    base = self.lines[self.base]
    wc = self.interp.do(base).weightCenter()

    self.wc = []
    self.xoff = []
    for i, l in enumerate(self.lines):
      if l == base:
        self.wc.append(wc)
        self.xoff.append(0)
      else:
        xoff, wc = self.calcXoff(l, wc)
        self.wc.append(wc)
        self.xoff.append(xoff)
    self.xoffUpdated.emit()

    if self.mode == 'xoff':
      return self.updatePeaks(self.doInterpIfEnabled(
        [l.xoff(xoff) for l, xoff in zip(self.lines, self.xoff)]))

    diff = []
    for l, xoff in zip(self.lines, self.xoff):
      x1 = l.x + xoff
      x2 = base.x
      X1 = max([min(x1), min(x2)])
      X2 = min([max(x1), max(x2)])
      l1 = self.interp.do(l.xoff(xoff), (X1, X2))
      l2 = self.interp.do(base,         (X1, X2))
      diff.append(l1 - l2)

    if self.mode == 'diff':
      return diff

    if self.mode == 'iad':
      x = self.iadX
      y = [sum(np.abs(d.y))*(d.x[1]-d.x[0]) for d in diff]
      self.iadY = y
      self.iadYUpdated.emit()
      return [Line(x, y, 'IAD')]

    raise RuntimeError()


class FitTool(ToolBase):
  name = 'Fit'

  def __init__(self):
    super().__init__()
    self.functions = []

  def createLineGraphItem(self, line, i):
    return pg.ScatterPlotItem(
      x=line.x, y=line.y,
      pen=pg.mkPen(None),
      brush=pg.mkBrush(self.getColor(i)),
      size=6,
      antialias=True,
      name=line.name)

  def getGraphItems(self):
    items = [] + super().getGraphItems()
    x1, x2 = self.getXrange()
    x = np.linspace(x1, x2, 500)
    for i, f in enumerate(self.functions):
      items += f.getGraphItems(x, pen=pg.mkPen(color=self.getColor(i), width=2))
    return items
