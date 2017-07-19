import logging
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QValidator
from PyQt5.QtWidgets import QGridLayout, QWidget, \
  QLabel, QSpinBox, QPushButton

from commonwidgets import LineEditWithBaloon



class ValidateError(Exception):
  def __init__(self, message):
    super().__init__()
    self.message = message



class ParamBase(QObject):
  valueChanged = pyqtSignal()
  dirtyStateChanged = pyqtSignal(bool)

  def __init__(self, name, label, default, validator=None):
    super().__init__()

    self.name = name
    self.label = label
    self.default = str(default)
    self.validator = validator
    self.edit = None
    self.baloon = None
    self.dirty = False

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
      self.checkInputValue()

  def saveValue(self):
    self.setStrValue(self.edit.text(), False)
    self.dirty = False
    self.dirtyStateChanged.emit(self.dirty)

  def checkInputValue(self):
    state, message = self.validate(self.edit.text())
    if state == QValidator.Acceptable:
      self.edit.setBaloonMessage(None)
    else:
      logging.warning(message)
      self.edit.setBaloonMessage(message)
    self.dirty = True
    self.dirtyStateChanged.emit(self.dirty)

  def validate(self, value):
    if self.validator:
      return self.validator(value)
    return QValidator.Acceptable, 'OK'

  def isValid(self):
    return self.validate(self.strValue())[0] == QValidator.Acceptable

  def textEdited(self, text):
    self.setStrValue(text)
    self.checkInputValue()

  def createWidget(self):
    self.edit = LineEditWithBaloon()
    self.edit.setText(self.strValue())
    self.edit.textEdited.connect(self.textEdited)
    self.edit.editingFinished.connect(self.saveValue)

  def getWidget(self):
    if self.edit is None:
      self.createWidget()
    return self.edit



class ParamStr(ParamBase): pass



class ParamInt(ParamBase):
  def __init__(self, name, label, default,
               min_=None, max_=None, validator=None):
    super().__init__(name, label, default, validator)
    self.min_ = min_
    self.max_ = max_

  def intValue(self):
    return int(self.strValue())

  def validate(self, text):
    try:
      val = int(text)
    except:
      return QValidator.Invalid, 'Must be integer'
    if self.min_ is not None and val < self.min_:
      return QValidator.Invalid, 'Value must be larger than or equal to %d' % self.min_
    if self.max_ is not None and val > self.max_:
      return QValidator.Invalid, 'Value must be less than or equal to %d' % self.max_

    return super().validate(val)



class ParamFloat(ParamStr):
  def floatValue(self):
    return float(self.strValue())

  def validate(self, text):
    try:
      val = float(text)
    except:
      return QValidator.Invalid, 'Must be float number'

    return super().validate(val)



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
        self.paramsMap[n].setStrValue(p['value'])
