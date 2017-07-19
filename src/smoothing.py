import numpy as np

from methodbase import MethodBase, ParamInt


class SmoothBase(MethodBase):
  def smooth(self, x, y):
    raise NotImplementedError()



class SmoothNop(SmoothBase):
  name  = 'nop'
  label = 'Do nothing'

  def smooth(self, x, y):
    return y



class SmoothSavGol(SmoothBase):
  name  = 'savgol'
  label = 'Savitzky-Golay'

  def __init__(self):
    super().__init__()
    self.windowLength = ParamInt('Window length', 'window_length', 3,
                                 1, None, lambda v: v%2==1)
    self.polyorder = ParamInt('Poly order', 'polyorder', 2,
                              1, None, lambda v: v<self.windowLength.value())

    self.addParam(self.windowLength)
    self.addParam(self.polyorder)

  def smooth(self, x, y):
    from scipy.signal import savgol_filter
    return savgol_filter(y, self.windowLength.value(), self.polyorder.value())
