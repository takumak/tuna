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
    return self.lines

  def getGraphItems(self, colorpicker):
    return []

  def getXrange(self):
    if len(self.lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getXrange() for l in self.lines])
    return min(l1), max(l2)

  def getYrange(self):
    if len(self.lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getYrange() for l in self.lines])
    return min(l1), max(l2)
