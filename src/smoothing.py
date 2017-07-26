import numpy as np
from PyQt5.QtGui import QValidator

from settingobj import SettingObj
from settingitems import SettingItemStr, SettingItemInt


class SmoothBase(SettingObj):
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
    self.addSettingItem(SettingItemInt(
      'windowLength', 'Window length', 3,
      validator=self.validateWindowLength))
    self.addSettingItem(SettingItemInt(
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
    if self.windowLength.isValid() and val >= self.windowLength.value():
      return QValidator.Invalid, 'Must be less than Window length'
    return QValidator.Acceptable, 'OK'

  def smooth(self, x, y):
    from scipy.signal import savgol_filter
    return savgol_filter(y, self.windowLength.value(), self.polyorder.value())
