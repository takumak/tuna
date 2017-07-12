from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QGridLayout, QWidget, \
  QLabel, QSpinBox, QLineEdit

class ParamBase:
  def __init__(self, name, label, default):
    self.name = name
    self.label = label
    self.default = default
    self.widget = None

  def value(self):
    if hasattr(self, 'value_'):
      return self.value_
    return self.default

  def setValue(self, value):
    if value == self.value():
      return
    self.value_ = value
    if self.widget and not self.widget.hasFocus():
      self.updateWidgetValue(self.widget, value)

  def getWidget(self):
    if self.widget is None:
      self.widget = self.createWidget()
    return self.widget



class ParamInt(ParamBase):
  def __init__(self, name, label, min_, max_, default):
    super().__init__(name, label, default)
    self.min = min_
    self.max = max_

  def updateWidgetValue(self, widget, value):
    self.widget.setValue(value)

  def createWidget(self):
    spin = QSpinBox()
    spin.setMinimum(self.min)
    spin.setMaximum(self.max)
    spin.setValue(self.value())
    spin.valueChanged.connect(self.setValue)
    return spin



class ParamDouble(ParamBase):
  def updateWidgetValue(self, widget, value):
    self.widget.setText(str(value))

  def createWidget(self):
    edit = QLineEdit()
    edit.setValidator(QDoubleValidator())
    edit.textChanged.connect(lambda t: self.setValue(float(t)))
    return edit



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
    return [{'name': p.name, 'value': p.value()} for p in self.params]

  def restoreState(self, state):
    for p in state:
      n = p['name']
      if n in self.paramsMap:
        self.paramsMap[n].setValue(p['value'])
