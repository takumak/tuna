from PyQt5.QtCore import QObject, pyqtSignal
import pyqtgraph as pg

from line import Line
from settingobj import SettingObj
from graphitems import *



class ToolBase(QObject, SettingObj):
  cleared = pyqtSignal()
  added = pyqtSignal(Line)

  def __init__(self, graphWidget):
    super().__init__()
    self.graphWidget = graphWidget
    self.lines = []
    self.lineNameMap = {}

  def clear(self):
    self.lines = []
    self.lineNameMap = {}
    self.cleared.emit()

  def add(self, name, x, y, y_):
    if name in self.lineNameMap:
      i = 2
      while True:
        name2 = '%s_%d' % (name, i)
        if name2 not in self.lineNameMap:
          break
        i += 1
      name = name2

    x, y, y_ = Line.cleanUp(x, y, y_)
    l = Line(name, x, y, y_)
    self.lines.append(l)
    self.lineNameMap[name] = l
    self.added.emit(l)
    return l

  def getLines(self):
    return self.lines

  def getGraphItems(self, colorpicker):
    items = []
    for line in self.getLines():
      col = colorpicker.next()
      curve = PlotCurveItem(line.x, line.y, self.graphWidget, col, line.name)
      items.append(curve)
      # if line.plotErrors:
      #   items.append(pg.ErrorBarItem(
      #     x=line.x, y=line.y, height=line.y_*2, beam=0.2, pen=pen))
      #   items.append(pg.ScatterPlotItem(
      #     x=line.x, y=line.y, brush=pg.mkBrush(color=col)))
    return items

  def getXrange(self):
    if len(self.lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getXrange() for l in self.lines])
    return min(l1), max(l2)

  def getYrange(self):
    if len(self.lines) == 0: return 0, 1
    l1, l2 = zip(*[l.getYrange() for l in self.lines])
    return min(l1), max(l2)

  def newSession(self):
    self.clear()
