import logging
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QValidator

from commonwidgets import *



__all__ = ['SettingItemStr', 'SettingItemInt', 'SettingItemFloat', 'SettingItemRange']



class ValidateError(Exception):
  def __init__(self, message):
    super().__init__()
    self.message = message



class SettingItemBase(QObject):
  valueChanged = pyqtSignal()

  def __init__(self, name, label, default, validator=None):
    super().__init__()

    self.name = name
    self.label = label
    self.default = default
    self.validator = validator
    self.edit = None

  def isSet(self):
    return hasattr(self, 'value_')

  def strValue(self):
    if hasattr(self, 'value_'):
      return self.value_
    return self.default

  def setStrValue(self, value, updateWidget=True):
    if hasattr(self, 'value_') and value == self.value_:
      return
    self.value_ = value
    self.valueChanged.emit()
    if self.edit and updateWidget:
      self.edit.setText(value)

  def saveValue(self):
    self.setStrValue(self.edit.text(), False)

  def validate(self, value):
    if self.validator:
      return self.validator(value)
    return QValidator.Acceptable, 'OK'

  def isValid(self):
    return self.validate(self.strValue())[0] == QValidator.Acceptable

  def checkInputValue(self):
    self.edit.checkValue()

  def createWidget(self):
    self.edit = ErrorCheckEdit(self.validate)
    self.edit.setText(self.strValue())
    self.edit.textEdited.connect(lambda t: self.setStrValue(t, False))

  def getWidget(self):
    if self.edit is None:
      self.createWidget()
    return self.edit



class SettingItemStr(SettingItemBase):
  def value(self):
    return self.strValue()



class SettingItemNumber(SettingItemBase):
  def __init__(self, name, label, default, type_,
               min_=None, max_=None, validator=None,
               emptyIsNone=False):
    super().__init__(name, label, str(default), validator)
    self.type_ = type_
    self.min_ = min_
    self.max_ = max_
    self.emptyIsNone = emptyIsNone

  def value(self):
    v = self.strValue()
    if v == '' and self.emptyIsNone:
      return None
    return self.type_(v)

  def validate(self, text):
    if text == '' and self.emptyIsNone:
      return QValidator.Acceptable, 'OK'

    try:
      val = self.type_(text)
    except:
      return QValidator.Invalid, 'Must be %s' % self.type_.__name__
    if self.min_ is not None and val < self.min_:
      return QValidator.Invalid, 'Value must be larger than or equal to %d' % self.min_
    if self.max_ is not None and val > self.max_:
      return QValidator.Invalid, 'Value must be less than or equal to %d' % self.max_

    return super().validate(val)



class SettingItemInt(SettingItemNumber):
  def __init__(self, name, label, default,
               min_=None, max_=None, validator=None,
               emptyIsNone=False):
    super().__init__(name, label, default, int,
                     min_=min_, max_=max_, validator=validator,
                     emptyIsNone=emptyIsNone)



class SettingItemFloat(SettingItemNumber):
  def __init__(self, name, label, default,
               min_=None, max_=None, validator=None,
               emptyIsNone=False):
    super().__init__(name, label, default, float,
                     min_=min_, max_=max_, validator=validator,
                     emptyIsNone=emptyIsNone)



class SettingItemRange(SettingItemBase):
  def __init__(self, name, label, default, validator=None):
    super().__init__(name, label, default, validator)

  def inRange(self, val):
    v1, v2 = self.value()
    return v1 <= val <= v2

  def value(self):
    return tuple(map(float, self.strValue().split(':', 1)))

  def validate(self, text):
    try:
      v1, v2 = map(float, text.split(':', 1))
    except:
      return QValidator.Invalid, 'Value must be in format of "{number}:{number}"'

    if v1 > v2:
      return QValidator.Invalid, 'The first value must be smaller than the second value'

    return super().validate((v1, v2))
