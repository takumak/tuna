from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget, QComboBox, QLabel

from toolbase import ToolBase
from settingobj import SettingObj
from commonwidgets import *



__all__ = ['ToolWidgetBase', 'MethodSelector']



class ToolWidgetBase(QWidget, SettingObj):
  plotRequested = pyqtSignal(ToolBase, bool, name='plotRequested')

  def __init__(self):
    super().__init__()
    self.tool = self.toolClass()
    self.tool.cleared.connect(self.clear)
    self.tool.added.connect(self.add)

  def clear(self):
    raise NotImplementedError()

  def add(self, line):
    raise NotImplementedError()

  def saveState(self):
    state = super().saveState()
    state['tool'] = self.tool.saveState()
    return state

  def restoreState(self, state):
    super().restoreState(state)
    if 'tool' in state: self.tool.restoreState(state['tool'])



class MethodSelector(QWidget):
  selectionChanged = pyqtSignal()

  def __init__(self, label, items):
    super().__init__()
    self.label = label
    self.items = items

    self.combo = QComboBox()

    vbox = VBoxLayout()
    self.setLayout(vbox)

    hbox = HBoxLayout()
    hbox.addWidget(QLabel(label))
    hbox.addWidget(self.combo)
    vbox.addLayout(hbox)
    self.comboHBox = hbox

    optl = VBoxLayout()
    optl.setContentsMargins(40, 0, 0, 0)
    vbox.addLayout(optl)
    self.setup(optl, items)


  def setup(self, optlayout, items):
    def selected(idx):
      for i in range(self.combo.count()):
        item, opt = self.combo.itemData(i)
        if opt is None: continue

        if i == idx:
          opt.show()
        else:
          opt.hide()
      self.selectionChanged.emit()

    for item in items:
      opt = item.getSettingWidget()
      self.combo.addItem(item.label, [item, opt])
      if opt:
        optlayout.addWidget(opt)
    self.combo.setCurrentIndex(0)
    selected(self.combo.currentIndex())
    self.combo.currentIndexChanged.connect(selected)

  def currentItem(self):
    return self.combo.currentData()[0]

  def setCurrentItem(self, item):
    if isinstance(item, str):
      name = item
    else:
      name = item.name

    for i in range(self.combo.count()):
      item, opt = self.combo.itemData(i)
      if item.name == name:
        self.combo.setCurrentIndex(i)
        break
