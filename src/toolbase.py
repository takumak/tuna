from PyQt5.QtCore import QObject, pyqtSignal

from line import Line
from settingobj import SettingObj



class ToolBase(QObject, SettingObj):
  cleared = pyqtSignal()
  added = pyqtSignal(Line)

  def __init__(self):
    super().__init__()
    self.lines = []

  def clear(self):
    self.lines = []
    self.cleared.emit()

  def add(self, name, x, y, y_):
    x, y, y_ = Line.cleanUp(x, y, y_)
    l = Line(name, x, y, y_)
    self.lines.append(l)
    self.added.emit(l)

  def getLines(self):
    raise NotImplementedError()
