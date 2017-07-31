from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QWidget

from toolbase import ToolBase
from settingobj import SettingObj



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
