import logging
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

from toolbase import ToolBase
from settingitems import SettingItemFloat
from line import Line



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
    self.smooth = None
    self.interp = None
    self.lines = None

    self.addSettingItem(SettingItemFloat(
      'interpdx', 'dx', '0.01', min_=0))
    self.addSettingItem(SettingItemFloat(
      'threshold', 'Threshold', '1e-10', min_=0))

  def calcXoff(self, lines, linesF, baseF):
    if len(lines) == 1:
      return [0], min(lines[0].x), max(lines[0].x)

    def weightCenter(x, y):
      return np.sum(x*y)/np.sum(y)

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
          x = np.arange(X1, X2, self.interpdx.value())
          wc1 = weightCenter(x, baseF(x))
          wc2 = weightCenter(x, lineF(x-xoff[i]))

          dx = wc1 - wc2
          cnt += 1
          if abs(dx) < self.threshold.value() or cnt > 10:
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

  def interpX(self, line):
    X1, X2 = min(line.x), max(line.x)
    return np.arange(X1, X2, self.interpdx.value())

  def getLines(self, mode=None):
    if not self.lines:
      return []

    if mode is None:
      mode = self.mode

    if mode == 'orig':
      return self.updatePeaks(self.lines)

    lines = [Line(l.name, l.x, self.smooth.smooth(l.x, l.y), None) for l in self.lines]
    linesF = [self.interp.func(l.x, l.y) for l in lines]
    linesX = [self.interpX(l) for l in lines]
    if self.bgsub:
      logging.info('Subtract bg: %s' % self.bgsub.label)
      linesF_ = []
      for l, f, x in zip(lines, linesF, linesX):
        fsub = self.bgsub.func(l, f, x)
        linesF_.append((lambda f, fsub: (lambda x: f(x)-fsub(x)))(f, fsub))
      linesF = linesF_


    if mode == 'norm':
      return self.updatePeaks([Line(l.name, x, f(x), None).normalize()
                               for l, f, x in zip(lines, linesF, linesX)])


    try:
      baseF = linesF[self.base]
    except IndexError:
      baseF = linesF[-1]
      self.base = -1


    self.xoff, X1, X2 = self.calcXoff(lines, linesF, baseF)
    x = np.arange(X1, X2, self.interpdx.value())
    lines_off = []
    for l, f, xoff in zip(lines, linesF, self.xoff):
      y = f(x-xoff)
      lines_off.append(Line(l.name, x, y, None).normalize())

    self.wc = [l.weightCenter() for l in lines_off]
    self.xoffUpdated.emit()


    diff = [l - lines_off[self.base] for l in lines_off]

    x = self.iadX
    y = [np.sum(np.abs(d.y)) for d in diff]


    # 誤差計算
    # スプライン補完で点を増やしてnormalizeしてから誤差を出すと
    # 二乗和なので誤差が小さくなってしまう(測定点の水増し)
    y_ = []
    lnorm = [l.normalize() for l in self.lines]
    for l in lnorm:
      y_.append(np.sqrt(np.sum(l.y_**2 + lnorm[self.base].y_**2)))


    self.iadY = y
    self.iadY_ = y_
    self.iadYUpdated.emit()
    x, y, y_ = Line.cleanUp(x, y, y_)
    IAD = Line('IAD', x, y, y_)
    IAD.plotErrors = True


    if mode == 'xoff':
      return self.updatePeaks(lines_off)

    if mode == 'diff':
      return diff

    if mode == 'iad':
      return [IAD]

    raise RuntimeError()

  def saveState(self):
    state = super().saveState()
    state.update({
      'plot_mode': self.mode,
      'base': self.base
    })
    return state

  def restoreState(self, state):
    super().restoreState(state)
    if 'plot_mode' in state: self.mode = state['plot_mode']
    if 'base' in state: self.base = state['base']
