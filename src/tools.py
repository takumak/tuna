import logging
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal


from line import Line


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
    self.bgsub = None
    self.interp = None
    self.interpdx = 0.01
    self.threshold = 1e-10
    self.lines = None

  def doInterp(self, line, *args):
    return self.interp.do(line, self.interpdx, *args)

  def calcXoff(self, lines, base):
    xoff = [0] * len(lines)

    for _p in range(100):
      X1_, X2_ = self.linesInnerRange(lines, xoff)
      if X1_ == X2_: break

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
          if abs(dx) < self.threshold or cnt > 10:
            break

          xoff[i] += dx

      if X1 == X1_ and X2 == X2_:
        break

    else:
      raise RuntimeError('Maximum loop count exceeded')

    return xoff, X1, X2

  def updatePeaks(self, lines):
    self.peaks = [l.peak() for l in lines]
    self.peaksUpdated.emit()
    return lines

  def linesInnerRange(self, lines, xoff):
    X1 = max([min(l.x+o) for l, o in zip(lines, xoff) if len(l.x) >= 1])
    X2 = min([max(l.x+o) for l, o in zip(lines, xoff) if len(l.x) >= 1])
    return X1, X2

  def getLines(self, mode=None):
    if not self.lines:
      return []

    if mode is None:
      mode = self.mode

    baseidx = self.base
    try:
      base = self.lines[baseidx]
    except IndexError:
      base = self.lines[-1]
      baseidx = -1


    lines = self.lines
    if self.bgsub:
      logging.info('Subtract bg: %s' % self.bgsub.label)
      lines = [l-Line(l.x, self.bgsub.calcY(l, l.x), 'bg') for l in lines]


    self.xoff, X1, X2 = self.calcXoff(lines, base)
    self.wc = [self.doInterp(line.xoff(xoff), (X1, X2)).weightCenter()
               for line, xoff in zip(lines, self.xoff)]
    self.xoffUpdated.emit()

    lines_off = [self.doInterp(l.xoff(xoff), (X1, X2)).normalize()
                 for l, xoff in zip(lines, self.xoff)]


    diff = []
    base = lines_off[baseidx]
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
      return self.updatePeaks(lines)

    if mode == 'xoff':
      return self.updatePeaks(lines_off)

    if mode == 'diff':
      return diff

    if mode == 'iad':
      return [IAD]

    raise RuntimeError()
