import numpy as np
from PyQt5.QtGui import QValidator

from methodbase import MethodBase, ParamStr, ParamInt


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
    self.addParam(ParamInt(
      'windowLength', 'Window length', 3,
      validator=self.validateWindowLength))
    self.addParam(ParamInt(
      'polyorder', 'Poly order', 2,
      validator=self.validatePolyorder))

    self.windowLength.valueChanged.connect(
      self.polyorder.checkInputValue)

  def validateWindowLength(self, val):
    if val >= 1 and val%2 == 1:
      return QValidator.Acceptable, 'OK'
    return QValidator.Invalid, 'Must be positive odd number'

  def validatePolyorder(self, val):
    if val < 1:
      return QValidator.Invalid, 'Must be positive integer'
    if self.windowLength.isValid() and val >= self.windowLength.intValue():
      return QValidator.Invalid, 'Must be less than Window length'
    return QValidator.Acceptable, 'OK'

  def smooth(self, x, y):
    from scipy.signal import savgol_filter
    return savgol_filter(y, self.windowLength.intValue(), self.polyorder.intValue())
