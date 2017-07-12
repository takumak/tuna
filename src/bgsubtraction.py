import numpy as np

from methodbase import MethodBase, ParamInt, ParamDouble



class BGSubBase(MethodBase):
  def func(self, line, lineF, x):
    raise NotImplementedError()



class BGSubNop(BGSubBase):
  name  = 'nop'
  label = 'Do nothing'

  def func(self, line, lineF, x):
    return lambda x: x*0



class BGSubMinimum(BGSubBase):
  name  = 'minimum'
  label = 'Minimum y'

  def func(self, line, lineF, x):
    v = min(line.y)
    return lambda x: x/x*v



class BGSubEdgeBase(BGSubBase):
  def __init__(self):
    super().__init__()
    self.addParam(ParamDouble('deltaX', '\u0394x', 1))

  def func(self, line, lineF, x):
    x1, x2 = self.range(x)
    y = lineF(np.array([xi for xi in x if x1 <= xi <= x2]))
    v = np.average(y)
    return lambda x: x/x*v



class BGSubLeftEdge(BGSubEdgeBase):
  name  = 'leftedge'
  label = 'Left edge'

  def range(self, x):
    x1 = min(x)
    return x1, x1 + self.deltaX.value()



class BGSubRightEdge(BGSubEdgeBase):
  name  = 'rightedge'
  label = 'Right edge'

  def range(self, x):
    x2 = max(x)
    return x2 - self.deltaX.value(), x2
