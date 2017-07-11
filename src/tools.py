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
    if len(self.x) == 0:
      return 0
    return sum(self.x*self.y)/sum(self.y)

  def normalize(self):
    return self.__class__(self.x, self.y/sum(self.y), self.name)

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

  def do(self, line, dx, xrange = None):
    if len(line.x) == 0:
      return Line([], [], line.name)

    if xrange is not None:
      X1, X2 = xrange
    else:
      X1, X2 = min(line.x), max(line.x)

    x = np.arange(X1, X2, dx)
    y = self.calcY(line, x)
    return Line(x, y, line.name)

  def calcY(self, line, x):
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



class InterpScipy(InterpBase):
  def calcY(self, line, x):
    import scipy.interpolate as interp
    return getattr(interp, self.clsname)(line.x, line.y)(x)

class CubicSpline(InterpScipy):
  name    = 'cubic_spline'
  label   = 'Cubic spline'
  clsname = 'CubicSpline'

class Barycentric(InterpScipy):
  name    = 'barycentric'
  label   = 'Barycentric'
  clsname = 'BarycentricInterpolator'

class Krogh(InterpScipy):
  name    = 'krogh'
  label   = 'Krogh'
  clsname = 'KroghInterpolator'

class Pchip(InterpScipy):
  name    = 'pchip'
  label   = 'Pchip'
  clsname = 'PchipInterpolator'

class Akima(InterpScipy):
  name    = 'akima'
  label   = 'Akima'
  clsname = 'Akima1DInterpolator'



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
    self.interpdx = 0.01
    self.threshold = 1e-10
    self.lines = None

  def doInterp(self, line, *args):
    return self.interp.do(line, self.interpdx, *args)

  def calcXoff(self, lines, base):
    xoff = [0] * len(lines)

    while True:
      X1_, X2_ = self.linesInnerRange(lines, xoff)

      for i, line in enumerate(lines):
        if line == base:
          continue

        cnt = 0
        while True:
          X1, X2 = self.linesInnerRange(lines, xoff)
          wc1 = self.doInterp(base,               (X1, X2)).weightCenter()
          wc2 = self.doInterp(line.xoff(xoff[i]), (X1, X2)).weightCenter()

          dx = wc1 - wc2
          cnt += 1
          if abs(dx) < self.threshold or cnt > 100:
            break

          xoff[i] += dx

      if X1 == X1_ and X2 == X2_:
        break

    return xoff, X1, X2

  def doInterpIfEnabled(self, lines):
    if self.interpEnabled:
      return [self.doInterp(l) for l in lines]
    return lines

  def updatePeaks(self, lines):
    self.peaks = [l.peak() for l in lines]
    self.peaksUpdated.emit()
    return lines

  def linesInnerRange(self, lines, xoff):
    X1 = max([min(l.x+o) for l, o in zip(lines, xoff)])
    X2 = min([max(l.x+o) for l, o in zip(lines, xoff)])
    return X1, X2

  def getLines(self, mode=None):
    if not self.lines:
      return []

    if mode is None:
      mode = self.mode

    try:
      base = self.lines[self.base]
    except IndexError:
      self.base = -1
      base = self.lines[-1]
    # wc = self.doInterp(base).weightCenter()

    self.xoff, X1, X2 = self.calcXoff(self.lines, base)
    self.wc = [self.doInterp(line.xoff(xoff), (X1, X2)).weightCenter()
               for line, xoff in zip(self.lines, self.xoff)]
    self.xoffUpdated.emit()

    lines_off = [self.doInterp(l.xoff(xoff), (X1, X2)).normalize()
                 for l, xoff in zip(self.lines, self.xoff)]

    diff = []
    base = lines_off[self.base]
    for l in lines_off:
      if len(l.x) == 0 or len(base.x) == 0:
        diff.append(Line([], [], l.name))
        continue
      diff.append(l - base)

    x = self.iadX
    y = [sum(np.abs(d.y)) for d in diff]
    self.iadY = y
    self.iadYUpdated.emit()
    IAD = Line(x, y, 'IAD')

    if mode == 'orig':
      return self.updatePeaks(self.doInterpIfEnabled(self.lines))

    if mode == 'xoff':
      return self.updatePeaks(lines_off)

    if mode == 'diff':
      return diff

    if mode == 'iad':
      return [IAD]

    raise RuntimeError()
