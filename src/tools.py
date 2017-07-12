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
    x, y = Line.cleanUp(x, y)
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
    self.interpdx = 0.1
    self.threshold = 1e-10
    self.lines = None

  def calcXoff(self, lines, linesF, baseF):
    # import cProfile, pstats, io
    # pr = cProfile.Profile()
    # pr.enable()

    def weightCenter(x, y):
      return np.sum(x*y)/np.sum(y)

    try:
      xoff = [0] * len(lines)

      for _p in range(len(lines)*10):
        X1_, X2_ = self.linesInnerRange(lines, xoff)
        if X1_ == X2_: break

        for i, (line, lineF) in enumerate(zip(lines, linesF)):
          if lineF == baseF:
            continue

          cnt = 0
          while True:
            X1, X2 = self.linesInnerRange(lines, xoff)
            x = np.arange(X1, X2, self.interpdx)
            wc1 = weightCenter(x, baseF(x))
            wc2 = weightCenter(x, lineF(x-xoff[i]))

            dx = wc1 - wc2
            cnt += 1
            if abs(dx) < self.threshold or cnt > 10:
              break

            xoff[i] += dx

        if X1 == X1_ and X2 == X2_:
          break

      else:
        raise RuntimeError('Maximum loop count exceeded')

    finally:
      # pr.disable()
      # s = io.StringIO()
      # sortby = 'cumulative'
      # ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
      # ps.print_stats()
      # logging.info('\n'+s.getvalue())
      pass

    return xoff, X1, X2

  def updatePeaks(self, lines):
    self.peaks = [l.peak() for l in lines]
    self.peaksUpdated.emit()
    return lines

  def linesInnerRange(self, lines, xoff):
    X1 = max([min(l.x+o) for l, o in zip(lines, xoff) if len(l.x) >= 1])
    X2 = min([max(l.x+o) for l, o in zip(lines, xoff) if len(l.x) >= 1])
    return X1, X2

  def interpX(self, line):
    X1, X2 = min(line.x), max(line.x)
    return np.arange(X1, X2, self.interpdx)

  def getLines(self, mode=None):
    if not self.lines:
      return []

    if mode is None:
      mode = self.mode

    if mode == 'orig':
      return self.updatePeaks(self.lines)


    linesF = [self.interp.func(l) for l in self.lines]
    linesX = [self.interpX(l) for l in self.lines]
    if self.bgsub:
      logging.info('Subtract bg: %s' % self.bgsub.label)
      linesF_ = []
      for l, f, x in zip(self.lines, linesF, linesX):
        fsub = self.bgsub.func(l, f, x)
        linesF_.append((lambda f, fsub: (lambda x: f(x)-fsub(x)))(f, fsub))
      linesF = linesF_


    baseidx = self.base
    try:
      baseF = linesF[baseidx]
    except IndexError:
      baseF = linesF[-1]
      baseidx = -1


    self.xoff, X1, X2 = self.calcXoff(self.lines, linesF, baseF)
    x = np.arange(X1, X2, self.interpdx)
    lines_off = [Line(x, f(x-xoff), l.name).normalize()
                 for l, f, xoff in zip(self.lines, linesF, self.xoff)]

    self.wc = [l.weightCenter() for l in lines_off]
    self.xoffUpdated.emit()


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
    x, y = Line.cleanUp(x, y)
    IAD = Line(x, y, 'IAD')


    if mode == 'xoff':
      return self.updatePeaks(lines_off)

    if mode == 'diff':
      return diff

    if mode == 'iad':
      return [IAD]

    raise RuntimeError()
