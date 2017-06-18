import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QSpinBox

from log import log


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
    return sum(self.x*self.y)/sum(self.y)

  def normalize(self):
    return self.__class__(self.x, self.y/sum(self.y), self.name)

  def xoff(self, off):
    return self.__class__(self.x + off, self.y, self.name)

  def __sub__(self, other):
    return self.__class__(self.x, self.y - other.y, self.name)


class InterpBase:
  class ParamBase:
    def __init__(self, name, default):
      self.name = name
      self.default = default

    def value(self):
      if hasattr(self, 'value_'):
        return self.value_
      return self.default

    def setValue(self, value):
      self.value_ = value

  class ParamInt(ParamBase):
    def __init__(self, name, min_, max_, default):
      super().__init__(name, default)
      self.min = min_
      self.max = max_

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

  def do(self, line):
    raise NotImplementedError()

  def addParam(self, param):
    self.params.append(param)
    self.paramsMap[param.name] = param

  def __getattr__(self, name):
    if name in self.paramsMap:
      return self.paramsMap[name]
    raise AttributeError()

  def createOptionsWidget(self):
    if not self.params:
      return None
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    for r, p in enumerate(self.params):
      grid.addWidget(QLabel(p.name), r, 0)
      grid.addWidget(p.createWidget(), r, 1)

    widget = QWidget()
    widget.setLayout(grid)
    return widget


class NopInterp(InterpBase):
  name = 'None'

  def do(self, line):
    return line


class CubicSpline(InterpBase):
  name = 'Cubic spline'

  def __init__(self):
    super().__init__()
    self.addParam(self.ParamInt('N', 1, 999, 9))

  def do(self, line):
    x, y = line.x, line.y
    from scipy import interpolate
    tck = interpolate.splrep(x, y, s=0)
    x2 = np.arange(min(x), max(x), (max(x)-min(x))/(len(x) * (self.N.value() + 1)))
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
  name = 'IAD'
  xoffUpdated = pyqtSignal()

  def __init__(self):
    super().__init__()
    self.mode = 'orig'
    self.base = 0
    self.interp = None
    self.threshold = 1e-10
    self.lines = None

  def calcXoff(self, line, wc):
    line_ = self.interp.do(line).normalize()
    line = line_
    xoff = 0
    cnt = 0
    while True:
      wc2 = line.weightCenter()
      dx = wc - wc2
      cnt += 1
      if abs(dx) < self.threshold or cnt > 100:
        return xoff, wc2, line
      xoff += dx
      line = line_.xoff(xoff).normalize()

  def getLines(self):
    if not self.lines:
      return []

    if self.mode == 'orig':
      return self.lines

    base = self.interp.do(self.lines[self.base]).normalize()
    wc = base.weightCenter()

    lines = []
    self.wc = []
    self.xoff = []
    for i, l in enumerate(self.lines):
      if i == self.base:
        lines.append(base)
        self.wc.append(wc)
        self.xoff.append(0)
      else:
        xoff, wc, line = self.calcXoff(l, wc)
        lines.append(line)
        self.wc.append(wc)
        self.xoff.append(xoff)
    self.xoffUpdated.emit()

    if self.mode == 'xoff':
      return lines

    if self.mode == 'diff':
      return [l - lines[self.base] for l in lines]

    if self.mode == 'iad':
      b = lines[self.base]
      x = self.iadX
      y = [sum(np.abs(l.y - b.y)) for l in lines]
      return [Line(x, y, 'IAD')]

    raise RuntimeError()
