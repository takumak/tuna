import numpy as np

from methodbase import MethodBase, ParamInt



class BGSubBase(MethodBase):
  def calcY(self, line, x):
    raise NotImplementedError()



class BGSubNop(BGSubBase):
  name  = 'nop'
  label = 'Do nothing'

  def calcY(self, line, x):
    return np.full(len(x), 0)



class BGSubMinimum(BGSubBase):
  name  = 'minimum'
  label = 'Minimum y'

  def calcY(self, line, x):
    return np.full(len(x), min(line.y))



class BGSubEdgeBase(BGSubBase):
  def __init__(self):
    super().__init__()
    self.addParam(ParamInt('N', 'Avg by N pts', 1, 99999, 10))

  def calcY(self, line, x):
    y = line.y[self.slice()]
    return np.full(len(x), sum(y)/len(y))



class BGSubLeftEdge(BGSubEdgeBase):
  name  = 'leftedge'
  label = 'Left edge'

  def slice(self):
    return slice(0, self.N.value())



class BGSubRightEdge(BGSubEdgeBase):
  name  = 'rightedge'
  label = 'Right edge'

  def slice(self):
    return slice(-self.N.value(), None)
