import logging
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QSpinBox, QLineEdit


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

  def weightCenter(self):
    if len(self.y) == 0:
      return 0
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
    if len(self.x) == 0:
      return 0, 0
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
      if self.widget and not self.widget.hasFocus():
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
      self.widget.setValue(value)

    def createWidget(self):
      spin = QSpinBox()
      spin.setMinimum(self.min)
      spin.setMaximum(self.max)
      spin.setValue(self.value())
      spin.valueChanged.connect(self.setValue)
      return spin


  class ParamDouble(ParamBase):
    def __init__(self, name, default):
      super().__init__(name, default)

    def updateWidgetValue(self, widget, value):
      self.widget.setText(str(value))

    def createWidget(self):
      edit = QLineEdit()
      edit.setValidator(QDoubleValidator())
      edit.textChanged.connect(lambda t: self.setValue(float(t)))
      return edit


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
      n = p['name']
      if n in self.paramsMap:
        self.paramsMap[n].setValue(p['value'])



class CubicSpline(InterpBase):
  name  = 'cubic_spline'
  label = 'Cubic spline'

  def __init__(self):
    super().__init__()
    self.addParam(self.ParamDouble('dx', 0.01))

  def do(self, line, xrange = None):
    if len(line.x) == 0:
      return Line([], [], line.name)

    if xrange is not None:
      X1, X2 = xrange
    else:
      X1, X2 = min(line.x), max(line.x)

    from scipy import interpolate
    tck = interpolate.splrep(line.x, line.y, s=0)
    x2 = np.arange(X1, X2, self.dx.value())
    y2 = interpolate.splev(x2, tck, der=0)
    return Line(x2, y2, line.name)



class ToolBase(QObject):
  cleared = pyqtSignal()
  added = pyqtSignal(Line)

  def __init__(self):
    super().__init__()
    self.lines = []

  def clear(self):
    self.lines = []
    self.cleared.emit()

  def add(self, x, y, name):
    l = Line(x, y, name)
    self.lines.append(l)
    self.added.emit(l)

  def getLines(self):
    raise NotImplementedError()


class NopTool(ToolBase):
  name = 'Nop'

  def getLines(self):
    return self.lines


class FitTool(NopTool):
  name = 'Fit'


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

    try:
      base = self.lines[self.base]
    except IndexError:
      self.base = -1
      base = self.lines[-1]
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
