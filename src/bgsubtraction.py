import numpy as np

from settingobj import SettingObj
from settingitems import *



__all__ = ['BGSubNop', 'BGSubMinimum', 'BGSubLeftEdge', 'BGSubRightEdge']



class BGSubBase(SettingObj):
  def func(self, line, lineF, x):
    raise NotImplementedError()



class BGSubNop(BGSubBase):
  name = 'nop'
  label = 'Do nothing'

  def func(self, line, lineF, x):
    return lambda x: x*0



class BGSubMinimum(BGSubBase):
  name = 'minimum'
  label = 'Minimum y'

  def func(self, line, lineF, x):
    v = min(line.y)
    return lambda x: v+x*0



class BGSubEdgeBase(BGSubBase):
  def __init__(self):
    super().__init__()
    self.addSettingItem(SettingItemFloat('deltaX', '\u0394x', 1))

  def func(self, line, lineF, x):
    x1, x2 = self.range(x)
    y = lineF(np.array([xi for xi in x if x1 <= xi <= x2]))
    v = np.average(y)
    return lambda x: v+x*0



class BGSubLeftEdge(BGSubEdgeBase):
  name = 'leftedge'
  label = 'Left edge'

  def range(self, x):
    x1 = min(x)
    return x1, x1 + self.deltaX.value()



class BGSubRightEdge(BGSubEdgeBase):
  name = 'rightedge'
  label = 'Right edge'

  def range(self, x):
    x2 = max(x)
    return x2 - self.deltaX.value(), x2
