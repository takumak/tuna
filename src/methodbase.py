import logging
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QGridLayout, QWidget, \
  QLabel, QSpinBox, QPushButton

from commonwidgets import ErrorCheckEdit



class ValidateError(Exception):
  def __init__(self, message):
    super().__init__()
    self.message = message



class ParamBase(QObject):
  valueChanged = pyqtSignal()

  def __init__(self, name, label, default, validator=None):
    super().__init__()

    self.name = name
    self.label = label
    self.default = default
    self.validator = validator
    self.edit = None

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



class ParamStr(ParamBase): pass



class ParamNumber(ParamBase):
  def __init__(self, name, label, default, type_,
               min_=None, max_=None, validator=None,
               emptyIsNone=False):
    super().__init__(name, label, str(default), validator)
    self.type_ = type_
    self.min_ = min_
    self.max_ = max_
    self.emptyIsNone = emptyIsNone

  def numValue(self):
    v = self.strValue()
    if v == '' and self.emptyIsNone:
      return None
    return self.type_(v)

  def validate(self, text):
    if text == '' and self.emptyIsNone:
      QValidator.Acceptable, 'OK'

    try:
      val = self.type_(text)
    except:
      return QValidator.Invalid, 'Must be %s' % self.type_.__name__
    if self.min_ is not None and val < self.min_:
      return QValidator.Invalid, 'Value must be larger than or equal to %d' % self.min_
    if self.max_ is not None and val > self.max_:
      return QValidator.Invalid, 'Value must be less than or equal to %d' % self.max_

    return super().validate(val)



class ParamInt(ParamNumber):
  def __init__(self, name, label, default,
               min_=None, max_=None, validator=None,
               emptyIsNone=False):
    super().__init__(name, label, default, int,
                     min_=min_, max_=max_, validator=validator,
                     emptyIsNone=emptyIsNone)

  def intValue(self):
    return self.numValue()



class ParamFloat(ParamNumber):
  def __init__(self, name, label, default,
               min_=None, max_=None, validator=None,
               emptyIsNone=False):
    super().__init__(name, label, default, float,
                     min_=min_, max_=max_, validator=validator,
                     emptyIsNone=emptyIsNone)

  def floatValue(self):
    return self.numValue()



class MethodBase:
  def __init__(self):
    self.params = []
    self.paramsMap = {}
    self.optionsWidget = None

  def addParam(self, param):
    self.params.append(param)
    self.paramsMap[param.name] = param

  def __getattr__(self, name):
    if name in self.paramsMap:
      return self.paramsMap[name]
    raise AttributeError()

  def getOptionsWidget(self):
    if self.optionsWidget is None:
      self.optionsWidget = self.createOptionsWidget()
    return self.optionsWidget

  def createOptionsWidget(self):
    if not self.params:
      return None
    grid = QGridLayout()
    grid.setContentsMargins(0, 0, 0, 0)
    for r, p in enumerate(self.params):
      grid.addWidget(QLabel(p.name), r, 0)
      grid.addWidget(p.getWidget(), r, 1)

    widget = QWidget()
    widget.setLayout(grid)
    return widget

  def saveState(self):
    return [{'name': p.name, 'value': p.strValue()} for p in self.params]

  def restoreState(self, state):
    for p in state:
      n = p['name']
      if n in self.paramsMap:
        self.paramsMap[n].setStrValue(str(p['value']))
